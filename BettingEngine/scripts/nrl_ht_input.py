#!/usr/bin/env python3
"""
scripts/nrl_ht_input.py

Manual halftime stats entry for NRL games.
At halftime: run this, enter stats from the TV/NRL app, get pricing output.

Usage:
    uv run python scripts/nrl_ht_input.py
    uv run python scripts/nrl_ht_input.py --round 15 --home Warriors --away Sharks
    uv run python scripts/nrl_ht_input.py --file path/to/existing_stats.json  # re-run pricing only
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
HALFTIME_DIR = _ROOT / "data" / "nrl" / "halfTime"


def ask(prompt: str, default=None, cast=None):
    """Prompt user for input, with optional default and type cast."""
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"  {prompt}{suffix}: ").strip()
        if not raw and default is not None:
            return default
        if not raw:
            continue
        if cast:
            try:
                return cast(raw)
            except ValueError:
                print(f"    → Enter a valid number")
                continue
        return raw


def ask_int(prompt: str, default: int = 0) -> int:
    return ask(prompt, default=default, cast=int)


def ask_float(prompt: str, default: float = 0.0) -> float:
    return ask(prompt, default=default, cast=float)


def collect_stats(round_num: int, season: int, home: str, away: str) -> dict:
    print(f"\n{'='*55}")
    print(f"  HALFTIME STATS — {home} vs {away}")
    print(f"  R{round_num} {season}")
    print(f"{'='*55}")
    print("  (press Enter to skip optional stats — they default to 0)\n")

    print("  SCORE")
    home_score = ask_int(f"{home} HT score")
    away_score = ask_int(f"{away} HT score")

    print("\n  TRIES & CONVERSIONS")
    home_tries = ask_int(f"{home} tries")
    away_tries = ask_int(f"{away} tries")
    home_conv  = ask_int(f"{home} conversions made")
    away_conv  = ask_int(f"{away} conversions made")

    print("\n  ERRORS")
    home_errors = ask_int(f"{home} errors")
    away_errors = ask_int(f"{away} errors")

    print("\n  SET RESTARTS (6-agains received)")
    home_restarts = ask_int(f"{home} set restarts received")
    away_restarts = ask_int(f"{away} set restarts received")

    print("\n  RUN METRES (optional — press Enter to skip)")
    home_metres = ask_int(f"{home} run metres", default=0)
    away_metres = ask_int(f"{away} run metres", default=0)

    print("\n  POSSESSION % (optional)")
    home_poss = ask_float(f"{home} possession %", default=0.0)
    away_poss = ask_float(f"{away} possession %", default=0.0)

    print("\n  INSIDE 20m POSSESSIONS (optional)")
    home_in20 = ask_int(f"{home} inside 20m possessions", default=0)
    away_in20 = ask_int(f"{away} inside 20m possessions", default=0)

    return {
        "season": season,
        "round": round_num,
        "game_date": date.today().isoformat(),
        "home_team": home,
        "away_team": away,
        "source": "manual_entry",
        "collected_at": datetime.utcnow().isoformat() + "Z",
        "home_ht_score": home_score,
        "away_ht_score": away_score,
        "home_tries": home_tries,
        "away_tries": away_tries,
        "home_conversions_made": home_conv,
        "away_conversions_made": away_conv,
        "home_errors": home_errors,
        "away_errors": away_errors,
        "home_set_restarts_received": home_restarts,
        "away_set_restarts_received": away_restarts,
        "home_run_metres": home_metres,
        "away_run_metres": away_metres,
        "home_possession_pct": home_poss,
        "away_possession_pct": away_poss,
        "home_inside_20_possessions": home_in20,
        "away_inside_20_possessions": away_in20,
        "home_completion_pct": 0.0,
        "away_completion_pct": 0.0,
        "home_penalties_conceded": 0,
        "away_penalties_conceded": 0,
        "notes": "",
    }


def save_stats(stats: dict) -> Path:
    round_dir = HALFTIME_DIR / f"R{stats['round']:02d}"
    round_dir.mkdir(parents=True, exist_ok=True)
    home_nick = stats["home_team"].split()[-1].lower()
    away_nick = stats["away_team"].split()[-1].lower()
    filename = f"{stats['game_date']}_{home_nick}_vs_{away_nick}_stats.json"
    path = round_dir / filename
    path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"\n  Saved → {path}")
    return path


def run_pricing(stats_path: Path) -> None:
    pricing_script = _ROOT / "scripts" / "halfTime_price_nrl.py"
    cmd = [sys.executable, str(pricing_script), "--file", str(stats_path), "--save"]
    subprocess.run(cmd)


def main():
    p = argparse.ArgumentParser(description="Manual NRL halftime stats entry")
    p.add_argument("--round",  type=int, default=15)
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--home",   type=str, default="New Zealand Warriors")
    p.add_argument("--away",   type=str, default="Cronulla-Sutherland Sharks")
    p.add_argument("--file",   type=Path, help="Re-run pricing on existing stats JSON")
    args = p.parse_args()

    if args.file:
        stats_path = args.file
        if not stats_path.exists():
            print(f"File not found: {stats_path}")
            sys.exit(1)
        print(f"Loaded: {stats_path}")
    else:
        stats = collect_stats(args.round, args.season, args.home, args.away)
        stats_path = save_stats(stats)

    print("\nRunning pricing model...")
    run_pricing(stats_path)


if __name__ == "__main__":
    main()
