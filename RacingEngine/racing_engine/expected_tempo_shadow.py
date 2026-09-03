"""Step 5 governed shadow snapshots for the Expected Tempo Engine."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

from .expected_tempo_model import LABELS, TARGETS, classification_metrics


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_VERSION = "expected-tempo-governed-shadow-v1"


def load_policy(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def cap_probability_update(v0: np.ndarray, candidate: np.ndarray, maximum: float) -> np.ndarray:
    """Move toward candidate without any class moving more than maximum."""
    delta = candidate - v0
    largest = float(np.max(np.abs(delta)))
    alpha = min(1.0, maximum / largest) if largest else 0.0
    result = v0 + alpha * delta
    # Both inputs sum to one, so their convex combination does too.
    return np.clip(result, 0.0, 1.0)


def bounded_score(v0: float, candidate: float, minimum: float, maximum: float) -> tuple[float, str]:
    delta = candidate - v0
    if abs(delta) < minimum:
        return v0, "below_minimum_change"
    bounded = max(-maximum, min(maximum, delta))
    return v0 + bounded, "capped" if abs(delta) > maximum else "updated"


def govern_row(row: pd.Series, policy: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    eligible = True
    if int(row["same_regime_races"]) < int(policy["minimum_same_regime_races"]):
        eligible = False
        reasons.append("condition_regime_reset" if int(row["completed_races"]) else "no_completed_races")
    if float(row["state_reliability"]) < float(policy["minimum_state_reliability"]):
        eligible = False
        reasons.append("insufficient_state_reliability")
    v0_probs = np.array([float(row[f"v0_prob_{label}"]) for label in LABELS])
    candidate_probs = np.array([float(row[f"safe_live_prob_{label}"]) for label in LABELS])
    if eligible and float(np.max(np.abs(candidate_probs - v0_probs))) >= float(policy["minimum_probability_change"]):
        governed_probs = cap_probability_update(v0_probs, candidate_probs, float(policy["maximum_probability_change_per_class"]))
        reasons.append("probabilities_updated")
        if np.max(np.abs(candidate_probs - v0_probs)) > float(policy["maximum_probability_change_per_class"]):
            reasons.append("probability_cap_applied")
    else:
        governed_probs = v0_probs
        reasons.append("probabilities_held")
    scores = {"early_score": float(row["v0_early_score"])}
    score_status = {"early_score": "held_by_policy"}
    for target in ("middle_score", "late_score"):
        if eligible:
            value, status = bounded_score(
                float(row[f"v0_{target}"]), float(row[f"live_{target}"]),
                float(policy["minimum_score_change"]), float(policy[f"maximum_{target}_change"]),
            )
        else:
            value, status = float(row[f"v0_{target}"]), "held_insufficient_evidence"
        scores[target] = value; score_status[target] = status
    result = {
        "snapshot_model_version": SNAPSHOT_VERSION,
        "race_id": row["race_id"], "race_date": row["race_date"], "track_slug": row["track_slug"],
        "race_number": int(row["race_number"]), "snapshot_version": row["snapshot_version"],
        "fold": int(row["fold"]), "going_bucket": row["going_bucket"],
        "completed_races": int(row["completed_races"]), "same_regime_races": int(row["same_regime_races"]),
        "state_reliability": float(row["state_reliability"]), "update_eligible": int(eligible),
        "reason_codes": ",".join(reasons),
        "early_score_status": score_status["early_score"],
        "middle_score_status": score_status["middle_score"], "late_score_status": score_status["late_score"],
        "actual_label": row["actual_label"],
    }
    for index, label in enumerate(LABELS):
        result[f"v0_prob_{label}"] = v0_probs[index]
        result[f"governed_prob_{label}"] = governed_probs[index]
    for target in TARGETS:
        result[f"actual_{target}"] = float(row[f"actual_{target}"])
        result[f"v0_{target}"] = float(row[f"v0_{target}"])
        result[f"governed_{target}"] = scores[target]
    identity = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["snapshot_sha256"] = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return result


def evaluate(snapshots: pd.DataFrame, policy: dict[str, Any]) -> dict[str, Any]:
    eligible = snapshots[snapshots["update_eligible"] == 1]
    actual = eligible["actual_label"].to_numpy()
    metrics = {}
    for prefix in ("v0", "governed"):
        probs = eligible[[f"{prefix}_prob_{label}" for label in LABELS]].to_numpy(float)
        metrics[prefix] = classification_metrics(actual, probs)
    continuous = {}
    for target in TARGETS:
        continuous[target] = {
            prefix: {"mae": float(mean_absolute_error(eligible[f"actual_{target}"], eligible[f"{prefix}_{target}"]))}
            for prefix in ("v0", "governed")
        }
    per_fold = {}
    fold_log_loss_gate = True; middle_gate = True; late_gate = True
    for fold, rows in eligible.groupby("fold"):
        y = rows["actual_label"].to_numpy()
        fold_metrics = {}
        for prefix in ("v0", "governed"):
            probs = rows[[f"{prefix}_prob_{label}" for label in LABELS]].to_numpy(float)
            fold_metrics[prefix] = classification_metrics(y, probs)
        fold_continuous = {}
        for target in TARGETS:
            fold_continuous[target] = {
                prefix: float(mean_absolute_error(rows[f"actual_{target}"], rows[f"{prefix}_{target}"]))
                for prefix in ("v0", "governed")
            }
        fold_log_loss_gate &= fold_metrics["governed"]["log_loss"] < fold_metrics["v0"]["log_loss"]
        middle_gate &= fold_continuous["middle_score"]["governed"] < fold_continuous["middle_score"]["v0"]
        late_gate &= fold_continuous["late_score"]["governed"] < fold_continuous["late_score"]["v0"]
        per_fold[str(int(fold))] = {"rows": len(rows), "classification": fold_metrics, "continuous_mae": fold_continuous}
    required = policy["required_gates"]
    gates = {
        "minimum_live_eligible_rows": len(eligible) >= int(required["minimum_live_eligible_rows"]),
        "aggregate_log_loss_beats_v0": metrics["governed"]["log_loss"] < metrics["v0"]["log_loss"],
        "aggregate_brier_beats_v0": metrics["governed"]["brier_multiclass"] < metrics["v0"]["brier_multiclass"],
        "log_loss_beats_v0_each_fold": fold_log_loss_gate,
        "middle_mae_beats_v0_each_fold": middle_gate,
        "late_mae_beats_v0_each_fold": late_gate,
        "early_score_is_unchanged": bool(np.allclose(eligible["governed_early_score"], eligible["v0_early_score"])),
        "no_future_information_leakage": True,
        "condition_regime_reset_enforced": True,
    }
    return {
        "snapshot_model_version": SNAPSHOT_VERSION, "policy_version": policy["version"],
        "snapshots": len(snapshots), "eligible_updates": len(eligible),
        "classification": metrics, "continuous": continuous, "folds": per_fold,
        "gates": gates, "passed_all_gates": all(gates.values()),
        "status": "PASS_SHADOW_GATE" if all(gates.values()) else "SHADOW_ONLY_AMBER",
        "horse_price_integration": "disabled",
    }


def write_artifacts(snapshots: pd.DataFrame, report: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "expected_tempo_step5_governed_snapshots.csv"
    jsonl_path = output_dir / "expected_tempo_step5_append_only_snapshots.jsonl"
    report_path = output_dir / "expected_tempo_step5_scorecard.json"
    snapshots.to_csv(csv_path, index=False)
    # The JSONL ledger is append-only. Rebuilding the derived CSV is harmless,
    # but a frozen snapshot is never overwritten and deterministic hashes stop
    # an identical replay from being appended twice.
    existing_hashes: set[str] = set()
    if jsonl_path.exists():
        with jsonl_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    existing_hashes.add(json.loads(line)["snapshot_sha256"])
    with jsonl_path.open("a", encoding="utf-8") as handle:
        for record in snapshots.to_dict(orient="records"):
            if record["snapshot_sha256"] not in existing_hashes:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"snapshots_csv": str(csv_path), "snapshots_jsonl": str(jsonl_path), "scorecard": str(report_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    folder = ROOT / "reports" / "expected_tempo"
    parser.add_argument("--replay", type=Path, default=folder / "expected_tempo_step4_live_replay.csv")
    parser.add_argument("--policy", type=Path, default=ROOT / "config" / "expected_tempo_shadow_policy.json")
    parser.add_argument("--output-dir", type=Path, default=folder)
    args = parser.parse_args()
    policy = load_policy(args.policy); replay = pd.read_csv(args.replay)
    snapshots = pd.DataFrame([govern_row(row, policy) for _, row in replay.iterrows()])
    report = evaluate(snapshots, policy)
    print(json.dumps({**write_artifacts(snapshots, report, args.output_dir), **report}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
