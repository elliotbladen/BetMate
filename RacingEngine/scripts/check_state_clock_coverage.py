#!/usr/bin/env python3
"""
scripts/check_state_clock_coverage.py

Guard against the bug that hid for weeks: NSW had ZERO official race clocks in the
clean layer (0/1,388) while Victoria had 99.8%, because `rnsw-authorised` was
missing from SOURCE_PRIORITY and was filtered out at load.

par-v2 only rates races that carry a clock, so a coverage gap between states is
not a data curiosity — it silently removes one state's horses from every
time-based rating and skews any cross-state leaderboard. Nothing checked for it.

This does. Run it after any clean-layer rebuild and before publishing ratings.

Exit codes:
    0  coverage gap within tolerance
    1  gap exceeds --max-gap — a cross-state leaderboard is NOT safe to publish

Usage:
    python3 scripts/check_state_clock_coverage.py
    python3 scripts/check_state_clock_coverage.py --max-gap 10 --min-coverage 80
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "racing_engine.sqlite"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-gap", type=float, default=15.0,
                    help="max acceptable percentage-point gap in clock coverage between states")
    ap.add_argument("--min-coverage", type=float, default=70.0,
                    help="min acceptable clock coverage for any single state")
    args = ap.parse_args()

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute("""
        SELECT state, COUNT(*),
               SUM(CASE WHEN official_time_seconds IS NOT NULL THEN 1 ELSE 0 END)
        FROM v2_clean_races GROUP BY state ORDER BY state""").fetchall()

    # how much of a typical horse's career is rateable, per state
    horse = dict(con.execute("""
        WITH h AS (SELECT u.horse_key, r.state, COUNT(*) runs,
                          SUM(CASE WHEN r.official_time_seconds IS NOT NULL THEN 1 ELSE 0 END) timed
                   FROM v2_clean_runner_results u JOIN v2_clean_races r USING(race_id)
                   WHERE u.result_status='finished' GROUP BY 1,2 HAVING runs>=4)
        SELECT state, ROUND(AVG(100.0*timed/runs),1) FROM h GROUP BY state""").fetchall())
    con.close()

    if not rows:
        print("No races in the clean layer — nothing to check.")
        return 0

    print("--- clock coverage by state ---")
    print(f"{'state':<7}{'races':>8}{'clocked':>9}{'coverage':>10}{'avg % of a career rateable':>28}")
    pcts = {}
    for state, races, clocked in rows:
        pct = 100.0 * clocked / races if races else 0.0
        pcts[state] = pct
        print(f"{state:<7}{races:>8}{clocked:>9}{pct:>9.1f}%{horse.get(state, 0):>27.1f}%")

    gap = max(pcts.values()) - min(pcts.values()) if len(pcts) > 1 else 0.0
    worst = min(pcts, key=pcts.get)
    print(f"\ngap between states: {gap:.1f}pp (tolerance {args.max_gap}pp)")
    print(f"weakest state     : {worst} at {pcts[worst]:.1f}% (floor {args.min_coverage}%)")

    problems = []
    if gap > args.max_gap:
        problems.append(f"coverage gap {gap:.1f}pp exceeds {args.max_gap}pp")
    if pcts[worst] < args.min_coverage:
        problems.append(f"{worst} coverage {pcts[worst]:.1f}% below {args.min_coverage}%")

    if problems:
        print("\nFAIL — a cross-state leaderboard is NOT safe to publish:")
        for p in problems:
            print("  -", p)
        print("\n  A time-based figure can only rate a race that has a clock, so the")
        print("  weaker state's horses are rated on fewer runs, shrink harder toward")
        print("  the mean and post lower peaks. Fix coverage first:")
        print("    python3 scripts/backfill_rnsw_missing_meetings.py --apply")
        return 1

    print("\nPASS — coverage is even enough to rank across states.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
