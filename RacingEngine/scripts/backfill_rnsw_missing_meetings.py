#!/usr/bin/env python3
"""
scripts/backfill_rnsw_missing_meetings.py

Import the Racing NSW meetings that were never ingested.

Why this matters: par-v2 only rates races that carry a clock
(`performance_par_v2.py` filters `official_time_seconds IS NOT NULL`), and the
RNSW official archive is the ONLY NSW source with one. Coverage today is NSW
48.6% against Victoria 99.8%, so a Sydney horse is rated on about half its
career and a Victorian horse on all of it. That is a systematic bias in any
cross-state rating, and it is what kept Sydney horses out of the leaderboards.

The gap splits two ways:
  * 34 meetings never imported  -> 339 races  (this script fixes these)
  * 50 meetings imported but with individual races missing -> 63 races
    (a PDF parser issue, NOT fixable here — reported separately)

Dry-run by default. Network access to the Racing NSW archive is required.

Usage:
  python3 scripts/backfill_rnsw_missing_meetings.py            # list the work
  python3 scripts/backfill_rnsw_missing_meetings.py --apply
  python3 scripts/backfill_rnsw_missing_meetings.py --apply --limit 5
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

MISSING_MEETINGS = """
WITH miss AS (
  SELECT a.race_date, a.track_slug, COUNT(*) AS missing
  FROM race_results a
  WHERE a.source='racing-com-nsw-authorised-v2'
    AND NOT EXISTS (SELECT 1 FROM race_results b
                    WHERE b.source='rnsw-authorised' AND b.race_date=a.race_date
                      AND b.track_slug=a.track_slug AND b.race_number=a.race_number)
  GROUP BY 1,2),
have AS (SELECT race_date, track_slug, COUNT(*) AS present
         FROM race_results WHERE source='rnsw-authorised' GROUP BY 1,2)
SELECT m.race_date, m.track_slug, m.missing, COALESCE(h.present,0) AS present
FROM miss m LEFT JOIN have h USING(race_date, track_slug)
ORDER BY m.race_date DESC
"""

COVERAGE = """
SELECT state,
       COUNT(*) races,
       SUM(CASE WHEN official_time_seconds IS NOT NULL THEN 1 ELSE 0 END) clocked
FROM v2_clean_races GROUP BY state
"""


def coverage(con) -> str:
    return " | ".join(f"{s} {c}/{n} ({100.0*c/n:.1f}%)" for s, n, c in con.execute(COVERAGE))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="only attempt the N most recent meetings")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    rows = con.execute(MISSING_MEETINGS).fetchall()
    never = [r for r in rows if r[3] == 0]
    partial = [r for r in rows if r[3] > 0]

    print(f"Clock coverage now: {coverage(con)}\n")
    print(f"Meetings never imported : {len(never):>3}  ({sum(r[2] for r in never)} races)  <- this script")
    print(f"Partially imported      : {len(partial):>3}  ({sum(r[2] for r in partial)} races)  <- PDF parser gap, not fixed here\n")
    for d, t, m, _ in never[:15]:
        print(f"   {d}  {t:<12} {m} races")
    if len(never) > 15:
        print(f"   ... and {len(never)-15} more")
    con.close()

    if not args.apply:
        print("\nDRY RUN. Re-run with --apply to import (needs network access).")
        return 0

    todo = never[: args.limit] if args.limit else never
    store = RacingStore(DB)
    ok = races = runners = 0
    failures: list[str] = []
    try:
        for d, t, _, _ in todo:
            try:
                r, n = import_meeting(store, d, venue=None, slug=t, sectional_code=None, meet_code=None)
                races += r; runners += n; ok += 1
                print(f"  imported {d} {t}: {r} races, {n} finishers")
            except Exception as exc:
                failures.append(f"{d} {t}: {exc}")
                print(f"  SKIPPED  {d} {t}: {str(exc)[:110]}")
    finally:
        store.close()

    print(f"\n{ok}/{len(todo)} meetings imported — {races} races, {runners} finishers.")
    if failures:
        print(f"{len(failures)} unavailable (archive gaps are expected and are recorded, not invented):")
        for f in failures[:10]:
            print("   ", f)
    print("\nNow rebuild the clean layer so the new clocks are picked up:")
    print("  python3 -c \"from pathlib import Path; import sys; sys.path.insert(0,'.'); "
          "from racing_engine.storage import RacingStore; from racing_engine.v2_ratings import rebuild_clean_history; "
          "s=RacingStore(Path('data/racing_engine.sqlite')); print(rebuild_clean_history(s,'2026-12-31')); s.connection.commit()\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
