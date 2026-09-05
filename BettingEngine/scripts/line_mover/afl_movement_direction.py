#!/usr/bin/env python3
"""AFL closing-line direction pilot.

Four deliberately small-sample-safe layers are evaluated independently for
handicap and totals:

1. prior/momentum baseline;
2. regularised multinomial logistic regression;
3. shallow histogram gradient boosting challenger;
4. a calibration-period probability blend.

The model predicts numerical line direction (UP/DOWN/NO_MOVE), not match
results.  Every feature is available at the forecast timestamp.  Team and
pair movement priors are updated only after each historical match is emitted.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "outputs/afl_weekly_review/historical/latest.xlsx"
DEFAULT_FINALS = ROOT.parent / "data/odds_snapshots/2026/2026-09-02_afl_finals_week2_sportsbet.csv"
MODEL_PATH = ROOT / "data/line_movement/models/afl_direction_pilot.joblib"
REPORT_PATH = ROOT / "outputs/line_movement/afl_direction_pilot_backtest.json"
PREDICTION_PATH = ROOT / "data/line_movement/predictions/afl_finals_direction_shadow.json"

CLASSES = np.array(["DOWN", "NO_MOVE", "UP"])
NUMERIC_FEATURES = [
    "opening_line", "current_line", "move_since_open", "current_price",
    "home_implied", "market_balance", "market_vig", "month", "day_of_season",
    "home_prior_mean", "away_prior_mean", "pair_prior_mean", "global_prior_mean",
    "home_prior_up_rate", "away_prior_up_rate", "pair_prior_up_rate",
    "home_games_prior", "away_games_prior", "pair_games_prior",
]
CATEGORICAL_FEATURES = ["home_team", "away_team"]


@dataclass(frozen=True)
class MarketSpec:
    name: str
    open_column: str
    close_column: str
    current_market: str


MARKETS = {
    "handicap": MarketSpec("handicap", "Home Line Open", "Home Line Close", "handicap"),
    "total": MarketSpec("total", "Total Score Open", "Total Score Close", "total"),
}


def _num(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def load_history(path: Path = DEFAULT_SOURCE, start: str = "2026-06-01") -> pd.DataFrame:
    """Load the requested recent AFL window from the canonical market workbook."""
    raw = pd.read_excel(path, header=1)
    raw["date"] = pd.to_datetime(raw.get("Date"), errors="coerce")
    raw = raw[raw["date"].notna() & (raw["date"] >= pd.Timestamp(start))].copy()
    raw["home_team"] = raw.get("Home Team", "").astype(str).str.strip()
    raw["away_team"] = raw.get("Away Team", "").astype(str).str.strip()
    raw["home_odds_open"] = _num(raw, "Home Odds Open")
    raw["away_odds_open"] = _num(raw, "Away Odds Open")
    raw = raw.sort_values(["date", "home_team", "away_team"]).reset_index(drop=True)
    return raw


def direction(move: pd.Series, material_points: float) -> np.ndarray:
    return np.select(
        [move <= -material_points, move >= material_points],
        ["DOWN", "UP"], default="NO_MOVE",
    )


def build_market_rows(raw: pd.DataFrame, spec: MarketSpec, material_points: float = 1.5) -> pd.DataFrame:
    """Create leakage-safe rolling features and closing-direction labels."""
    frame = raw.copy()
    frame["opening_line"] = _num(frame, spec.open_column)
    frame["current_line"] = frame["opening_line"]
    frame["closing_line"] = _num(frame, spec.close_column)
    frame = frame[frame["opening_line"].notna() & frame["closing_line"].notna()].copy()
    frame["line_move"] = frame["closing_line"] - frame["current_line"]
    frame["target"] = direction(frame["line_move"], material_points)
    frame["move_since_open"] = 0.0
    frame["current_price"] = 1.90
    home_raw, away_raw = 1 / frame["home_odds_open"], 1 / frame["away_odds_open"]
    frame["market_vig"] = home_raw + away_raw - 1
    frame["home_implied"] = home_raw / (home_raw + away_raw)
    frame["market_balance"] = (frame["home_implied"] - 0.5).abs()
    frame["month"] = frame["date"].dt.month
    frame["day_of_season"] = frame["date"].dt.dayofyear

    team_moves: dict[str, list[float]] = {}
    pair_moves: dict[tuple[str, str], list[float]] = {}
    global_moves: list[float] = []
    records: list[dict] = []

    def prior(values: list[float], n: int) -> tuple[float, float, int]:
        recent = values[-n:]
        if not recent:
            return 0.0, 0.5, 0
        return float(np.mean(recent)), float(np.mean(np.asarray(recent) >= material_points)), len(recent)

    for _, row in frame.iterrows():
        home, away = row["home_team"], row["away_team"]
        pair = tuple(sorted((home, away)))
        hp = prior(team_moves.get(home, []), 12)
        ap = prior(team_moves.get(away, []), 12)
        pp = prior(pair_moves.get(pair, []), 6)
        gp = prior(global_moves, 40)
        rec = row.to_dict()
        rec.update({
            "home_prior_mean": hp[0], "away_prior_mean": ap[0], "pair_prior_mean": pp[0],
            "global_prior_mean": gp[0], "home_prior_up_rate": hp[1],
            "away_prior_up_rate": ap[1], "pair_prior_up_rate": pp[1],
            "home_games_prior": hp[2], "away_games_prior": ap[2], "pair_games_prior": pp[2],
        })
        records.append(rec)
        observed = float(row["line_move"])
        team_moves.setdefault(home, []).append(observed)
        team_moves.setdefault(away, []).append(observed)
        pair_moves.setdefault(pair, []).append(observed)
        global_moves.append(observed)
    return pd.DataFrame(records)


def chronological_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split by whole match dates: 60% fit, 20% blend calibration, 20% test."""
    dates = np.array(sorted(frame["date"].dt.normalize().unique()))
    if len(dates) < 12:
        raise RuntimeError("Need at least 12 distinct match dates for chronological evaluation")
    first = max(1, int(len(dates) * 0.60))
    second = max(first + 1, int(len(dates) * 0.80))
    train = frame[frame["date"].dt.normalize().isin(dates[:first])]
    calibrate = frame[frame["date"].dt.normalize().isin(dates[first:second])]
    test = frame[frame["date"].dt.normalize().isin(dates[second:])]
    if min(len(train), len(calibrate), len(test)) < 12:
        raise RuntimeError("Each chronological partition needs at least 12 matches")
    return train, calibrate, test


