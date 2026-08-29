#!/usr/bin/env python3
"""Train and serve a leakage-safe NRL totals line-movement model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, log_loss, mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = ROOT / "outputs/nrl_weekly_review/historical/latest.xlsx"
MODEL_DIR = ROOT / "data/line_movement/models"
REPORT_DIR = ROOT / "outputs/line_movement"
MODEL_PATH = MODEL_DIR / "nrl_totals_movement.joblib"
REPORT_PATH = REPORT_DIR / "nrl_totals_movement_backtest.json"

FEATURES = [
    "total_open", "home_implied", "market_balance", "over_price_open",
    "under_price_open", "price_skew", "month",
    "home_for_l5", "home_against_l5", "away_for_l5", "away_against_l5",
    "home_total_l5", "away_total_l5", "combined_expected_total",
    "combined_total_volatility", "home_move_prior", "away_move_prior",
    "pair_move_prior", "home_games_prior", "away_games_prior",
]
CLASSES = np.array(["DOWN", "EVEN", "UP"])


def _number(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[name], errors="coerce")


def load_source(path: Path = SOURCE) -> pd.DataFrame:
    df = pd.read_excel(path, header=1)
    df["date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df[df["date"].notna() & (df["date"] >= "2024-01-01")].copy()
    rename = {
        "Home Team": "home_team", "Away Team": "away_team", "Venue": "venue",
        "Home Score": "home_score", "Away Score": "away_score",
        "Home Odds Open": "home_odds_open", "Away Odds Open": "away_odds_open",
        "Total Score Open": "total_open", "Total Score Close": "total_close",
        "Total Score Over Open": "over_price_open",
        "Total Score Under Open": "under_price_open",
    }
    df = df.rename(columns=rename)
    for col in rename.values():
        if col not in df:
            df[col] = np.nan
    kickoff = df["Kick Off (local)"] if "Kick Off (local)" in df else pd.Series(pd.NaT, index=df.index)
    df["kickoff_hour"] = pd.to_datetime(kickoff, errors="coerce").dt.hour
    for col in ["home_score", "away_score", "home_odds_open", "away_odds_open",
                "total_open", "total_close", "over_price_open", "under_price_open"]:
        df[col] = _number(df, col)
    df = df[df["total_open"].gt(0) & df["total_close"].gt(0)].copy()
    df = df.sort_values(["date", "home_team", "away_team"]).reset_index(drop=True)
    return df


def build_features(raw: pd.DataFrame) -> pd.DataFrame:
    """Build only features knowable before each match."""
    df = raw.copy().sort_values(["date", "home_team", "away_team"]).reset_index(drop=True)
    df["actual_total"] = df["home_score"] + df["away_score"]
    df["total_move"] = df["total_close"] - df["total_open"]
    df["direction"] = np.select(
        [df["total_move"] < -0.25, df["total_move"] > 0.25],
        ["DOWN", "UP"], default="EVEN",
    )
    home_imp = 1 / df["home_odds_open"]
    away_imp = 1 / df["away_odds_open"]
    df["home_implied"] = home_imp / (home_imp + away_imp)
    df["market_balance"] = (df["home_implied"] - 0.5).abs()
    df["price_skew"] = (1 / df["over_price_open"]) - (1 / df["under_price_open"])
    df["month"] = df["date"].dt.month

    state: dict[str, dict[str, list[float]]] = {}
    movement_state: dict[str, list[float]] = {}
    pair_state: dict[tuple[str, str], list[float]] = {}
    records = []
    for _, row in df.iterrows():
        home, away = row["home_team"], row["away_team"]
        hs = state.setdefault(home, {"for": [], "against": [], "total": []})
        aws = state.setdefault(away, {"for": [], "against": [], "total": []})
        hm = movement_state.setdefault(home, [])
        am = movement_state.setdefault(away, [])
        pair = tuple(sorted((home, away)))
        pm = pair_state.setdefault(pair, [])

        def avg(values: list[float], n: int = 5) -> float:
            return float(np.mean(values[-n:])) if values else np.nan

        def std(values: list[float], n: int = 5) -> float:
            return float(np.std(values[-n:])) if len(values) >= 2 else np.nan

        def nan_avg(values: list[float]) -> float:
            available = [value for value in values if pd.notna(value)]
            return float(np.mean(available)) if available else np.nan

        rec = row.to_dict()
        rec.update({
            "home_for_l5": avg(hs["for"]), "home_against_l5": avg(hs["against"]),
            "away_for_l5": avg(aws["for"]), "away_against_l5": avg(aws["against"]),
            "home_total_l5": avg(hs["total"]), "away_total_l5": avg(aws["total"]),
            "combined_expected_total": nan_avg([
                avg(hs["for"]), avg(hs["against"]), avg(aws["for"]), avg(aws["against"])
            ]),
            "combined_total_volatility": nan_avg([std(hs["total"]), std(aws["total"])]),
            "home_move_prior": avg(hm, 10), "away_move_prior": avg(am, 10),
            "pair_move_prior": avg(pm, 5),
            "home_games_prior": len(hs["total"]), "away_games_prior": len(aws["total"]),
        })
        records.append(rec)

        if pd.notna(row["actual_total"]):
            hs["for"].append(float(row["home_score"])); hs["against"].append(float(row["away_score"]))
            aws["for"].append(float(row["away_score"])); aws["against"].append(float(row["home_score"]))
            hs["total"].append(float(row["actual_total"])); aws["total"].append(float(row["actual_total"]))
        hm.append(float(row["total_move"])); am.append(float(row["total_move"])); pm.append(float(row["total_move"]))
    return pd.DataFrame(records)


def _pipeline(model) -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ("scale", StandardScaler()),
        ("model", model),
    ])


def multiclass_brier(y: pd.Series, probs: np.ndarray, classes: np.ndarray) -> float:
    probs = np.asarray(probs, dtype=float)
    classes = np.asarray(classes)
    actual = np.column_stack([(y.to_numpy() == label).astype(float) for label in classes])
    return float(np.mean(np.sum((probs - actual) ** 2, axis=1)))


def train_backtest(df: pd.DataFrame) -> tuple[dict, object]:
    train = df[df["date"].dt.year == 2024]
    calibration = df[df["date"].dt.year == 2025]
    test = df[df["date"].dt.year == 2026]
    if min(len(train), len(calibration), len(test)) < 50:
        raise RuntimeError("Need at least 50 matches in each of 2024, 2025 and 2026")

    base = _pipeline(HistGradientBoostingClassifier(
        max_iter=180, learning_rate=0.045, max_leaf_nodes=10,
        min_samples_leaf=18, l2_regularization=2.0, random_state=42,
    ))
    base.fit(train[FEATURES], train["direction"])
    calibrated = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
    calibrated.fit(calibration[FEATURES], calibration["direction"])
    probs = calibrated.predict_proba(test[FEATURES])
    pred = calibrated.classes_[np.argmax(probs, axis=1)]
    max_prob = probs.max(axis=1)

    reg = _pipeline(HistGradientBoostingRegressor(
        loss="absolute_error", max_iter=180, learning_rate=0.045, max_leaf_nodes=10,
        min_samples_leaf=18, l2_regularization=2.0, random_state=42,
    ))
    reg.fit(pd.concat([train, calibration])[FEATURES], pd.concat([train, calibration])["total_move"])
    move_pred = reg.predict(test[FEATURES])
    majority = train["direction"].value_counts().idxmax()
    moved = test["direction"].ne("EVEN").to_numpy()
    confident = max_prob >= 0.55
    zero_move_mae = float(test["total_move"].abs().mean())
    model_accuracy = float(accuracy_score(test["direction"], pred))
    baseline_accuracy = float((test["direction"] == majority).mean())
    movement_mae = float(mean_absolute_error(test["total_move"], move_pred))
    approved = model_accuracy >= baseline_accuracy + 0.02 and movement_mae <= zero_move_mae * 0.95
    report = {
        "split": {"train_2024": len(train), "calibrate_2025": len(calibration), "test_2026": len(test)},
        "class_counts": {str(k): int(v) for k, v in df["direction"].value_counts().items()},
        "test": {
            "accuracy": model_accuracy,
            "majority_baseline_accuracy": baseline_accuracy,
            "log_loss": float(log_loss(test["direction"], probs, labels=calibrated.classes_)),
            "multiclass_brier": multiclass_brier(test["direction"], probs, calibrated.classes_),
            "movement_mae_points": movement_mae,
            "zero_move_baseline_mae_points": zero_move_mae,
            "movement_rmse_points": float(mean_squared_error(test["total_move"], move_pred) ** 0.5),
            "mean_actual_move": float(test["total_move"].mean()),
            "directional_accuracy_when_market_moved": float(accuracy_score(test.loc[moved, "direction"], pred[moved])),
            "confidence_55_coverage": float(confident.mean()),
            "confidence_55_accuracy": float(accuracy_score(test.loc[confident, "direction"], pred[confident])) if confident.any() else None,
        },
        "approved_for_live_confidence": approved,
        "approval_rule": "accuracy >= majority baseline + 2pp and movement MAE <= zero-move MAE * 0.95",
        "classes": calibrated.classes_.tolist(),
        "features": FEATURES,
    }

    # Refit production models using all available completed rows. Native
    # probabilities remain conservative; the held-out report stays immutable.
    production_classifier = _pipeline(HistGradientBoostingClassifier(
        max_iter=180, learning_rate=0.045, max_leaf_nodes=10,
        min_samples_leaf=18, l2_regularization=2.0, random_state=42,
    ))
    production_regressor = _pipeline(HistGradientBoostingRegressor(
        loss="absolute_error", max_iter=180, learning_rate=0.045, max_leaf_nodes=10,
        min_samples_leaf=18, l2_regularization=2.0, random_state=42,
    ))
    production_classifier.fit(df[FEATURES], df["direction"])
    production_regressor.fit(df[FEATURES], df["total_move"])
    artifact = {
        "classifier": production_classifier, "regressor": production_regressor,
        "features": FEATURES, "classes": production_classifier.classes_.tolist(),
        "trained_through": str(df["date"].max().date()), "backtest": report,
        "approved_for_live_confidence": approved,
    }
    return report, artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    args = parser.parse_args()
    df = build_features(load_source(args.source))
    report, artifact = train_backtest(df)
    MODEL_DIR.mkdir(parents=True, exist_ok=True); REPORT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, MODEL_PATH)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Model: {MODEL_PATH}\nBacktest: {REPORT_PATH}")


if __name__ == "__main__":
    main()
