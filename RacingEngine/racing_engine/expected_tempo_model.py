"""Step 3 chronological backtest for the standalone Expected Tempo Engine."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, log_loss, mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
MODEL_VERSION = "expected-tempo-step3-walk-forward-v1"
# scikit-learn's log-loss contract requires lexicographic class order when
# explicit labels are supplied; probability columns follow this exact order.
LABELS = ["even", "fast", "slow", "very_fast_or_collapse"]
TARGETS = ["early_score", "middle_score", "late_score"]
TEST_START = "2024-09-01"
FOLD_MONTHS = 6

CATEGORICAL = [
    "source", "state", "track_slug", "feature_going_bucket", "rail_bucket",
    "feature_race_type", "feature_class_family", "feature_group_grade",
    "feature_benchmark", "feature_class_number", "feature_age_condition",
    "feature_sex_condition", "calendar_month",
]
NUMERIC = [
    "feature_distance_metres", "race_number", "feature_field_size",
    "feature_barrier_coverage", "feature_barrier_mean", "feature_barrier_spread",
    "feature_profiled_runner_count", "feature_profiled_runner_coverage",
    "feature_likely_leader_count", "feature_on_pace_count",
    "feature_field_median_prior_early_relative", "feature_field_median_prior_position_800",
    "feature_temperature_c", "feature_humidity_pct", "feature_precipitation_mm",
    "feature_wind_speed_kmh", "wind_sin", "wind_cos",
]


def load_frame(step1: Path, step2: Path) -> pd.DataFrame:
    features = pd.read_csv(step1, dtype={"race_id": str})
    targets = pd.read_csv(step2, dtype={"race_id": str})
    target_columns = ["race_id", "rail_bucket", "early_score", "middle_score", "late_score", "pace_label_4way"]
    frame = features.merge(targets[target_columns], on="race_id", how="inner", validate="one_to_one")
    frame["race_date"] = pd.to_datetime(frame["race_date"], errors="raise")
    frame["calendar_month"] = frame["race_date"].dt.month.astype(str)
    radians = np.deg2rad(pd.to_numeric(frame["feature_wind_direction_deg"], errors="coerce"))
    frame["wind_sin"] = np.sin(radians)
    frame["wind_cos"] = np.cos(radians)
    for column in CATEGORICAL:
        frame[column] = frame[column].fillna("missing").astype(str)
    for column in NUMERIC:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values(["race_date", "track_slug", "race_number"]).reset_index(drop=True)


def chronological_folds(frame: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp, np.ndarray, np.ndarray]]:
    start = pd.Timestamp(TEST_START)
    end_all = frame["race_date"].max() + pd.Timedelta(days=1)
    folds = []
    while start < end_all:
        end = min(start + pd.DateOffset(months=FOLD_MONTHS), end_all)
        train = (frame["race_date"] < start).to_numpy()
        test = ((frame["race_date"] >= start) & (frame["race_date"] < end)).to_numpy()
        if train.sum() and test.sum():
            folds.append((start, end, train, test))
        start = end
    return folds


def _preprocessor(*, dense: bool) -> ColumnTransformer:
    return ColumnTransformer([
        ("categorical", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=not dense)),
        ]), CATEGORICAL),
        ("numeric", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), NUMERIC),
    ])


def classifier(kind: str) -> Pipeline:
    if kind == "regularised_logistic":
        model = LogisticRegression(C=0.35, max_iter=2000, class_weight=None)
        return Pipeline([("features", _preprocessor(dense=False)), ("model", model)])
    if kind == "boosted_tree":
        model = HistGradientBoostingClassifier(
            learning_rate=0.045, max_iter=140, max_leaf_nodes=15,
            min_samples_leaf=25, l2_regularization=2.0, random_state=20260903,
        )
        return Pipeline([("features", _preprocessor(dense=True)), ("model", model)])
    raise ValueError(kind)


def regressor(kind: str) -> Pipeline:
    if kind == "ridge":
        return Pipeline([("features", _preprocessor(dense=False)), ("model", Ridge(alpha=12.0))])
    if kind == "boosted_tree":
        model = HistGradientBoostingRegressor(
            learning_rate=0.045, max_iter=140, max_leaf_nodes=15,
            min_samples_leaf=25, l2_regularization=2.0, random_state=20260903,
        )
        return Pipeline([("features", _preprocessor(dense=True)), ("model", model)])
    raise ValueError(kind)


def _context_key(row: pd.Series) -> tuple[str, str, str, str]:
    distance_band = str(int(float(row["feature_distance_metres"]) // 200 * 200))
    return row["state"], distance_band, row["feature_going_bucket"], row["feature_group_grade"]


def context_probabilities(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    global_counts = Counter(train["pace_label_4way"])
    cells: dict[tuple, Counter] = defaultdict(Counter)
    for _, row in train.iterrows():
        cells[_context_key(row)][row["pace_label_4way"]] += 1
    global_probs = np.array([(global_counts[label] + 1) / (len(train) + len(LABELS)) for label in LABELS])
    output = []
    for _, row in test.iterrows():
        counts = cells[_context_key(row)]; n = sum(counts.values()); weight = n / (n + 25.0)
        local = np.array([(counts[label] + 1) / (n + len(LABELS)) for label in LABELS])
        probs = weight * local + (1 - weight) * global_probs
        output.append(probs / probs.sum())
    return np.asarray(output)


def context_scores(train: pd.DataFrame, test: pd.DataFrame, target: str) -> np.ndarray:
    global_mean = float(train[target].mean())
    cells: dict[tuple, list[float]] = defaultdict(list)
    for _, row in train.iterrows():
        cells[_context_key(row)].append(float(row[target]))
    result = []
    for _, row in test.iterrows():
        values = cells[_context_key(row)]; n = len(values); weight = n / (n + 25.0)
        local = float(np.mean(values)) if values else global_mean
        result.append(weight * local + (1 - weight) * global_mean)
    return np.asarray(result)


def classification_metrics(y: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    encoded = np.array([LABELS.index(value) for value in y])
    one_hot = np.eye(len(LABELS))[encoded]
    predicted = np.asarray(LABELS)[probabilities.argmax(axis=1)]
    confidence = probabilities.max(axis=1)
    correct = (predicted == y).astype(float)
    ece = 0.0
    for low in np.linspace(0, 0.9, 10):
        mask = (confidence >= low) & (confidence < low + 0.1 if low < 0.9 else confidence <= 1)
        if mask.any():
            ece += mask.mean() * abs(correct[mask].mean() - confidence[mask].mean())
    return {
        "log_loss": float(log_loss(y, probabilities, labels=LABELS)),
        "brier_multiclass": float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
        "accuracy": float(accuracy_score(y, predicted)),
        "confidence_ece_10bin": float(ece),
    }


def _aligned_probabilities(model: Pipeline, values: pd.DataFrame) -> np.ndarray:
    raw = model.predict_proba(values)
    classes = list(model.named_steps["model"].classes_)
    return np.column_stack([raw[:, classes.index(label)] if label in classes else np.zeros(len(values)) for label in LABELS])


def run_backtest(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    records: list[dict[str, Any]] = []
    fold_reports = []
    final_models: dict[str, Pipeline] = {}
    last_test: pd.DataFrame | None = None
    for fold_number, (start, end, train_mask, test_mask) in enumerate(chronological_folds(frame), 1):
        train, test = frame.loc[train_mask], frame.loc[test_mask]
        x_train, x_test = train[CATEGORICAL + NUMERIC], test[CATEGORICAL + NUMERIC]
        probability_sets = {
            "global_prior": np.tile(
                [(sum(train["pace_label_4way"] == label) + 1) / (len(train) + len(LABELS)) for label in LABELS],
                (len(test), 1),
            ),
            "context_baseline": context_probabilities(train, test),
        }
        for name in ("regularised_logistic", "boosted_tree"):
            model = classifier(name); model.fit(x_train, train["pace_label_4way"])
            probability_sets[name] = _aligned_probabilities(model, x_test)
            final_models[name] = model
        # Calibrate model influence strictly inside the training window. The
        # final 20% of training dates selects how much logistic signal may be
        # blended into the stable context prior; the outer test is untouched.
        train_dates = np.array(sorted(train["race_date"].unique()))
        calibration_start = pd.Timestamp(train_dates[max(1, int(len(train_dates) * 0.8))])
        inner_fit = train[train["race_date"] < calibration_start]
        inner_calibration = train[train["race_date"] >= calibration_start]
        blend_weight = 0.0
        if len(inner_fit) >= 200 and len(inner_calibration) >= 50:
            inner_model = classifier("regularised_logistic")
            inner_model.fit(inner_fit[CATEGORICAL + NUMERIC], inner_fit["pace_label_4way"])
            inner_ml = _aligned_probabilities(inner_model, inner_calibration[CATEGORICAL + NUMERIC])
            inner_context = context_probabilities(inner_fit, inner_calibration)
            candidates = [0.0, 0.10, 0.20, 0.30, 0.40]
            blend_weight = min(candidates, key=lambda weight: log_loss(
                inner_calibration["pace_label_4way"],
                (1 - weight) * inner_context + weight * inner_ml,
                labels=LABELS,
            ))
        probability_sets["calibrated_logistic_blend"] = (
            (1 - blend_weight) * probability_sets["context_baseline"]
            + blend_weight * probability_sets["regularised_logistic"]
        )
        score_sets: dict[str, dict[str, np.ndarray]] = {name: {} for name in ("global_mean", "context_baseline", "ridge", "boosted_tree")}
        for target in TARGETS:
            score_sets["global_mean"][target] = np.full(len(test), float(train[target].mean()))
            score_sets["context_baseline"][target] = context_scores(train, test, target)
            for name in ("ridge", "boosted_tree"):
                model = regressor(name); model.fit(x_train, train[target])
                score_sets[name][target] = model.predict(x_test)
        fold_metric = {name: classification_metrics(test["pace_label_4way"].to_numpy(), probs) for name, probs in probability_sets.items()}
        fold_reports.append({
            "fold": fold_number, "train_end_exclusive": start.date().isoformat(),
            "test_start": start.date().isoformat(), "test_end_exclusive": end.date().isoformat(),
            "train_rows": len(train), "test_rows": len(test), "classification": fold_metric,
            "inner_selected_logistic_blend_weight": blend_weight,
        })
        for position, (_, row) in enumerate(test.iterrows()):
            for name, probs in probability_sets.items():
                record = {
                    "race_id": row["race_id"], "race_date": row["race_date"].date().isoformat(),
                    "track_slug": row["track_slug"], "race_number": row["race_number"],
                    "fold": fold_number, "model": name, "actual_label": row["pace_label_4way"],
                }
                record.update({f"prob_{label}": float(probs[position, i]) for i, label in enumerate(LABELS)})
                for target in TARGETS:
                    record[f"actual_{target}"] = float(row[target])
                    record[f"predicted_{target}"] = None
                records.append(record)
            for name, targets in score_sets.items():
                record = {
                    "race_id": row["race_id"], "race_date": row["race_date"].date().isoformat(),
                    "track_slug": row["track_slug"], "race_number": row["race_number"],
                    "fold": fold_number, "model": f"continuous_{name}", "actual_label": row["pace_label_4way"],
                }
                record.update({f"prob_{label}": None for label in LABELS})
                for target in TARGETS:
                    record[f"actual_{target}"] = float(row[target])
                    record[f"predicted_{target}"] = float(targets[target][position])
                records.append(record)
        last_test = test
    predictions = pd.DataFrame(records)
    aggregate_classification = {}
    for name in ("global_prior", "context_baseline", "regularised_logistic", "boosted_tree", "calibrated_logistic_blend"):
        subset = predictions[predictions["model"] == name]
        probs = subset[[f"prob_{label}" for label in LABELS]].to_numpy(float)
        aggregate_classification[name] = classification_metrics(subset["actual_label"].to_numpy(), probs)
    aggregate_continuous = {}
    for name in ("global_mean", "context_baseline", "ridge", "boosted_tree"):
        subset = predictions[predictions["model"] == f"continuous_{name}"]
        aggregate_continuous[name] = {}
        for target in TARGETS:
            actual, predicted = subset[f"actual_{target}"], subset[f"predicted_{target}"]
            aggregate_continuous[name][target] = {
                "mae": float(mean_absolute_error(actual, predicted)),
                "rmse": float(mean_squared_error(actual, predicted) ** 0.5),
            }
    importances = []
    if last_test is not None and "boosted_tree" in final_models:
        sample = last_test[CATEGORICAL + NUMERIC]
        result = permutation_importance(
            final_models["boosted_tree"], sample, last_test["pace_label_4way"],
            scoring="neg_log_loss", n_repeats=8, random_state=20260903,
        )
        importances = [
            {"feature": feature, "mean_log_loss_improvement": float(mean), "std": float(std)}
            for feature, mean, std in sorted(
                zip(CATEGORICAL + NUMERIC, result.importances_mean, result.importances_std),
                key=lambda item: item[1], reverse=True,
            )[:15]
        ]
    report = {
        "model_version": MODEL_VERSION,
        "rows": len(frame), "oof_races": int(predictions["race_id"].nunique()),
        "folds": fold_reports,
        "aggregate_classification": aggregate_classification,
        "aggregate_continuous": aggregate_continuous,
        "last_fold_boosted_permutation_importance": importances,
        "feature_policy": {
            "categorical": CATEGORICAL, "numeric": NUMERIC,
            "forbidden": ["all target_* columns", "same-day completed-race evidence", "horse ratings", "market prices"],
            "historical_limit": "official going/rail values lack archived freeze timestamps; prospective collection required",
        },
        "promotion_status": "shadow_research_only",
    }
    return predictions, report


def write_artifacts(predictions: pd.DataFrame, report: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / "expected_tempo_step3_oof_predictions.csv"
    report_path = output_dir / "expected_tempo_step3_backtest.json"
    predictions.to_csv(predictions_path, index=False)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"predictions": str(predictions_path), "report": str(report_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    folder = ROOT / "reports" / "expected_tempo"
    parser.add_argument("--step1", type=Path, default=folder / "expected_tempo_step1.csv")
    parser.add_argument("--step2", type=Path, default=folder / "expected_tempo_step2_targets.csv")
    parser.add_argument("--output-dir", type=Path, default=folder)
    args = parser.parse_args()
    frame = load_frame(args.step1, args.step2)
    predictions, report = run_backtest(frame)
    print(json.dumps({**write_artifacts(predictions, report, args.output_dir), **report}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
