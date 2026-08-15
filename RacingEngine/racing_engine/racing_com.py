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
from datetime import date, timedelta
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
METRO_VENUES = {
    "caulfield", "caulfield heath", "flemington", "moonee valley",
    "sportsbet sandown hillside", "sportsbet sandown lakeside",
}

QUERY = """
query RacingEngineMeeting($meetCode: ID!) {
  getNoCacheRacesForMeet(meetCode: $meetCode) {
    id raceNumber distance raceTime time timeAtVenue trackCondition condition hasSectionals
    stewardsReport { raceCode htmlCode lastUpdated }
    meet { id venue date state railPosition trackCondition }
    formRaceEntries {
      id raceEntryNumber horseName position margin winningTime
      barrierNumber weight weightCarried jockeyName trainerName handicapRating rdcClass
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

CALENDAR_QUERY = """
query RacingEngineCalendar($states: String!, $daysBack: Int!, $daysForward: Int!, $userDate: String!) {
  GetRaceMeetingsByStateNew(states: $states, daysBack: $daysBack, daysForward: $daysForward, userDate: $userDate) {
    id venue date state isTrial isJumpOut meetUrl
  }
}
"""

DATE_QUERY = """
query RacingEngineMeetingsByDate($date: String!) {
  GetMeetingByDate(date: $date) {
    id venue date state isTrial isJumpOut meetUrl
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


def distance_metres(value: object) -> int | None:
    match = re.fullmatch(r"(\d+)m", str(value or "").strip(), flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def lengths(value: object) -> float | None:
    if not value:
        return None
    match = re.match(r"^([0-9.]+)L$", str(value).strip())
    return float(match.group(1)) if match else None


def position(value: object) -> int | None:
    match = re.search(r"(\d+)", str(value or ""))
    return int(match.group(1)) if match else None


def kilograms(value: object) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group()) if match else None


def graphql_request(query: str, variables: dict) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode()
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
    return parsed


def request_meeting(meet_code: str) -> dict:
    parsed = graphql_request(QUERY, {"meetCode": meet_code})
    races = parsed.get("data", {}).get("getNoCacheRacesForMeet")
    if not races:
        raise RuntimeError(f"No race data returned for meeting {meet_code}.")
    return parsed


def discover_saturday_metro_meetings(start_date: str, end_date: str) -> list[dict]:
    """Discover only authorised Victorian Saturday metro meetings.

    Discovery and ingestion are separate so a caller can inspect the exact
    meeting list before a larger historical backfill is run.
    """
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    if end < start:
        raise ValueError("end date must not precede start date")
    # The calendar caps historical look-backs.  The public form service's
    # meeting-by-date lookup is deterministic, so query Saturdays directly.
    meetings_by_code: dict[str, dict] = {}
    current = start + timedelta(days=(5 - start.weekday()) % 7)
    while current <= end:
        payload = graphql_request(DATE_QUERY, {"date": current.isoformat()})
        records = payload.get("data", {}).get("GetMeetingByDate") or []
        for record in records:
            meeting_date = date.fromisoformat(record["date"])
            venue = (record.get("venue") or "").lower()
            if (meeting_date == current and meeting_date.weekday() == 5
                    and venue in METRO_VENUES and not record.get("isTrial") and not record.get("isJumpOut")):
                url = record.get("meetUrl") or ""
                meetings_by_code[str(record["id"])] = {
                    "date": record["date"], "meet_code": str(record["id"]),
                    "slug": url.rstrip("/").rsplit("/", 1)[-1], "venue": record["venue"], "url": url,
                }
        current += timedelta(days=7)
    return sorted(meetings_by_code.values(), key=lambda meeting: (meeting["date"], meeting["meet_code"]))


def import_meeting(store: RacingStore, race_date: str, *, meet_code: str | None = None,
                   slug: str | None = None, expected_state: str = "VIC",
                   source: str = SOURCE) -> tuple[int, int, int]:
    default = MEETINGS.get(race_date)
    if meet_code is None:
        if default is None:
            discovered = discover_saturday_metro_meetings(race_date, race_date)
            if len(discovered) != 1:
                raise RuntimeError(f"Expected one Victorian Saturday metro meeting on {race_date}, found {len(discovered)}.")
            meet_code, slug = discovered[0]["meet_code"], discovered[0]["slug"]
        else:
            meet_code, slug = default
    if not slug:
        raise ValueError("A meeting slug is required.")
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
        if meet.get("state") != expected_state:
            raise RuntimeError(f"Expected {expected_state} data, received {meet.get('state')!r}.")
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
                "barrier": position(entry.get("barrierNumber")),
                "weight_carried_kg": kilograms(entry.get("weightCarried") or entry.get("weight")),
                "jockey": entry.get("jockeyName"),
                "trainer": entry.get("trainerName"),
                "official_handicap_rating": entry.get("handicapRating"),
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
                    "source": source,
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
            source=source,
            race_date=race_date,
            state=expected_state,
            track_slug=slug,
            race_number=int(race["raceNumber"]),
            distance_metres=distance_metres(race.get("distance")),
            race_class=race.get("condition"),
            race_class_code=next((entry.get("rdcClass") for entry in race.get("formRaceEntries") or [] if entry.get("rdcClass")), None),
            scheduled_start_at=race.get("time"),
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
    parser.add_argument("--date", help="One Victorian Saturday metro date (YYYY-MM-DD)")
    parser.add_argument("--from-date", dest="from_date", help="Discover range start (YYYY-MM-DD)")
    parser.add_argument("--to-date", dest="to_date", help="Discover range end (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Print discovered meetings without downloading cards")
    args = parser.parse_args()
    if bool(args.date) == bool(args.from_date or args.to_date):
        parser.error("Provide either --date or both --from-date and --to-date.")
    if (args.from_date and not args.to_date) or (args.to_date and not args.from_date):
        parser.error("--from-date and --to-date must be used together.")
    meetings = ([{"date": args.date, "meet_code": None, "slug": None}] if args.date
                else discover_saturday_metro_meetings(args.from_date, args.to_date))
    if args.dry_run:
        print(json.dumps(meetings, indent=2, sort_keys=True)); return
    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        totals = [0, 0, 0]; failures: list[str] = []
        for meeting in meetings:
            try:
                races, runners, sections = import_meeting(store, meeting["date"], meet_code=meeting["meet_code"], slug=meeting["slug"])
                totals = [left + right for left, right in zip(totals, (races, runners, sections))]
                print(f"Imported {meeting['date']}: {races} VIC races, {runners} runner results and {sections} sectional records.")
            except Exception as exc:
                failures.append(f"{meeting['date']} {meeting.get('venue', meeting['slug'])}: {exc}")
                print(f"Skipped {meeting['date']} {meeting.get('venue', meeting['slug'])}: {exc}")
        print(f"Total: {totals[0]} VIC races, {totals[1]} runner results and {totals[2]} sectional records.")
        if failures:
            print(f"Unavailable meetings ({len(failures)}):\n" + "\n".join(failures))
    finally:
        store.close()


if __name__ == "__main__":
    main()
