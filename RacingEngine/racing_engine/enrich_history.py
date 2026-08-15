"""Backfill objective historic card metadata without replacing result sources."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from .racing_com import DATE_QUERY, graphql_request, kilograms, position, request_meeting
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
VENUE_SLUGS = {
    "VIC": {"caulfield": "caulfield", "caulfield heath": "caulfield-heath", "flemington": "flemington",
            "sportsbet sandown hillside": "sportsbet-sandown-hillside", "sportsbet sandown lakeside": "sportsbet-sandown-lakeside"},
    "NSW": {"rosehill gardens": "rosehill", "royal randwick": "randwick", "randwick": "randwick"},
}


def runner_metadata(entry: dict) -> dict:
    return {
        "runner_number": int(entry["raceEntryNumber"]),
        "barrier": position(entry.get("barrierNumber")),
        "weight_carried_kg": kilograms(entry.get("weightCarried") or entry.get("weight")),
        "jockey": entry.get("jockeyName"),
        "trainer": entry.get("trainerName"),
        "official_handicap_rating": entry.get("handicapRating"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", choices=("VIC", "NSW", "ALL"), default="ALL")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--missing-start-times", action="store_true", help="Resume only races without a timestamp")
    args = parser.parse_args()
    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        states = ("VIC", "NSW") if args.state == "ALL" else (args.state,)
        filter_sql = " AND scheduled_start_at IS NULL" if args.missing_start_times else ""
        targets = store.connection.execute(
            """SELECT state, race_date, track_slug, group_concat(DISTINCT source) AS sources
                 FROM race_results WHERE state IN ({}) {}
                 GROUP BY state, race_date, track_slug ORDER BY race_date, track_slug""".format(
                ",".join("?" for _ in states), filter_sql), states).fetchall()
        by_date: dict[str, list] = defaultdict(list)
        for target in targets:
            by_date[target["race_date"]].append(target)
        if args.dry_run:
            print(json.dumps([dict(row) for row in targets], indent=2)); return
        total = errors = 0
        for race_date, date_targets in by_date.items():
            records = graphql_request(DATE_QUERY, {"date": race_date}).get("data", {}).get("GetMeetingByDate") or []
            records_by_slug = {}
            for record in records:
                venue = (record.get("venue") or "").lower()
                for state in states:
                    if record.get("state") == state and venue in VENUE_SLUGS[state] and not record.get("isTrial") and not record.get("isJumpOut"):
                        slug = VENUE_SLUGS[state][venue]
                        records_by_slug[(state, slug)] = record
            for target in date_targets:
                record = records_by_slug.get((target["state"], target["track_slug"]))
                if not record:
                    errors += 1; print(f"Skipped {race_date} {target['track_slug']}: public meeting not found", flush=True); continue
                try:
                    races = request_meeting(str(record["id"])).get("data", {}).get("getNoCacheRacesForMeet") or []
                    sources = str(target["sources"]).split(",")
                    for race in races:
                        entries = [entry for entry in race.get("formRaceEntries") or [] if entry.get("raceEntryNumber")]
                        class_code = next((entry.get("rdcClass") for entry in entries if entry.get("rdcClass")), None)
                        for source in sources:
                            store.enrich_result_metadata(source=source, race_date=race_date,
                                track_slug=target["track_slug"], race_number=int(race["raceNumber"]),
                                race_class=race.get("condition"), race_class_code=class_code,
                                scheduled_start_at=race.get("time"),
                                runners=[runner_metadata(entry) for entry in entries])
                    total += 1; print(f"Enriched {race_date} {target['track_slug']}", flush=True)
                except Exception as exc:
                    errors += 1; print(f"Skipped {race_date} {target['track_slug']}: {exc}", flush=True)
        print(json.dumps({"meetings_enriched": total, "errors": errors}, sort_keys=True))
    finally:
        store.close()


if __name__ == "__main__":
    main()
