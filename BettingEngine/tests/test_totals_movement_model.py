import pandas as pd

from scripts.line_mover.totals_movement_model import build_features, multiclass_brier


def test_rolling_features_do_not_use_current_match_score():
    rows = pd.DataFrame([
        {"date": pd.Timestamp("2024-03-01"), "home_team": "A", "away_team": "B",
         "home_score": 10, "away_score": 20, "total_open": 40, "total_close": 41,
         "home_odds_open": 2.0, "away_odds_open": 2.0, "over_price_open": 1.9,
         "under_price_open": 1.9, "kickoff_hour": 19},
        {"date": pd.Timestamp("2024-03-08"), "home_team": "A", "away_team": "B",
         "home_score": 100, "away_score": 100, "total_open": 42, "total_close": 41,
         "home_odds_open": 2.0, "away_odds_open": 2.0, "over_price_open": 1.9,
         "under_price_open": 1.9, "kickoff_hour": 19},
    ])
    features = build_features(rows)
    assert pd.isna(features.loc[0, "home_total_l5"])
    assert features.loc[1, "home_total_l5"] == 30
    assert features.loc[1, "away_total_l5"] == 30


def test_multiclass_brier_is_zero_for_perfect_predictions():
    y = pd.Series(["DOWN", "EVEN", "UP"])
    probabilities = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    assert multiclass_brier(y, probabilities, ["DOWN", "EVEN", "UP"]) == 0
