"""Monte Carlo qualification probabilities for modern UCL league phases."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from .ucl_league_sim import rank_table
from .ucl_backtest import qualification_metrics
from .ucl_state_backtest import run as actual_states

ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS = ROOT / "data/ucl/clv/ucl_walk_forward_predictions.csv"
OUTPUT = ROOT / "data/ucl/clv/ucl_qualification_probabilities.csv"
REPORT = ROOT / "ml/football/reports/ucl_qualification_backtest.json"


def run(simulations: int = 2000, seed: int = 20260901) -> tuple[pd.DataFrame, dict]:
    if simulations <= 0:
        raise ValueError("simulations must be positive")
    predictions = pd.read_csv(PREDICTIONS)
    predictions = predictions[predictions.season.isin(["2024-25", "2025-26"]) & (predictions.stage == "league_phase")]
    actual, _ = actual_states()
    rng = np.random.default_rng(seed)
    output_rows = []
    for season, fixtures in predictions.groupby("season", sort=True):
        clubs = sorted(set(fixtures.home_club_id) | set(fixtures.away_club_id))
        counts = defaultdict(lambda: {"top8": 0, "top24": 0, "position_sum": 0.0})
        for _ in range(simulations):
            records = []
            for row in fixtures.to_dict("records"):
                u = rng.random(); outcome = "home" if u < row["p_home"] else "draw" if u < row["p_home"] + row["p_draw"] else "away"
                # Preserve the model's expected scoring shape while sampling a valid score.
                hg, ag = int(rng.poisson(max(float(row["expected_home_goals"]), .05))), int(rng.poisson(max(float(row["expected_away_goals"]), .05)))
                if outcome == "home" and hg <= ag: hg = ag + 1
                if outcome == "away" and ag <= hg: ag = hg + 1
                if outcome == "draw": hg = ag = min(hg, ag)
                records.append({"home_club_id": row["home_club_id"], "away_club_id": row["away_club_id"], "home_goals": hg, "away_goals": ag})
            ranking = rank_table(records, [{"club_id": club} for club in clubs])
            for position, club in enumerate(ranking, 1):
                counts[club]["position_sum"] += position
                counts[club]["top8"] += position <= 8; counts[club]["top24"] += position <= 24
        for club in clubs:
            hit = actual[(actual.season == season) & (actual.club_id == club)].iloc[0]
            output_rows.append({"season": season, "club_id": club, "top8_probability": counts[club]["top8"] / simulations,
                                "top24_probability": counts[club]["top24"] / simulations, "expected_position": counts[club]["position_sum"] / simulations,
                                "top8_actual": int(hit.qualification_bucket == "top8"), "top24_actual": int(hit.qualification_bucket != "eliminated25_36"),
                                "simulations": simulations})
    output = pd.DataFrame(output_rows)
    report = {"status": "ucl_qualification_probability_backtest_complete", "seasons": sorted(output.season.unique().tolist()),
              "clubs": len(output), "simulations_per_season": simulations,
              "overall": qualification_metrics(output), "by_season": {season: qualification_metrics(rows) for season, rows in output.groupby("season")},
              "restrictions": ["uses walk-forward match probabilities", "no odds", "no player data", "tie-break approximation follows rank_table"]}
    return output, report


def main() -> None:
    output, report = run(); OUTPUT.parent.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT, index=False); REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8"); print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
