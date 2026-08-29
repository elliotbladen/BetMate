#!/usr/bin/env python3
"""Collect post-game AFL/NRL evidence before Monday availability forecasts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from run_pipeline import detect_round

ROOT = Path(__file__).resolve().parents[2]
BETMATE_ROOT = ROOT.parent


def run(command: list[str]) -> bool:
    result = subprocess.run([sys.executable, *command], cwd=BETMATE_ROOT)
    return result.returncode == 0


def main() -> None:
    season = 2026
    afl_target = detect_round("AFL", season)
    nrl_target = detect_round("NRL", season)
    commands = [
        ["scrapers/afl_match_reports.py", "--round", str(max(1, afl_target - 1))],
        ["scrapers/nrl_postgame_scout.py", "--season", str(season), "--round", str(max(1, nrl_target - 1))],
        ["scrapers/nrl_match_review.py", "--season", str(season), "--round", str(max(1, nrl_target - 1))],
        ["scrapers/weekend_injury_diff.py", "--sport", "both", "--season", str(season),
         "--nrl-round", str(nrl_target), "--afl-round", str(afl_target)],
    ]
    failed = [" ".join(cmd) for cmd in commands if not run(cmd)]
    if failed:
        print("Monday intelligence completed with failed sources:")
        print("\n".join(failed))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
