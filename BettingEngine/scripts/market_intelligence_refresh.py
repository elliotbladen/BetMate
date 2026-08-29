#!/usr/bin/env python3
"""Refresh maintained injury/news feeds and rebuild the causal event log."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
BETMATE_ROOT = ENGINE_ROOT.parent
PYTHON = Path("/usr/local/bin/python3")


def detect_afl_round(season: int) -> int | None:
    """Use the latest prepared AFL round instead of a calendar approximation.

    AFL bye rounds make a simple weeks-since-Round-1 calculation drift.  Round
    preparation is the local source of truth used by the pricing pipeline.
    """
    prep_root = ENGINE_ROOT / "outputs" / "afl_round_prep"
    rounds: list[int] = []
    for path in prep_root.glob(f"r*_{season}"):
        match = re.fullmatch(rf"r(\d+)_{season}", path.name)
        if match and path.is_dir():
            rounds.append(int(match.group(1)))
    return max(rounds) if rounds else None


def run(name: str, args: list[str], cwd: Path = BETMATE_ROOT) -> bool:
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {name}", flush=True)
    result = subprocess.run([str(PYTHON), *args], cwd=cwd)
    if result.returncode:
        print(f"ERROR: {name} exited {result.returncode}", file=sys.stderr, flush=True)
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--sport", choices=("NRL", "AFL", "ALL"), default="ALL")
    args = parser.parse_args()

    steps: list[tuple[str, list[str], Path]] = []
    if args.sport in {"NRL", "ALL"}:
        steps.extend([
            ("NRL injuries", ["scrapers/nrl_injuries.py", "--season", str(args.season)], BETMATE_ROOT),
            ("NRL team news", ["scrapers/nrl_team_news.py"], BETMATE_ROOT),
            ("NRL market-moving news", ["scrapers/nrl_news_flags.py", "--season", str(args.season)], BETMATE_ROOT),
        ])
    if args.sport in {"AFL", "ALL"}:
        afl_round = detect_afl_round(args.season)
        afl_injury_command = ["scrapers/afl_injuries.py", "--season", str(args.season)]
        if afl_round is not None:
            afl_injury_command.extend(["--round", str(afl_round)])
            print(f"AFL injury refresh pinned to prepared round {afl_round}", flush=True)
        steps.append((
            "AFL injuries",
            afl_injury_command,
            BETMATE_ROOT,
        ))
    steps.append((
        "Market event log",
        ["scripts/build_market_event_log.py", "--season", str(args.season)],
        BETMATE_ROOT,
    ))

    failures = [name for name, command, cwd in steps if not run(name, command, cwd)]
    if failures:
        print("Failed steps: " + ", ".join(failures), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
