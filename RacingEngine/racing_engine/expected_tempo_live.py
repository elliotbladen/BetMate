"""Step 4 historical live replay for the standalone Expected Tempo Engine.

For each target race, only earlier completed races at that meeting may update
the latent meeting state. A change of going starts a new evidence regime.
Horse ratings, prices and market data are intentionally outside this module.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .expected_tempo_model import LABELS, TARGETS, classification_metrics


ROOT = Path(__file__).resolve().parents[1]
LIVE_VERSION = "expected-tempo-step4-live-replay-v1"
OVERLAY_TEST_START = "2025-03-01"
FOLD_MONTHS = 6
STATE_PRIOR_WEIGHT = 2.0

BASE_PROB_MODEL = "calibrated_logistic_blend"
BASE_SCORE_MODEL = "continuous_context_baseline"
META_FEATURES = [
    *[f"log_prob_{label}" for label in LABELS],
    *[f"base_{target}" for target in TARGETS],
    "completed_races", "same_regime_races", "state_total_weight", "state_reliability",
    "state_early", "state_middle", "state_late", "state_early_trend",
    "last_early", "last_middle", "last_late",
]
STATE_FEATURES = [
    "same_regime_races", "state_total_weight", "state_reliability",
    "state_early", "state_middle", "state_late", "state_early_trend",
    "last_early", "last_middle", "last_late",
]


def observation_weight(prior: dict[str, Any], target: dict[str, Any]) -> float:
    """Relevance of an already completed race to a later target race."""
    if prior["going_bucket"] != target["going_bucket"]:
        return 0.0
    distance_weight = math.exp(-abs(float(prior["distance_metres"]) - float(target["distance_metres"])) / 600.0)
    recency_gap = max(0, int(target["race_number"]) - int(prior["race_number"]) - 1)
    recency_weight = math.exp(-0.18 * recency_gap)
    coverage_weight = max(0.25, min(1.0, float(prior["sectional_coverage"])))
    return distance_weight * recency_weight * coverage_weight


def meeting_state(prior_races: list[dict[str, Any]], target: dict[str, Any]) -> dict[str, float]:
    weighted = [(row, observation_weight(row, target)) for row in prior_races]
    weighted = [(row, weight) for row, weight in weighted if weight > 0]
    total = sum(weight for _, weight in weighted)
    reliability = total / (total + STATE_PRIOR_WEIGHT) if total else 0.0

    def average(name: str) -> float:
        raw = sum(float(row[name]) * weight for row, weight in weighted) / total if total else 0.0
        return reliability * raw

    last = weighted[-1][0] if weighted else None
    early_values = [float(row["early_score"]) for row, _ in weighted]
    trend = (early_values[-1] - early_values[0]) if len(early_values) >= 2 else 0.0
    return {
        "completed_races": float(len(prior_races)),
        "same_regime_races": float(len(weighted)),
        "state_total_weight": total,
        "state_reliability": reliability,
        "state_early": average("early_score"),
        "state_middle": average("middle_score"),
        "state_late": average("late_score"),
        "state_early_trend": reliability * trend,
        "last_early": reliability * float(last["early_score"]) if last else 0.0,
        "last_middle": reliability * float(last["middle_score"]) if last else 0.0,
        "last_late": reliability * float(last["late_score"]) if last else 0.0,
    }


def load_replay_frame(predictions_path: Path, targets_path: Path) -> pd.DataFrame:
    predictions = pd.read_csv(predictions_path, dtype={"race_id": str})
    probabilities = predictions[predictions["model"] == BASE_PROB_MODEL][
        ["race_id", *[f"prob_{label}" for label in LABELS]]
    ].copy()
    scores = predictions[predictions["model"] == BASE_SCORE_MODEL][
        ["race_id", *[f"predicted_{target}" for target in TARGETS]]
    ].copy()
    targets = pd.read_csv(targets_path, dtype={"race_id": str})[
        ["race_id", "race_date", "track_slug", "race_number", "distance_metres", "going_bucket",
         "sectional_coverage", "early_score", "middle_score", "late_score", "pace_label_4way"]
    ]
    frame = probabilities.merge(scores, on="race_id", validate="one_to_one").merge(
        targets, on="race_id", validate="one_to_one", suffixes=("_prediction", "")
    )
    frame["race_date"] = pd.to_datetime(frame["race_date"])
    for label in LABELS:
        frame[f"log_prob_{label}"] = np.log(np.clip(frame[f"prob_{label}"].astype(float), 1e-6, 1.0))
    for target in TARGETS:
        frame[f"base_{target}"] = frame[f"predicted_{target}"].astype(float)
    state_rows = []
    for (_, _), card in frame.groupby(["race_date", "track_slug"], sort=False):
        prior: list[dict[str, Any]] = []
        for _, row in card.sort_values("race_number").iterrows():
            as_dict = row.to_dict()
            state_rows.append({"race_id": row["race_id"], **meeting_state(prior, as_dict)})
            prior.append(as_dict)
    state = pd.DataFrame(state_rows)
    return frame.merge(state, on="race_id", validate="one_to_one").sort_values(
        ["race_date", "track_slug", "race_number"]
    ).reset_index(drop=True)


def overlay_folds(frame: pd.DataFrame):
    start = pd.Timestamp(OVERLAY_TEST_START)
    end_all = frame["race_date"].max() + pd.Timedelta(days=1)
    while start < end_all:
        end = min(start + pd.DateOffset(months=FOLD_MONTHS), end_all)
        train = frame["race_date"] < start
        test = (frame["race_date"] >= start) & (frame["race_date"] < end)
        if train.sum() >= 150 and test.sum():
            yield start, end, train.to_numpy(), test.to_numpy()
        start = end


def _classifier() -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(C=0.08, max_iter=2000)),
    ])


def _regressor() -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", Ridge(alpha=25.0)),
    ])


def _aligned(model: Pipeline, values: pd.DataFrame) -> np.ndarray:
    raw = model.predict_proba(values)
    classes = list(model.named_steps["model"].classes_)
    return np.column_stack([raw[:, classes.index(label)] for label in LABELS])


def _counterfactual(values: pd.DataFrame) -> pd.DataFrame:
    result = values.copy()
    for feature in STATE_FEATURES:
        result[feature] = 0.0
    # Keep completed_races: it represents card position, not observed tempo.
    return result


def run_replay(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    outputs = []
    folds = []
    for fold_number, (start, end, train_mask, test_mask) in enumerate(overlay_folds(frame), 1):
        train, test = frame.loc[train_mask], frame.loc[test_mask]
        model = _classifier(); model.fit(train[META_FEATURES], train["pace_label_4way"])
        live_prob = _aligned(model, test[META_FEATURES])
        meta_v0_prob = _aligned(model, _counterfactual(test[META_FEATURES]))
        base_prob = test[[f"prob_{label}" for label in LABELS]].to_numpy(float)
        # Select a conservative update weight using only an inner chronological
        # calibration slice. The live overlay may never wholly replace V0.
        dates = np.array(sorted(train["race_date"].unique()))
        calibration_start = pd.Timestamp(dates[max(1, int(len(dates) * 0.8))])
        inner_fit = train[train["race_date"] < calibration_start]
        inner_calibration = train[train["race_date"] >= calibration_start]
        safe_weight = 0.0
        if len(inner_fit) >= 150 and len(inner_calibration) >= 40:
            inner_model = _classifier(); inner_model.fit(inner_fit[META_FEATURES], inner_fit["pace_label_4way"])
            inner_live = _aligned(inner_model, inner_calibration[META_FEATURES])
            inner_v0 = inner_calibration[[f"prob_{label}" for label in LABELS]].to_numpy(float)
            candidates = [0.0, 0.10, 0.20, 0.30, 0.40]
            safe_weight = min(candidates, key=lambda weight: classification_metrics(
                inner_calibration["pace_label_4way"].to_numpy(),
                (1 - weight) * inner_v0 + weight * inner_live,
            )["log_loss"])
        safe_live_prob = (1 - safe_weight) * base_prob + safe_weight * live_prob
        score_predictions: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for target in TARGETS:
            reg = _regressor(); reg.fit(train[META_FEATURES], train[target])
            score_predictions[target] = (
                reg.predict(_counterfactual(test[META_FEATURES])), reg.predict(test[META_FEATURES])
            )
        eligible = test["same_regime_races"].to_numpy() > 0
        y = test["pace_label_4way"].to_numpy()
        fold_report = {
            "fold": fold_number, "train_rows": len(train), "test_rows": len(test),
            "live_eligible_rows": int(eligible.sum()), "test_start": start.date().isoformat(),
            "test_end_exclusive": end.date().isoformat(),
            "classification_all": {
                "raw_v0": classification_metrics(y, base_prob),
                "meta_v0": classification_metrics(y, meta_v0_prob),
                "live_updated": classification_metrics(y, live_prob),
                "safe_live_blend": classification_metrics(y, safe_live_prob),
            },
            "inner_selected_live_weight": safe_weight,
        }
        if eligible.any():
            fold_report["classification_live_eligible"] = {
                "raw_v0": classification_metrics(y[eligible], base_prob[eligible]),
                "meta_v0": classification_metrics(y[eligible], meta_v0_prob[eligible]),
                "live_updated": classification_metrics(y[eligible], live_prob[eligible]),
                "safe_live_blend": classification_metrics(y[eligible], safe_live_prob[eligible]),
            }
        folds.append(fold_report)
        for position, (_, row) in enumerate(test.iterrows()):
            record = {
                "race_id": row["race_id"], "race_date": row["race_date"].date().isoformat(),
                "track_slug": row["track_slug"], "race_number": int(row["race_number"]),
                "snapshot_version": f"V{int(row['completed_races'])}", "fold": fold_number,
                "going_bucket": row["going_bucket"], "distance_metres": row["distance_metres"],
                "completed_races": int(row["completed_races"]),
                "same_regime_races": int(row["same_regime_races"]),
                "state_reliability": row["state_reliability"],
                "state_early": row["state_early"], "state_middle": row["state_middle"], "state_late": row["state_late"],
                "actual_label": row["pace_label_4way"],
            }
            for index, label in enumerate(LABELS):
                record[f"v0_prob_{label}"] = base_prob[position, index]
                record[f"meta_v0_prob_{label}"] = meta_v0_prob[position, index]
                record[f"live_prob_{label}"] = live_prob[position, index]
                record[f"safe_live_prob_{label}"] = safe_live_prob[position, index]
            for target in TARGETS:
                record[f"actual_{target}"] = row[target]
                record[f"v0_{target}"] = row[f"base_{target}"]
                record[f"meta_v0_{target}"] = score_predictions[target][0][position]
                record[f"live_{target}"] = score_predictions[target][1][position]
            outputs.append(record)
    replay = pd.DataFrame(outputs)
    report: dict[str, Any] = {
        "live_version": LIVE_VERSION, "input_rows": len(frame),
        "oof_rows": len(replay), "oof_races": int(replay["race_id"].nunique()), "folds": folds,
        "policy": {
            "causality": "only lower race numbers from the same date and track",
            "condition_change": "different going receives zero weight and starts a new regime",
            "distance_relevance": "exponential decay exp(-absolute distance difference / 600m)",
            "recency_relevance": "exponential decay by intervening races",
            "uncertainty": f"weighted observations shrink toward neutral with prior weight {STATE_PRIOR_WEIGHT}",
            "price_integration": "none; tempo engine only",
        },
        "promotion_status": "shadow_research_only",
    }
    if not replay.empty:
        eligible = replay["same_regime_races"] > 0
        y = replay.loc[eligible, "actual_label"].to_numpy()
        report["aggregate_live_eligible_classification"] = {}
        for prefix in ("v0", "meta_v0", "live", "safe_live"):
            probs = replay.loc[eligible, [f"{prefix}_prob_{label}" for label in LABELS]].to_numpy(float)
            report["aggregate_live_eligible_classification"][prefix] = classification_metrics(y, probs)
        report["aggregate_live_eligible_continuous"] = {}
        for target in TARGETS:
            actual = replay.loc[eligible, f"actual_{target}"]
            report["aggregate_live_eligible_continuous"][target] = {}
            for prefix in ("v0", "meta_v0", "live"):
                predicted = replay.loc[eligible, f"{prefix}_{target}"]
                report["aggregate_live_eligible_continuous"][target][prefix] = {
                    "mae": float(mean_absolute_error(actual, predicted)),
                    "rmse": float(mean_squared_error(actual, predicted) ** 0.5),
                }
        report["live_eligible_rows"] = int(eligible.sum())
    return replay, report


def write_artifacts(replay: pd.DataFrame, report: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    replay_path = output_dir / "expected_tempo_step4_live_replay.csv"
    report_path = output_dir / "expected_tempo_step4_evaluation.json"
    replay.to_csv(replay_path, index=False)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"replay": str(replay_path), "report": str(report_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    folder = ROOT / "reports" / "expected_tempo"
    parser.add_argument("--predictions", type=Path, default=folder / "expected_tempo_step3_oof_predictions.csv")
    parser.add_argument("--targets", type=Path, default=folder / "expected_tempo_step2_targets.csv")
    parser.add_argument("--output-dir", type=Path, default=folder)
    args = parser.parse_args()
    frame = load_replay_frame(args.predictions, args.targets)
    replay, report = run_replay(frame)
    print(json.dumps({**write_artifacts(replay, report, args.output_dir), **report}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
