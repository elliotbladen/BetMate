#!/usr/bin/env python3
"""
scripts/racing_seed_status.py

Is this machine's RacingEngine database in step with the committed seed?

The racing DB is ~18.5 GB and gitignored, so it never travels. 91% of it
(run_performances, horse_rating_states) is regenerable model output and is
deliberately excluded from the seed; the irreplaceable source data compresses to
about 52 MB and DOES travel, via RacingEngine/data/seed/racing_seed.sql.gz.

That only works if the seed is rebuilt whenever the source data changes. This
compares the seed's manifest watermark against the live DB and says which way
they are out of step.

Exit codes (so shell scripts can branch):
    0  in step, or nothing to compare
    1  local DB is BEHIND the seed   -> ./restore_db.sh
    2  local DB is AHEAD of the seed -> python3 build_seed.py, then commit
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "RacingEngine"
DB = ROOT / "data" / "racing_engine.sqlite"
MANIFEST = ROOT / "data" / "seed" / "seed_manifest.json"
SEED = ROOT / "data" / "seed" / "racing_seed.sql.gz"

KEYS = ("race_results_max_date", "race_results_rows", "runner_results_rows", "sectionals_rows")
SQL = {
    "race_results_max_date": "SELECT MAX(race_date) FROM race_results",
    "race_results_rows":     "SELECT COUNT(*) FROM race_results",
    "runner_results_rows":   "SELECT COUNT(*) FROM runner_results",
    "sectionals_rows":       "SELECT COUNT(*) FROM canonical_sectionals",
}


def live() -> dict | None:
    if not DB.exists():
        return None
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        return {k: c.execute(q).fetchone()[0] for k, q in SQL.items()}
    except sqlite3.Error:
        return None
    finally:
        c.close()


def main() -> int:
    print("--- RacingEngine seed status ---")
    if not SEED.exists():
        print("  No seed committed. Run: git lfs pull")
        return 0
    if not MANIFEST.exists():
        print("  Seed has no manifest (built before manifests existed).")
        print("  Rebuild on the machine with the newest data: python3 RacingEngine/build_seed.py")
        return 0

    m = json.loads(MANIFEST.read_text())
    l = live()
    if l is None:
        print(f"  No local database. Seed holds results to {m.get('race_results_max_date')}.")
        print("  Restore it:  cd RacingEngine && ./restore_db.sh")
        return 1

    print(f"  seed  : results to {m.get('race_results_max_date')}  "
          f"({m.get('race_results_rows'):,} races, {m.get('sectionals_rows'):,} sectionals)"
          f"  built {m.get('built_at','?')[:10]}")
    print(f"  local : results to {l['race_results_max_date']}  "
          f"({l['race_results_rows']:,} races, {l['sectionals_rows']:,} sectionals)")

    if all(m.get(k) == l.get(k) for k in KEYS):
        print("  IN STEP.")
        return 0

    # Recency decides, not row count. A cleanup legitimately REMOVES rows — the
    # 2026-09-09 wrong-meeting purge dropped 978 of them — and treating a smaller
    # database as "behind" would send you to restore over your own fix. Row count
    # only breaks a tie when both sides hold the same latest race date.
    seed_date, local_date = str(m.get("race_results_max_date")), str(l["race_results_max_date"])
    if seed_date != local_date:
        seed_newer = seed_date > local_date
    else:
        seed_newer = m.get("race_results_rows", 0) > l["race_results_rows"]
    if seed_newer:
        print("\n  LOCAL DB IS BEHIND THE SEED — the other machine has newer racing data.")
        print("  Restore before doing racing work:")
        print("    cd RacingEngine && git lfs pull && ./restore_db.sh")
        return 1

    print("\n  LOCAL DB IS AHEAD OF THE SEED — this machine has racing data the other lacks.")
    print("  Rebuild the seed so it travels, then commit it:")
    print("    cd RacingEngine && python3 build_seed.py")
    return 2


if __name__ == "__main__":
    sys.exit(main())