def _preprocessor(scale: bool) -> ColumnTransformer:
    numeric_steps = [("impute", SimpleImputer(strategy="median", add_indicator=True))]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))
    return ColumnTransformer([
        ("numeric", Pipeline(numeric_steps), NUMERIC_FEATURES),
        ("teams", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
    ], sparse_threshold=0.0)


def build_logistic() -> Pipeline:
    return Pipeline([
        ("features", _preprocessor(scale=True)),
        ("model", LogisticRegression(C=0.30, max_iter=2000, class_weight="balanced", random_state=42)),
    ])


def build_tree() -> Pipeline:
    return Pipeline([
        ("features", _preprocessor(scale=False)),
        ("model", HistGradientBoostingClassifier(
            max_iter=100, learning_rate=0.04, max_leaf_nodes=7,
            min_samples_leaf=12, l2_regularization=5.0, random_state=42,
        )),
    ])


def baseline_probabilities(frame: pd.DataFrame, material_points: float = 1.5) -> np.ndarray:
    """Momentum when observed; otherwise a shrunk prior-movement baseline."""
    observed = frame["move_since_open"].to_numpy(float)
    prior_score = (
        0.30 * frame["home_prior_mean"].to_numpy(float)
        + 0.30 * frame["away_prior_mean"].to_numpy(float)
        + 0.20 * frame["pair_prior_mean"].to_numpy(float)
        + 0.20 * frame["global_prior_mean"].to_numpy(float)
    )
    score = np.where(np.abs(observed) >= 0.5, observed, prior_score)
    scale = max(material_points, 0.5)
    up = 1 / (1 + np.exp(-score / scale))
    down = 1 - up
    no_move = np.exp(-np.abs(score) / scale)
    probabilities = np.column_stack([down, no_move, up])
    return probabilities / probabilities.sum(axis=1, keepdims=True)


def aligned_probabilities(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    raw = model.predict_proba(frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
    result = np.zeros((len(frame), len(CLASSES)))
    for source_index, label in enumerate(model.classes_):
        result[:, int(np.where(CLASSES == label)[0][0])] = raw[:, source_index]
    return result


def metrics(actual: pd.Series, probabilities: np.ndarray, confidence: float = 0.55) -> dict:
    pred = CLASSES[np.argmax(probabilities, axis=1)]
    maximum = probabilities.max(axis=1)
    confident = maximum >= confidence
    moved = actual.ne("NO_MOVE").to_numpy()
    return {
        "matches": int(len(actual)),
        "accuracy": float(accuracy_score(actual, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(actual, pred)),
        "log_loss": float(log_loss(actual, probabilities, labels=CLASSES)),
        "material_move_accuracy": float(accuracy_score(actual[moved], pred[moved])) if moved.any() else None,
        "confidence_55_coverage": float(confident.mean()),
        "confidence_55_accuracy": float(accuracy_score(actual[confident], pred[confident])) if confident.any() else None,
        "predicted_counts": {label: int(np.sum(pred == label)) for label in CLASSES},
    }


def choose_blend(actual: pd.Series, base: np.ndarray, logistic: np.ndarray, tree: np.ndarray) -> tuple[list[float], np.ndarray]:
    """Choose non-negative 0.1-grid weights on calibration log loss only."""
    best_loss, best_weights, best_probs = float("inf"), [0.0, 0.5, 0.5], logistic
    for base_weight in np.arange(0, 0.51, 0.1):
        for logistic_weight in np.arange(0, 1.01 - base_weight, 0.1):
            tree_weight = 1.0 - base_weight - logistic_weight
            candidate = base_weight * base + logistic_weight * logistic + tree_weight * tree
            loss = log_loss(actual, candidate, labels=CLASSES)
            if loss < best_loss:
                best_loss = loss
                best_weights = [float(base_weight), float(logistic_weight), float(tree_weight)]
                best_probs = candidate
    return best_weights, best_probs


def fit_market(frame: pd.DataFrame, market: str, material_points: float = 1.5) -> tuple[dict, dict]:
    train, calibrate, test = chronological_split(frame)
    logistic, tree = build_logistic(), build_tree()
    columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    logistic.fit(train[columns], train["target"])
    tree.fit(train[columns], train["target"])
    cal_probs = {
        "baseline": baseline_probabilities(calibrate, material_points),
        "logistic": aligned_probabilities(logistic, calibrate),
        "tree": aligned_probabilities(tree, calibrate),
    }
    weights, _ = choose_blend(calibrate["target"], cal_probs["baseline"], cal_probs["logistic"], cal_probs["tree"])
    test_probs = {
        "baseline": baseline_probabilities(test, material_points),
        "logistic": aligned_probabilities(logistic, test),
        "tree": aligned_probabilities(tree, test),
    }
    test_probs["blend"] = sum(weight * test_probs[name] for weight, name in zip(weights, ["baseline", "logistic", "tree"]))
    report = {
        "market": market,
        "material_move_points": material_points,
        "date_split": {
            "train": [str(train["date"].min().date()), str(train["date"].max().date()), len(train)],
            "calibration": [str(calibrate["date"].min().date()), str(calibrate["date"].max().date()), len(calibrate)],
            "test": [str(test["date"].min().date()), str(test["date"].max().date()), len(test)],
        },
        "class_counts": {label: int((frame["target"] == label).sum()) for label in CLASSES},
        "blend_weights": dict(zip(["baseline", "logistic", "tree"], weights)),
        "test": {name: metrics(test["target"], probs) for name, probs in test_probs.items()},
        "beats_50_percent": bool(metrics(test["target"], test_probs["blend"])["accuracy"] > 0.50),
    }

    # Frozen live artifact fits the two ML layers through the calibration cutoff;
    # the held-out test remains untouched evidence.
    fit = pd.concat([train, calibrate]).sort_values("date")
    live_logistic, live_tree = build_logistic(), build_tree()
    live_logistic.fit(fit[columns], fit["target"])
    live_tree.fit(fit[columns], fit["target"])
    artifact = {
        "market": market, "logistic": live_logistic, "tree": live_tree,
        "weights": weights, "material_points": material_points,
        "classes": CLASSES.tolist(), "trained_through": str(fit["date"].max().date()),
        "history": frame, "report": report,
    }
    return report, artifact


def current_market_rows(snapshot_path: Path) -> dict[str, pd.DataFrame]:
    raw = pd.read_csv(snapshot_path)
    raw["captured_at"] = pd.to_datetime(raw["captured_at"], errors="coerce", utc=True)
    output: dict[str, list[dict]] = {"handicap": [], "total": []}
    for (home, away), game in raw.groupby(["home_team", "away_team"], sort=False):
        hcap = game[(game["market"] == "handicap") & (game["outcome"] == home)]
        total = game[(game["market"] == "total") & (game["outcome"].str.lower() == "over")]
        h2h = game[game["market"] == "h2h"]
        home_h2h = h2h[h2h["outcome"] == home]
        away_h2h = h2h[h2h["outcome"] == away]
        common = {
            "date": game["captured_at"].max().tz_convert(None), "home_team": home, "away_team": away,
            "home_odds_open": float(home_h2h.iloc[-1]["price"]) if not home_h2h.empty else 2.0,
            "away_odds_open": float(away_h2h.iloc[-1]["price"]) if not away_h2h.empty else 2.0,
        }
        if not hcap.empty:
            output["handicap"].append({**common, "opening_line": float(hcap.iloc[-1]["line"]),
                "current_line": float(hcap.iloc[-1]["line"]), "current_price": float(hcap.iloc[-1]["price"])})
        if not total.empty:
            output["total"].append({**common, "opening_line": float(total.iloc[-1]["line"]),
                "current_line": float(total.iloc[-1]["line"]), "current_price": float(total.iloc[-1]["price"])})
    return {market: pd.DataFrame(rows) for market, rows in output.items()}


def add_live_features(current: pd.DataFrame, history: pd.DataFrame, material_points: float) -> pd.DataFrame:
    result = current.copy()
    result["move_since_open"] = result["current_line"] - result["opening_line"]
    home_raw, away_raw = 1 / result["home_odds_open"], 1 / result["away_odds_open"]
    result["market_vig"] = home_raw + away_raw - 1
    result["home_implied"] = home_raw / (home_raw + away_raw)
    result["market_balance"] = (result["home_implied"] - 0.5).abs()
    result["month"] = result["date"].dt.month
    result["day_of_season"] = result["date"].dt.dayofyear
    for index, row in result.iterrows():
        pair = {row["home_team"], row["away_team"]}
        home_hist = history[(history["home_team"] == row["home_team"]) | (history["away_team"] == row["home_team"])].tail(12)
        away_hist = history[(history["home_team"] == row["away_team"]) | (history["away_team"] == row["away_team"])].tail(12)
        pair_hist = history[history.apply(lambda item: {item["home_team"], item["away_team"]} == pair, axis=1)].tail(6)
        global_hist = history.tail(40)
        for prefix, subset in (("home", home_hist), ("away", away_hist), ("pair", pair_hist)):
            result.loc[index, f"{prefix}_prior_mean"] = subset["line_move"].mean() if len(subset) else 0.0
            result.loc[index, f"{prefix}_prior_up_rate"] = (subset["line_move"] >= material_points).mean() if len(subset) else 0.5
            result.loc[index, f"{prefix}_games_prior"] = len(subset)
        result.loc[index, "global_prior_mean"] = global_hist["line_move"].mean() if len(global_hist) else 0.0
    return result


def forecast(artifacts: dict, snapshot_path: Path) -> dict:
    current = current_market_rows(snapshot_path)
    predictions = []
    for market, artifact in artifacts.items():
        live = add_live_features(current[market], artifact["history"], artifact["material_points"])
        base = baseline_probabilities(live, artifact["material_points"])
        logistic = aligned_probabilities(artifact["logistic"], live)
        tree = aligned_probabilities(artifact["tree"], live)
        weights = artifact["weights"]
        blend = weights[0] * base + weights[1] * logistic + weights[2] * tree
        for row_index, (_, row) in enumerate(live.iterrows()):
            probs = {label: float(blend[row_index, i]) for i, label in enumerate(CLASSES)}
            selected = max(probs, key=probs.get)
            predictions.append({
                "market": market, "home_team": row["home_team"], "away_team": row["away_team"],
                "current_line": float(row["current_line"]), "direction": selected,
                "confidence": probs[selected], "probabilities": probs,
                "interpretation": "higher numerical line" if selected == "UP" else "lower numerical line" if selected == "DOWN" else "no move of at least 1.5 points",
                "status": "SHADOW_ONLY_SMALL_SAMPLE",
            })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(snapshot_path), "model_version": "afl-direction-pilot-v1",
        "predictions": predictions,
    }


def run(source: Path, finals: Path, start: str) -> tuple[dict, dict]:
    history = load_history(source, start)
    reports, artifacts = {}, {}
    for market, spec in MARKETS.items():
        market_rows = build_market_rows(history, spec)
        reports[market], artifacts[market] = fit_market(market_rows, market)
    report = {
        "model_version": "afl-direction-pilot-v1", "status": "SHADOW_ONLY_SMALL_SAMPLE",
        "training_start": start, "source": str(source), "markets": reports,
        "notes": [
            "Direction is numerical line movement, not a match-result prediction.",
            "Finals are prospective only and were not used in fitting.",
            "Dense intermediate snapshots can populate current_line/move_since_open when recovered.",
        ],
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREDICTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"version": "afl-direction-pilot-v1", "markets": artifacts}, MODEL_PATH)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    prediction = forecast(artifacts, finals) if finals.exists() else {"predictions": [], "missing_finals_source": str(finals)}
    PREDICTION_PATH.write_text(json.dumps(prediction, indent=2), encoding="utf-8")
    return report, prediction


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--finals", type=Path, default=DEFAULT_FINALS)
    parser.add_argument("--start", default="2026-06-01")
    args = parser.parse_args()
    report, prediction = run(args.source, args.finals, args.start)
    print(json.dumps(report, indent=2))
    print(json.dumps(prediction, indent=2))
    print(f"Model: {MODEL_PATH}\nBacktest: {REPORT_PATH}\nFinals shadow: {PREDICTION_PATH}")


if __name__ == "__main__":
    main()
