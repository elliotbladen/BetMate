"""Leakage-safe NFL Elo and ridge baselines with rolling-origin evaluation."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


MARGIN_STATS = (
    "off_pass_epa", "off_rush_epa", "off_success_rate",
    "off_early_down_epa", "off_explosive_rate", "off_sack_rate",
    "def_pass_epa", "def_rush_epa", "def_success_rate",
    "def_early_down_epa", "def_explosive_rate", "def_sack_rate",
)


@dataclass(frozen=True)
class RidgeModel:
    columns: tuple[str, ...]
    mean: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        x = frame.loc[:, self.columns].astype(float).to_numpy()
        z = (x - self.mean) / self.scale
        return np.column_stack([np.ones(len(z)), z]) @ self.coefficients


def model_frame(games: pd.DataFrame) -> pd.DataFrame:
    """Create football-shaped predictors without scores or market prices."""
    out = pd.DataFrame(index=games.index)
    for stat in MARGIN_STATS:
        home = games[f"home_{stat}"].astype(float)
        away = games[f"away_{stat}"].astype(float)
        out[f"diff_{stat}"] = home - away
        out[f"sum_{stat}"] = home + away
    out["rest_diff"] = games.home_rest.astype(float) - games.away_rest.astype(float)
    out["rest_sum"] = games.home_rest.astype(float) + games.away_rest.astype(float)
    out["div_game"] = games.div_game.astype(float)
    out["week"] = games.week.astype(float)
    for name in (
        "dynamic_kickoff_rule", "onside_anytime_when_trailing",
        "kickoff_touchback_to_35", "regular_season_ot_both_possess",
        "onside_2026_alignment_rule",
    ):
        out[name] = games[name].astype(float) if name in games else 0.0
    return out.fillna(0.0)


def fit_ridge(frame: pd.DataFrame, target: pd.Series, columns: list[str], alpha: float = 25.0) -> RidgeModel:
    x = frame.loc[:, columns].astype(float).to_numpy()
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale == 0] = 1.0
    z = (x - mean) / scale
    design = np.column_stack([np.ones(len(z)), z])
    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ target.astype(float).to_numpy())
    return RidgeModel(tuple(columns), mean, scale, coefficients)


def elo_predictions(games: pd.DataFrame, k: float = 20.0, home_points: float = 2.2) -> pd.Series:
    """Predict chronologically, updating ratings only after each final score."""
    ratings: dict[str, float] = {}
    predictions = pd.Series(index=games.index, dtype=float)
    ordered = games.sort_values(["gameday", "game_id"])
    for idx, game in ordered.iterrows():
        home = ratings.get(game.home_team, 1500.0)
        away = ratings.get(game.away_team, 1500.0)
        predictions.at[idx] = (home - away) / 25.0 + home_points
        expected = 1.0 / (1.0 + 10.0 ** (-(home - away + home_points * 25.0) / 400.0))
        actual = 1.0 if game.margin > 0 else 0.0 if game.margin < 0 else 0.5
        margin_mult = np.log(abs(float(game.margin)) + 1.0) * 2.2 / (
            ((home - away) * 0.001) + 2.2
        )
        change = k * margin_mult * (actual - expected)
        ratings[game.home_team] = home + change
        ratings[game.away_team] = away - change
    return predictions


def _metrics(actual: pd.Series, prediction: pd.Series) -> dict[str, float | int]:
    keep = actual.notna() & prediction.notna()
    error = prediction[keep].astype(float) - actual[keep].astype(float)
    return {
        "games": int(keep.sum()),
        "mae": float(error.abs().mean()),
        "rmse": float(np.sqrt(np.mean(error ** 2))),
    }


def rolling_origin_evaluation(games: pd.DataFrame, first_test: int = 2019, last_test: int = 2024) -> tuple[pd.DataFrame, dict]:
    """Train on prior seasons only; the 2025 vault is never read into a fit."""
    games = games.sort_values(["season", "week", "gameday", "game_id"]).copy()
    if int(games.season.max()) >= 2025:
        development = games[games.season <= last_test].copy()
    else:
        development = games.copy()
    predictors = model_frame(development)
    margin_columns = [c for c in predictors if c.startswith("diff_")] + ["rest_diff", "div_game", "week"]
    total_columns = [c for c in predictors if c.startswith("sum_")] + [
        "rest_sum", "div_game", "week", "dynamic_kickoff_rule",
        "onside_anytime_when_trailing", "kickoff_touchback_to_35",
        "regular_season_ot_both_possess", "onside_2026_alignment_rule",
    ]
    development["elo_margin"] = elo_predictions(development)
    rows = []
    for season in range(first_test, last_test + 1):
        train_mask = development.season < season
        test_mask = development.season == season
        margin_model = fit_ridge(predictors[train_mask], development.loc[train_mask, "margin"], margin_columns)
        total_model = fit_ridge(predictors[train_mask], development.loc[train_mask, "total"], total_columns)
        fold = development.loc[test_mask, [
            "game_id", "season", "week", "margin", "total", "spread_home_open",
            "spread_home_close", "total_line_open", "total_line_close",
        ]].copy()
        fold["ridge_margin"] = margin_model.predict(predictors[test_mask])
        fold["ridge_total"] = total_model.predict(predictors[test_mask])
        fold["elo_margin"] = development.loc[test_mask, "elo_margin"]
        rows.append(fold)
    predictions = pd.concat(rows, ignore_index=True)
    close_margin = -predictions.spread_home_close
    open_margin = -predictions.spread_home_open
    summary = {
        "status": "development_only_2025_vault_untouched",
        "train_start": int(development.season.min()),
        "test_seasons": list(range(first_test, last_test + 1)),
        "ridge_margin": _metrics(predictions.margin, predictions.ridge_margin),
        "elo_margin": _metrics(predictions.margin, predictions.elo_margin),
        "closing_spread_as_margin": _metrics(predictions.margin, close_margin),
        "opening_spread_as_margin": _metrics(predictions.margin, open_margin),
        "ridge_margin_to_close": _metrics(close_margin, predictions.ridge_margin),
        "opener_to_close": _metrics(close_margin, open_margin),
        "ridge_total": _metrics(predictions.total, predictions.ridge_total),
        "closing_total": _metrics(predictions.total, predictions.total_line_close),
        "opening_total": _metrics(predictions.total, predictions.total_line_open),
        "ridge_total_to_close": _metrics(predictions.total_line_close, predictions.ridge_total),
        "total_opener_to_close": _metrics(predictions.total_line_close, predictions.total_line_open),
    }
    return predictions, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", default="data/nfl/features/weekly_epa.parquet")
    parser.add_argument("--report", default="ml/nfl/reports/step2_baselines.json")
    parser.add_argument("--predictions", default="data/nfl/predictions/step2_rolling_origin.csv")
    args = parser.parse_args()
    games = pd.read_parquet(args.features)
    predictions, summary = rolling_origin_evaluation(games)
    report = Path(args.report)
    output = Path(args.predictions)
    report.parent.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    predictions.to_csv(output, index=False)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
