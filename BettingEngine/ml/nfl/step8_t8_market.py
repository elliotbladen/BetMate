"""NFL T8: does model-versus-open disagreement anticipate the closing line?"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .baselines import _metrics, fit_ridge


ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data/nfl/features/weekly_epa.parquet"
MODELS = ROOT / "data/nfl/predictions/step4_challenger.csv"
PREDICTIONS = ROOT / "data/nfl/predictions/step8_t8_market_disagreement.csv"
REPORT = ROOT / "ml/nfl/reports/step8_t8_market.json"


def add_market_disagreement(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["open_implied_margin"] = -out.spread_home_open
    out["close_implied_margin"] = -out.spread_home_close
    # Positive target means the closing market rated the home team more strongly.
    out["spread_move_home_strength"] = out.close_implied_margin - out.open_implied_margin
    out["ridge_spread_disagreement"] = out.ridge_margin - out.open_implied_margin
    out["tree_spread_disagreement"] = out.tree_margin - out.open_implied_margin
    out["spread_model_agreement"] = np.sign(out.ridge_spread_disagreement) == np.sign(out.tree_spread_disagreement)
    out["total_market_move"] = out.total_line_close - out.total_line_open
    out["tree_total_disagreement"] = out.tree_total - out.total_line_open
    return out


def _direction_summary(target: pd.Series, signal: pd.Series, threshold: float) -> dict:
    valid = target.notna() & signal.notna() & target.ne(0) & signal.abs().ge(threshold)
    correct = np.sign(target[valid]) == np.sign(signal[valid])
    return {"threshold_points": threshold, "games": int(valid.sum()),
            "direction_accuracy": float(correct.mean()) if len(correct) else None,
            "mean_market_move_points": float(target[valid].abs().mean()) if valid.any() else None}


def run_audit() -> tuple[pd.DataFrame, dict]:
    market = pd.read_parquet(FEATURES)[["game_id", "spread_home_open", "total_line_open"]]
    models = pd.read_csv(MODELS)
    games = add_market_disagreement(models.merge(market, on="game_id", validate="one_to_one"))
    games = games[games.season.between(2019, 2024)].sort_values(["season", "week", "game_id"]).copy()
    outputs = []
    spread_features = ["ridge_spread_disagreement", "tree_spread_disagreement", "spread_model_agreement"]
    for season in range(2020, 2025):
        train, test = games.season.lt(season), games.season.eq(season)
        spread_train = games.loc[train].dropna(subset=spread_features + ["spread_move_home_strength"])
        total_train = games.loc[train].dropna(subset=["tree_total_disagreement", "total_market_move"])
        spread_model = fit_ridge(spread_train, spread_train["spread_move_home_strength"], spread_features, alpha=25.0)
        total_model = fit_ridge(total_train, total_train["total_market_move"], ["tree_total_disagreement"], alpha=25.0)
        fold = games.loc[test, ["game_id", "season", "week", "margin", "total", "spread_home_open",
                                "spread_home_close", "total_line_open", "total_line_close"] + spread_features +
                               ["tree_total_disagreement", "spread_move_home_strength", "total_market_move"]].copy()
        fold["predicted_spread_move"] = spread_model.predict(games.loc[test])
        fold["predicted_total_move"] = total_model.predict(games.loc[test])
        outputs.append(fold)
    predictions = pd.concat(outputs, ignore_index=True)
    spread_valid = predictions.dropna(subset=["spread_home_open", "spread_home_close", "predicted_spread_move"])
    total_valid = predictions.dropna(subset=["total_line_open", "total_line_close", "predicted_total_move"])
    report = {
        "status": "t8_historical_market_disagreement_diagnostic",
        "games": len(predictions), "test_seasons": list(range(2020, 2025)), "vault_2025_predictions": 0,
        "spread": {
            "opener_to_close_baseline": _metrics(spread_valid.close_implied_margin if "close_implied_margin" in spread_valid else -spread_valid.spread_home_close,
                                                  -spread_valid.spread_home_open),
            "calibrated_t8_to_close": _metrics(-spread_valid.spread_home_close,
                                                -spread_valid.spread_home_open + spread_valid.predicted_spread_move),
            "raw_ridge_direction": [_direction_summary(predictions.spread_move_home_strength,
                                                        predictions.ridge_spread_disagreement, x) for x in (0.0, 1.0, 2.0, 3.0)],
            "raw_tree_direction": [_direction_summary(predictions.spread_move_home_strength,
                                                       predictions.tree_spread_disagreement, x) for x in (0.0, 1.0, 2.0, 3.0)],
        },
        "total": {
            "opener_to_close_baseline": _metrics(total_valid.total_line_close, total_valid.total_line_open),
            "calibrated_t8_to_close": _metrics(total_valid.total_line_close,
                                                total_valid.total_line_open + total_valid.predicted_total_move),
            "raw_tree_direction": [_direction_summary(predictions.total_market_move,
                                                       predictions.tree_total_disagreement, x) for x in (0.0, 1.0, 2.0, 3.0)],
        },
        "restrictions": ["after-open diagnostic only", "no bookmaker-dispersion history available",
                         "historical true-opener audit incomplete", "no prices or ROI claimed", "staking disabled"],
    }
    return predictions, report


def main() -> None:
    predictions, report = run_audit()
    PREDICTIONS.parent.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(PREDICTIONS, index=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
