"""Independent shallow-tree NFL challenger and leakage-safe calibration."""

from __future__ import annotations

import json
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

from .baselines import _metrics, fit_ridge, model_frame


def _regressor() -> GradientBoostingRegressor:
    return GradientBoostingRegressor(
        n_estimators=120, learning_rate=0.025, max_depth=2,
        min_samples_leaf=40, subsample=0.75, loss="huber", random_state=404,
    )


def _classifier() -> GradientBoostingClassifier:
    return GradientBoostingClassifier(
        n_estimators=100, learning_rate=0.025, max_depth=2,
        min_samples_leaf=40, subsample=0.75, random_state=405,
    )


def _normal_win_probability(margin: np.ndarray, residual_sd: float) -> np.ndarray:
    scale = max(float(residual_sd), 1.0)
    return np.array([0.5 * (1.0 + erf(float(value) / (scale * sqrt(2.0)))) for value in margin])


def _probability_metrics(actual: pd.Series, probability: pd.Series) -> dict[str, float | int]:
    keep = actual.notna() & probability.notna()
    y = actual[keep].astype(int)
    p = probability[keep].astype(float).clip(0.001, 0.999)
    return {
        "games": int(keep.sum()),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "accuracy": float(accuracy_score(y, p >= 0.5)),
    }


def challenger_frame(games: pd.DataFrame) -> pd.DataFrame:
    """Independent point-in-time inputs; market and tier outputs are excluded."""
    base = model_frame(games)
    for column in games.columns:
        if column.startswith(("home_off_", "away_off_", "home_def_", "away_def_")):
            base[column] = pd.to_numeric(games[column], errors="coerce")
    base["home_games_in_ewma"] = games.home_games_in_ewma
    base["away_games_in_ewma"] = games.away_games_in_ewma
    return base.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def run_challenger(
    feature_path: str = "data/nfl/features/weekly_epa.parquet",
) -> tuple[pd.DataFrame, dict]:
    games = pd.read_parquet(feature_path)
    games = games[games.season <= 2024].sort_values(["season", "week", "gameday", "game_id"]).copy()
    x = challenger_frame(games)
    ridge_columns = [c for c in model_frame(games) if c.startswith("diff_")] + ["rest_diff", "div_game", "week"]
    folds = []
    for season in range(2019, 2025):
        early = games.season < season - 1
        calibration = games.season == season - 1
        train = games.season < season
        test = games.season == season

        calibration_margin_model = _regressor().fit(x[early], games.loc[early, "margin"])
        calibration_margin = calibration_margin_model.predict(x[calibration])
        residual_sd = float(np.std(games.loc[calibration, "margin"].to_numpy() - calibration_margin, ddof=1))

        margin_model = _regressor().fit(x[train], games.loc[train, "margin"])
        total_model = _regressor().fit(x[train], games.loc[train, "total"])
        ridge = fit_ridge(x[train], games.loc[train, "margin"], ridge_columns)

        direct_base = _classifier().fit(x[early], games.loc[early, "margin"].gt(0).astype(int))
        calibration_raw = direct_base.predict_proba(x[calibration])[:, 1]
        platt = LogisticRegression(C=1.0, solver="lbfgs").fit(
            np.log(np.clip(calibration_raw, 0.001, 0.999) / np.clip(1.0 - calibration_raw, 0.001, 0.999)).reshape(-1, 1),
            games.loc[calibration, "margin"].gt(0).astype(int),
        )
        direct_model = _classifier().fit(x[train], games.loc[train, "margin"].gt(0).astype(int))

        fold = games.loc[test, [
            "game_id", "season", "week", "margin", "total", "spread_home_close",
            "total_line_close", "h2h_home_close", "h2h_away_close",
        ]].copy()
        fold["ridge_margin"] = ridge.predict(x[test])
        fold["tree_margin"] = margin_model.predict(x[test])
        fold["tree_total"] = total_model.predict(x[test])
        fold["margin_h2h_probability"] = _normal_win_probability(fold.tree_margin.to_numpy(), residual_sd)
        raw_probability = direct_model.predict_proba(x[test])[:, 1]
        raw_logit = np.log(np.clip(raw_probability, 0.001, 0.999) / np.clip(1.0 - raw_probability, 0.001, 0.999))
        fold["direct_h2h_probability"] = platt.predict_proba(raw_logit.reshape(-1, 1))[:, 1]
        market_home = 1.0 / fold.h2h_home_close
        market_away = 1.0 / fold.h2h_away_close
        fold["market_h2h_probability"] = market_home / (market_home + market_away)
        fold["home_win"] = fold.margin.gt(0).astype(int)
        folds.append(fold)
    predictions = pd.concat(folds, ignore_index=True)
    report = {
        "status": "independent_shadow",
        "test_seasons": list(range(2019, 2025)),
        "games": len(predictions),
        "vault_2025_predictions": int((predictions.season == 2025).sum()),
        "margin": {
            "ridge": _metrics(predictions.margin, predictions.ridge_margin),
            "shallow_tree": _metrics(predictions.margin, predictions.tree_margin),
            "closing_spread": _metrics(predictions.margin, -predictions.spread_home_close),
        },
        "total": {
            "shallow_tree": _metrics(predictions.total, predictions.tree_total),
            "closing_total": _metrics(predictions.total, predictions.total_line_close),
        },
        "h2h": {
            "margin_derived": _probability_metrics(predictions.home_win, predictions.margin_h2h_probability),
            "direct_calibrated": _probability_metrics(predictions.home_win, predictions.direct_h2h_probability),
            "closing_market": _probability_metrics(predictions.home_win, predictions.market_h2h_probability),
        },
        "independence": {
            "tier_outputs_used": False,
            "market_features_used": False,
            "official_prices_mutated": False,
        },
    }
    return predictions, report


if __name__ == "__main__":
    predictions, report = run_challenger()
    predictions.to_csv("data/nfl/predictions/step4_challenger.csv", index=False)
    Path("ml/nfl/reports/step4_challenger.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
