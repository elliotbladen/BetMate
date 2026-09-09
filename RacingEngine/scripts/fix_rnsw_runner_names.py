#!/usr/bin/env python3
"""
Backfill: strip barrier/top-speed tokens from stored Racing NSW runner names.

`clean_pdf_runner_name` was added to racing_engine/rnsw.py on 2026-09-03 (b7d5552)
but the NSW rows were imported before that and never re-cleaned, so 9,652 of
10,598 rnsw-authorised runner names still read like "LIFESAVER 3 67.1".

That fragments NSW horse identity — every run looks like a different horse — which
is why no Sydney horse accumulates a form history in the par/ratings chain.

Idempotent: re-running is a no-op. Source data is recoverable from
data/seed/racing_seed.sql.gz if anything goes wrong.

Usage:  python3 scripts_fix_rnsw_names.py [--apply]
"""
from __future__ import annotations
import argparse, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from racing_engine.rnsw import clean_pdf_runner_name

DB = ROOT / "data" / "racing_engine.sqlite"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default is dry-run)")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT source,race_date,track_slug,race_number,runner_number,runner_name "
        "FROM runner_results WHERE source='rnsw-authorised'").fetchall()

    changes = []
    for src, d, t, rn, num, name in rows:
        clean = clean_pdf_runner_name(name)
        if clean and clean != name:
            changes.append((clean, src, d, t, rn, num))

    print(f"rnsw-authorised runner rows : {len(rows):,}")
    print(f"names needing a fix         : {len(changes):,}")
    bad = [c for c in changes if any(ch.isdigit() for ch in c[0])]
    if bad:
        print(f"  WARNING: {len(bad)} would still contain digits — inspect before applying")
        for c in bad[:5]:
            print("   ", c[0])
    for c in changes[:5]:
        print(f"   -> {c[0]!r}")

    if not args.apply:
        print("\nDRY RUN. Re-run with --apply to write.")
        return 0

    con.executemany(
        "UPDATE runner_results SET runner_name=? WHERE source=? AND race_date=? "
        "AND track_slug=? AND race_number=? AND runner_number=?", changes)
    con.commit()
    left = con.execute(
        "SELECT COUNT(*) FROM runner_results WHERE source='rnsw-authorised' "
        "AND runner_name GLOB '*[0-9]*'").fetchone()[0]
    distinct = con.execute(
        "SELECT COUNT(DISTINCT runner_name) FROM runner_results WHERE source='rnsw-authorised'").fetchone()[0]
    print(f"\nApplied {len(changes):,} updates.")
    print(f"NSW names still containing digits: {left}")
    print(f"Distinct NSW runner names now    : {distinct:,}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
