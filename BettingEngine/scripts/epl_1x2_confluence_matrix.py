#!/usr/bin/env python3
"""Build the historical EPL 1X2 matrix for the current season's teams.

The live 2026/27 season is excluded so the matrix can be used prospectively
without leaking current-season outcomes.
"""
from pathlib import Path

from efl_championship_confluence_matrix import build_workbook, load_rows


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ml/football/data/epl/matches/epl_matches.csv"
OUTPUT = ROOT / "outputs/football/epl/epl_1x2_confluence_matrix.xlsx"
SEASONS = ("2022/23", "2023/24", "2024/25", "2025/26")
CURRENT_TEAMS = (
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
    "Chelsea", "Coventry", "Crystal Palace", "Everton", "Fulham", "Hull",
    "Ipswich", "Leeds", "Liverpool", "Man City", "Man United", "Newcastle",
    "Nott'm Forest", "Sunderland", "Tottenham",
)


def main() -> None:
    rows = load_rows(SOURCE, SEASONS)
    build_workbook(
        rows,
        list(CURRENT_TEAMS),
        SEASONS,
        "1x2",
        OUTPUT,
        league_name="English Premier League",
        holdout_note=(
            "The live 2026/27 season is excluded; no current-season results enter "
            "these calculations."
        ),
    )
    print(f"Loaded {len(rows)} historical matches")
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
