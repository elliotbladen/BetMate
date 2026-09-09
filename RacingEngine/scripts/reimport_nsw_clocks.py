#!/usr/bin/env python3
"""
scripts/reimport_nsw_clocks.py

Re-import every NSW metro meeting whose races still have no official clock.

Root cause: an older importer cached the ATC Swiss Timing report under
`sectionals.pdf` using a URL that was NOT year-qualified, so it fetched whatever
that day/month resolved to. 2024-04-13 Randwick came back as *13 April 2019* —
which is why 437 of 1,006 shared races had a completely different runner set
(WINX and HARTNELL in a 2024 field). 108 dates carry that legacy file.

`download_atc_sectional_pdf` now builds a year-qualified URL
(`/{year}/{DDMM}{RHIL|RAND}.pdf`) and caches as `atc-sectionals.pdf`, so a plain
re-import fetches the correct meeting and UPDATEs the clock onto the
racing-com result row. Verified on 2024-04-13: all 10 races now clock at
15.8-17.4 m/s and race 8 is the 2000m Queen Elizabeth at 122.02s.

Legacy rnsw-authorised rows for the date are deleted first so the wrong meeting
cannot linger. Only randwick and rosehill are covered by the ATC archive.

Usage:
  python3 scripts/reimport_nsw_clocks.py                # list the work
  python3 scripts/reimport_nsw_clocks.py --apply
  python3 scripts/reimport_nsw_clocks.py --apply --limit 5
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from racing_engine.rnsw import import_meeting
from racing_engine.storage import RacingStore

DB = ROOT / "data" / "racing_engine.sqlite"
ATC_TRACKS = ("randwick", "rosehill")

NEEDS_CLOCK = """
SELECT race_date, track_slug, COUNT(*) races
  FROM race_results
 WHERE source='racing-com-nsw-authorised-v2' AND official_time_seconds IS NULL
   AND track_slug IN ('randwick','rosehill')
 GROUP BY race_date, track_slug ORDER BY race_date DESC
"""

COVERAGE = """
SELECT COUNT(*) races, SUM(CASE WHEN official_time_seconds IS NOT NULL THEN 1 ELSE 0 END) clocked
  FROM race_results WHERE source='racing-com-nsw-authorised-v2'
"""


def coverage(con) -> str:
    n, c = con.execute(COVERAGE).fetchone()
    return f"{c}/{n} ({100.0 * c / n:.1f}%)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    todo = con.execute(NEEDS_CLOCK).fetchall()
    print(f"NSW racing-com clock coverage now: {coverage(con)}")
    print(f"meetings still without a clock   : {len(todo)}  ({sum(r[2] for r in todo)} races)\n")
    for d, t, n in todo[:12]:
        print(f"   {d}  {t:<10} {n} races")
    if len(todo) > 12:
        print(f"   ... and {len(todo)-12} more")
    con.close()

    if not args.apply:
        print("\nDRY RUN. Re-run with --apply (needs network access).")
        return 0

    work = todo[: args.limit] if args.limit else todo
    store = RacingStore(DB)
    ok = 0
    failures: list[str] = []
    try:
        for d, t, _n in work:
            try:
                # drop the legacy wrong-meeting rows for this date first
                store.connection.execute(
                    "DELETE FROM runner_sectionals WHERE source='rnsw-authorised' AND race_date=? AND track_slug=?", (d, t))
                store.connection.execute(
                    "DELETE FROM runner_results WHERE source='rnsw-authorised' AND race_date=? AND track_slug=?", (d, t))
                store.connection.execute(
                    "DELETE FROM race_results WHERE source='rnsw-authorised' AND race_date=? AND track_slug=?", (d, t))
                store.connection.commit()
                import_meeting(store, d, venue=None, slug=t, sectional_code=None, meet_code=None)
                ok += 1
                print(f"  ok   {d} {t}")
            except Exception as exc:
                failures.append(f"{d} {t}: {str(exc)[:90]}")
                print(f"  SKIP {d} {t}: {str(exc)[:90]}")
    finally:
        store.close()

    con = sqlite3.connect(DB)
    print(f"\n{ok}/{len(work)} meetings re-imported. NSW coverage now: {coverage(con)}")
    con.close()
    if failures:
        print(f"{len(failures)} unavailable (archive gaps are recorded, never invented):")
        for f in failures[:12]:
            print("   ", f)
    print("\nRebuild the clean layer, then re-check coverage:")
    print("  python3 -m racing_engine.v2_ratings --as-of 2026-12-31")
    print("  python3 scripts/check_state_clock_coverage.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
