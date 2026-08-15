"""Authorised internal Racing Victoria results and sectionals importer.

Racing Victoria has given BetMate permission to scrape the public Racing.com
form pages for this non-commercial research project.  This module uses the
same public GraphQL request made by that page, archives the unmodified JSON
response locally, and writes only verified values to the research database.

It is deliberately limited to the configured Victorian Saturday meetings.
It is not a public feed, customer feature, or odds/pricing publisher.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://graphql.rmdprod.racing.com/"
# This is the public page's client key, not a BetMate credential.  Keep the
# request shape aligned with the public page and do not use privileged APIs.
PUBLIC_CLIENT_KEY = "da2-6nsi4ztsynar3l3frgxf77q5fe"
SOURCE = "racing-com-rv-authorised"
MEETINGS = {
    "2026-08-01": ("5195982", "flemington"),
    "2026-08-08": ("5195479", "caulfield-heath"),
}

QUERY = """
query RacingEngineMeeting($meetCode: ID!) {
  getNoCacheRacesForMeet(meetCode: $meetCode) {
    id raceNumber distance raceTime trackCondition condition hasSectionals
    meet { id venue date state railPosition trackCondition }
    formRaceEntries {
      id raceEntryNumber horseName position margin winningTime
      positionAtSettledAbv positionAt800Abv positionAt400Abv
      timing {
        toEightHundredMetresSeconds
        eightHundredToFourHundredMetresSeconds
        fourHundredToFinishMetresSeconds
        finishTimeSeconds
      }
    }
  }
}
"""


def centiseconds(value: object) -> float | None:
    """Convert the public form payload's centisecond integers to seconds."""
    if value in (None, "", 0, "0"):
        return None
    try:
        return int(value) / 100
    except (TypeError, ValueError):
        return None


def race_time(value: object) -> float | None:
    """Convert the displayed race time, such as ``1:23.25``, to seconds."""
    match = re.fullmatch(r"(?:(\d+):)?(\d{1,2})\.(\d{1,2})", str(value or "").strip())
    if not match:
        return None
    return int(match.group(1) or 0) * 60 + int(match.group(2)) + int(match.group(3)) / 100


def lengths(value: object) -> float | None:
    if not value:
        return None
    match = re.match(r"^([0-9.]+)L$", str(value).strip())
    return float(match.group(1)) if match else None


def position(value: object) -> int | None:
    match = re.search(r"(\d+)", str(value or ""))
    return int(match.group(1)) if match else None


def request_meeting(meet_code: str) -> dict:
    payload = json.dumps({"query": QUERY, "variables": {"meetCode": meet_code}}).encode()
    request = Request(
        ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": PUBLIC_CLIENT_KEY,
            "User-Agent": "BetMate-RacingEngine/0.1 (authorised internal research ingestion)",
        },
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if parsed.get("errors"):
        raise RuntimeError(f"Racing.com returned GraphQL errors: {parsed['errors']}")
    races = parsed.get("data", {}).get("getNoCacheRacesForMeet")
    if not races:
        raise RuntimeError(f"No race data returned for meeting {meet_code}.")
    return parsed


def import_meeting(store: RacingStore, race_date: str) -> tuple[int, int, int]:
    meet_code, slug = MEETINGS[race_date]
    payload = request_meeting(meet_code)
    archive = ROOT / "data" / "raw" / "racing_com" / race_date / slug
    archive.mkdir(parents=True, exist_ok=True)
    raw_path = archive / "meeting.json"
    raw_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    source_url = f"https://www.racing.com/form/{race_date}/{slug}"
    races = payload["data"]["getNoCacheRacesForMeet"]
    imported_races = imported_runners = imported_sections = 0
    for race in races:
        meet = race.get("meet") or {}
        if meet.get("state") != "VIC":
            raise RuntimeError(f"Expected VIC data, received {meet.get('state')!r}.")
        runners: list[dict] = []
        sectional_rows: list[dict] = []
        for entry in race.get("formRaceEntries") or []:
            runner_number = entry.get("raceEntryNumber")
            if not runner_number:
                continue
            finish_position = entry.get("position")
            # Racing.com's public form uses 109 for a non-runner.  It is not a
            # finishing position and must never be treated as one in ratings.
            status = "scratched" if finish_position == 109 else "finished"
            runners.append({
                "runner_number": int(runner_number),
                "runner_name": entry.get("horseName") or "Unknown",
                "finish_position": None if status == "scratched" else finish_position,
                "beaten_lengths": lengths(entry.get("margin")),
                "finish_time_seconds": centiseconds((entry.get("timing") or {}).get("finishTimeSeconds")),
                "result_status": status,
                "raw_entry": entry,
            })
            if status != "finished":
                continue
            timing = entry.get("timing") or {}
            # Markers are metres remaining, matching Racing.com's displayed
            # "to 800", "800-400" and "last 400" sections.  Values are
            # section durations, not cumulative times.
            for marker, value, pos in (
                (800, timing.get("toEightHundredMetresSeconds"), entry.get("positionAt800Abv")),
                (400, timing.get("eightHundredToFourHundredMetresSeconds"), entry.get("positionAt400Abv")),
                (0, timing.get("fourHundredToFinishMetresSeconds"), None),
            ):
                seconds = centiseconds(value)
                if seconds is None:
                    continue
                sectional_rows.append({
                    "source": SOURCE,
                    "race_date": race_date,
                    "track_slug": slug,
                    "race_number": int(race["raceNumber"]),
                    "runner_number": int(runner_number),
                    "marker_metres": marker,
                    "section_seconds": seconds,
                    "position_at_marker": position(pos),
                    "source_url": source_url,
                    "raw_entry": entry,
                })
        store.upsert_result(
            source=SOURCE,
            race_date=race_date,
            state="VIC",
            track_slug=slug,
            race_number=int(race["raceNumber"]),
            official_time_seconds=race_time(race.get("raceTime")),
            track_condition=race.get("trackCondition") or meet.get("trackCondition"),
            rail_position=meet.get("railPosition"),
            source_url=source_url,
            raw_race=race,
            runners=runners,
        )
        store.upsert_sectionals(sectional_rows)
        imported_races += 1
        imported_runners += len(runners)
        imported_sections += len(sectional_rows)
    return imported_races, imported_runners, imported_sections


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", choices=tuple(MEETINGS), required=True)
    args = parser.parse_args()
    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        races, runners, sections = import_meeting(store, args.date)
        print(f"Imported {races} VIC result races, {runners} runner results and {sections} sectional records.")
    finally:
        store.close()


if __name__ == "__main__":
    main()
