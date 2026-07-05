#!/usr/bin/env python3
"""
Weekly AFL T2 refresh.

Sequence:
  1. Refresh AFL Tables game stats for the requested season.
  2. Refresh the Footywire round snapshot for the requested round.
  3. Rebuild the richer public AFL T2 snapshot table.
  4. Optionally run the AFL round pricing engine.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run_step(*args: str) -> None:
    cmd = [sys.executable, *args]
    print(f"\n>> {' '.join(args)}")
    subprocess.run(cmd, check=True, cwd=str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh AFL T2 and optional pricing outputs.")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--no-scrape", action="store_true", help="Skip source refresh and only rebuild snapshots.")
    parser.add_argument("--no-price", action="store_true", help="Skip running the AFL pricing engine.")
    args = parser.parse_args()

    if not args.no_scrape:
        run_step("scripts/scrape_afl_game_stats.py", "--seasons", str(args.season))
        run_step("scripts/scrape_footywire_round_snapshot.py", "--season", str(args.season), "--round", str(args.round))

    run_step("scripts/build_afl_public_t2_snapshots.py")

    if not args.no_price:
        run_step("scripts/prepare_afl_round.py", "--season", str(args.season), "--round", str(args.round))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
