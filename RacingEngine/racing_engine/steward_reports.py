"""Import official steward reports through the authorised public form source."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from .enrich_history import VENUE_SLUGS
from .racing_com import DATE_QUERY, graphql_request, request_meeting
from .storage import RacingStore
from .stewards import PARSER_VERSION, REPORT_SOURCE, classify_report, plain_text


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", choices=("VIC", "NSW", "ALL"), default="ALL")
    parser.add_argument("--date", help="Import only meetings on this ISO date (YYYY-MM-DD).")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-meetings", type=int, default=0, help="Bound a resumable batch; 0 means all remaining.")
    args = parser.parse_args()
    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        states = ("VIC", "NSW") if args.state == "ALL" else (args.state,)
        date_filter = " AND race_date = ?" if args.date else ""
        parameters = (*states, REPORT_SOURCE, *((args.date,) if args.date else ()))
        targets = store.connection.execute(
            """SELECT DISTINCT state, race_date, track_slug FROM race_results
               WHERE state IN ({})
                 AND NOT EXISTS (
                   SELECT 1 FROM steward_report_ingestions si
                    WHERE si.report_source = ? AND si.race_date = race_results.race_date
                      AND si.track_slug = race_results.track_slug AND si.status = 'complete'
                 )
                 {}
               ORDER BY race_date, track_slug""".format(
                   ",".join("?" for _ in states), date_filter), parameters).fetchall()
        if args.dry_run:
            print(json.dumps([dict(row) for row in targets], indent=2)); return
        if args.max_meetings:
            targets = targets[:args.max_meetings]
        by_date: dict[str, list] = defaultdict(list)
        for target in targets:
            by_date[target["race_date"]].append(target)
        reports = events = errors = meetings_done = 0
        for race_date, date_targets in by_date.items():
            records = graphql_request(DATE_QUERY, {"date": race_date}).get("data", {}).get("GetMeetingByDate") or []
            records_by_slug = {}
            for record in records:
                venue = (record.get("venue") or "").lower()
                for state in states:
                    if record.get("state") == state and venue in VENUE_SLUGS[state] and not record.get("isTrial") and not record.get("isJumpOut"):
                        records_by_slug[(state, VENUE_SLUGS[state][venue])] = record
            for target in date_targets:
                record = records_by_slug.get((target["state"], target["track_slug"]))
                if not record:
                    errors += 1; continue
                try:
                    for race in request_meeting(str(record["id"])).get("data", {}).get("getNoCacheRacesForMeet") or []:
                        report = race.get("stewardsReport") or {}
                        html = str(report.get("htmlCode") or "").strip()
                        if not html:
                            continue
                        names = [str(item.get("horseName")) for item in race.get("formRaceEntries") or [] if item.get("horseName")]
                        extracted = classify_report(html, names)
                        store.upsert_steward_report(
                            report_source=REPORT_SOURCE, race_date=race_date, track_slug=target["track_slug"],
                            race_number=int(race["raceNumber"]), source_race_code=str(report.get("raceCode") or race.get("id") or "") or None,
                            report_html=html, report_text=plain_text(html), source_updated_at=report.get("lastUpdated"),
                            source_url=f"https://www.racing.com/form/{race_date}/{target['track_slug']}",
                            parser_version=PARSER_VERSION, events=extracted,
                        )
                        reports += 1; events += len(extracted)
                    store.record_steward_report_check(
                        report_source=REPORT_SOURCE, race_date=race_date, track_slug=target["track_slug"],
                        status="complete", detail="official report imported or no report published",
                    )
                    meetings_done += 1
                    if meetings_done % 25 == 0:
                        print(f"Imported {meetings_done} meetings through {race_date}", flush=True)
                except Exception as exc:
                    errors += 1
                    store.record_steward_report_check(
                        report_source=REPORT_SOURCE, race_date=race_date, track_slug=target["track_slug"],
                        status="error", detail=str(exc)[:500],
                    )
                    print(f"Skipped {race_date} {target['track_slug']}: {exc}", flush=True)
        print(json.dumps({"reports": reports, "events": events, "errors": errors}, sort_keys=True))
    finally:
        store.close()


if __name__ == "__main__":
    main()
