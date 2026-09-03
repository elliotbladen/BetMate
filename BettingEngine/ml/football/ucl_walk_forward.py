"""Leakage-safe expanding-window UCL match forecasts from imported results."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from .ucl_backtest import multiclass_metrics

ROOT = Path(__file__).resolve().parents[2]
MATCHES = ROOT / "data/ucl/matches/ucl_matches_openfootball.csv"
OUTPUT = ROOT / "data/ucl/clv/ucl_walk_forward_predictions.csv"
REPORT = ROOT / "ml/football/reports/ucl_walk_forward.json"


def _probs(rating_diff: float, draw_rate: float) -> tuple[float, float, float]:
    home_win = 1.0 / (1.0 + math.exp(-rating_diff / 320.0))
    draw = max(0.12, min(0.32, draw_rate))
    decisive = 1.0 - draw
    home = decisive * home_win; away = decisive * (1.0 - home_win)
    return home, draw, away


def run() -> tuple[pd.DataFrame, dict]:
    matches = pd.read_csv(MATCHES)
    if matches.empty:
        raise ValueError("sourced UCL matches are required")
    matches = matches.sort_values(["season", "kickoff_utc", "match_id"]).reset_index(drop=True)
    ratings = defaultdict(lambda: 1500.0); goals_for = defaultdict(list); goals_against = defaultdict(list)
    rows = []
    for item in matches.to_dict("records"):
        home, away = item["home_club_id"], item["away_club_id"]
        home_history = goals_for[home] + goals_against[away]
        away_history = goals_for[away] + goals_against[home]
        league_home = np.mean(home_history) if home_history else 1.45
        league_away = np.mean(away_history) if away_history else 1.20
        home_xg = max(.15, min(4.5, league_home + (ratings[home] - ratings[away]) / 1200.0 + .12))
        away_xg = max(.10, min(4.0, league_away - (ratings[home] - ratings[away]) / 1500.0))
        draw_rate = 1.0 / (1.0 + len(rows) / 500.0) * .27 + (1 - 1.0 / (1.0 + len(rows) / 500.0)) * .24
        p_home, p_draw, p_away = _probs(ratings[home] - ratings[away] + 55.0, draw_rate)
        rows.append({**item, "p_home": p_home, "p_draw": p_draw, "p_away": p_away,
                     "expected_home_goals": home_xg, "expected_away_goals": away_xg,
                     "rating_home_pre": ratings[home], "rating_away_pre": ratings[away]})
        hg, ag = int(item["home_goals"]), int(item["away_goals"])
        outcome = 1.0 if hg > ag else 0.0 if hg == ag else -1.0
        expected = p_home - p_away
        change = 20.0 * (outcome - expected)
        ratings[home] += change; ratings[away] -= change
        goals_for[home].append(hg); goals_against[home].append(ag)
        goals_for[away].append(ag); goals_against[away].append(hg)
    predictions = pd.DataFrame(rows)
    report = {"status": "ucl_expanding_window_backtest_complete", "games": len(predictions),
              "seasons": sorted(predictions.season.unique().tolist()), "market_fields_used": False,
              "modern_format_seasons": ["2024-25", "2025-26"], "legacy_format_separate": True,
              "overall": multiclass_metrics(predictions),
              "by_format": {
                  "modern": multiclass_metrics(predictions[predictions.season.isin(["2024-25", "2025-26"]) ]),
                  "legacy": multiclass_metrics(predictions[~predictions.season.isin(["2024-25", "2025-26"])])
              },
              "restrictions": ["results-only expanding window", "date-only source timestamps", "no xG or odds",
                               "qualifying and knockout outcome semantics require separate state evaluation",
                               "paper research only", "staking disabled"]}
    return predictions, report


def main() -> None:
    predictions, report = run(); OUTPUT.parent.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(OUTPUT, index=False); REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
