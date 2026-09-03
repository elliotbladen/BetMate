"""Replay modern UCL league phases and validate qualification-state labels."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .ucl_league_sim import rank_table

ROOT = Path(__file__).resolve().parents[2]
MATCHES = ROOT / "data/ucl/matches/ucl_matches_openfootball.csv"
OUTPUT = ROOT / "data/ucl/clv/ucl_league_phase_actual_states.csv"
REPORT = ROOT / "ml/football/reports/ucl_state_backtest.json"


def run() -> tuple[pd.DataFrame, dict]:
    source = pd.read_csv(MATCHES)
    modern = source[source["season"].isin(["2024-25", "2025-26"]) & (source["stage"] == "league_phase")].copy()
    if modern.empty:
        raise ValueError("modern league-phase matches are required")
    states = []
    for season, games in modern.groupby("season", sort=True):
        clubs = sorted(set(games.home_club_id) | set(games.away_club_id))
        if len(clubs) != 36 or len(games) != 144:
            raise ValueError(f"{season} must contain 36 clubs and 144 league-phase matches")
        ranking = rank_table(games.to_dict("records"), [{"club_id": c} for c in clubs])
        for position, club_id in enumerate(ranking, start=1):
            bucket = "top8" if position <= 8 else "playoff9_24" if position <= 24 else "eliminated25_36"
            states.append({"season": season, "club_id": club_id, "final_position": position, "qualification_bucket": bucket,
                           "format": "single_league_phase", "rules_version": "ucl-2026-27-regulations-v1"})
    output = pd.DataFrame(states)
    report = {"status": "ucl_modern_state_replay_complete", "seasons": sorted(output.season.unique().tolist()),
              "clubs_labelled": len(output), "matches_replayed": int(len(modern)),
              "bucket_counts": output.groupby(["season", "qualification_bucket"]).size().unstack(fill_value=0).to_dict(),
              "checks": {"clubs_per_season_36": bool((output.groupby("season").size() == 36).all()),
                         "top8_per_season_8": bool(((output.qualification_bucket == "top8").groupby(output.season).sum() == 8).all()),
                         "playoff_per_season_16": bool(((output.qualification_bucket == "playoff9_24").groupby(output.season).sum() == 16).all()),
                         "eliminated_per_season_12": bool(((output.qualification_bucket == "eliminated25_36").groupby(output.season).sum() == 12).all())},
              "forecast_metrics": "pending probabilistic qualification simulation",
              "restrictions": ["historical labels only", "no odds", "no player data", "tie-break approximation follows stored rank_table contract"]}
    return output, report


def main() -> None:
    output, report = run(); OUTPUT.parent.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT, index=False); REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
