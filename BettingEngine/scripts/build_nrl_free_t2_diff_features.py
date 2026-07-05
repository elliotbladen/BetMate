#!/usr/bin/env python3
"""
Build compact NRL free-data T2 differential features.

This script reads the expanded free T2 matrix and adds direct home-minus-away
differences for the core rolling stats. The goal is to give the model a more
compact, matchup-oriented feature set than the wide raw home/away block.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "ml" / "results" / "features_nrl_free_t2.csv"
DEFAULT_OUT = ROOT / "ml" / "results" / "features_nrl_free_t2_diff.csv"


CORE_STATS = [
    "run_metres",
    "post_contact_metres",
    "line_breaks",
    "line_break_assists",
    "tackle_busts",
    "off_loads",
    "effective_offloads",
    "tackles",
    "missed_tackles",
    "tackle_opp20",
    "tackle_opp_half",
    "forced_drop_outs",
    "possession_percentage",
    "territory",
    "complete_sets",
    "total_sets",
    "errors",
    "in_complete_sets",
    "penalties_conceded",
    "kick_metres",
    "play_the_balls",
    "general_play_pass",
    "supports",
    "options",
    "line_engagements",
]


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_rows(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def num(v) -> float:
    try:
        return float(v) if v not in (None, "", "None") else 0.0
    except ValueError:
        return 0.0


def build_rows(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        out_row = dict(row)
        for stat in CORE_STATS:
            for suffix in ("last5", "season"):
                h_key = f"home_nrl_t2_{stat}_{suffix}"
                a_key = f"away_nrl_t2_{stat}_{suffix}"
                d_key = f"nrl_t2_diff_{stat}_{suffix}"
                out_row[d_key] = f"{num(row.get(h_key)) - num(row.get(a_key)):.4f}"

        out_row["nrl_t2_diff_games_played_last5"] = (
            f"{num(row.get('home_nrl_t2_games_played_last5')) - num(row.get('away_nrl_t2_games_played_last5')):.4f}"
        )
        out_row["nrl_t2_diff_games_played_season"] = (
            f"{num(row.get('home_nrl_t2_games_played_season')) - num(row.get('away_nrl_t2_games_played_season')):.4f}"
        )
        out.append(out_row)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build compact NRL free T2 differential features")
    parser.add_argument("--features", default=str(DEFAULT_IN))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    rows = load_rows(Path(args.features))
    out = build_rows(rows)
    write_rows(out, Path(args.out))

    diff_cols = [
        f"nrl_t2_diff_{stat}_{suffix}"
        for stat in CORE_STATS
        for suffix in ("last5", "season")
    ] + ["nrl_t2_diff_games_played_last5", "nrl_t2_diff_games_played_season"]
    print(f"Wrote {args.out}")
    print(f"Added {len(diff_cols)} compact diff columns")


if __name__ == "__main__":
    main()
