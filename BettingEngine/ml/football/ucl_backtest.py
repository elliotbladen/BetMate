"""Format-aware Champions League backtest metrics and fail-closed runner."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
MATCHES = ROOT / "data/ucl/matches/ucl_matches_openfootball.csv"
REPORT = ROOT / "ml/football/reports/step9_ucl_backtest.json"


def multiclass_metrics(rows: pd.DataFrame) -> dict[str, float | int]:
    """Calculate RPS, Brier and log loss from H/D/A probabilities."""
    required = {"home_goals", "away_goals", "p_home", "p_draw", "p_away"}
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"missing prediction fields: {', '.join(sorted(missing))}")
    probs = rows[["p_home", "p_draw", "p_away"]].astype(float)
    if ((probs < 0).any().any() or (probs.sum(axis=1).sub(1).abs() > 1e-6).any()):
        raise ValueError("match probabilities must be non-negative and sum to one")
    actual = []
    for home, away in rows[["home_goals", "away_goals"]].itertuples(index=False):
        actual.append([1, 0, 0] if home > away else [0, 1, 0] if home == away else [0, 0, 1])
    # Use positional arrays here: prediction columns are named p_home/p_draw,
    # while the one-hot actual frame has integer column labels.  DataFrame
    # label alignment would otherwise produce NaNs and an erroneously zero RPS.
    actual_df = pd.DataFrame(actual, index=rows.index, columns=["p_home", "p_draw", "p_away"])
    cumulative_p = probs.iloc[:, :2].to_numpy().cumsum(axis=1)
    cumulative_a = actual_df.iloc[:, :2].to_numpy().cumsum(axis=1)
    rps = ((cumulative_p - cumulative_a) ** 2).sum(axis=1).mean() / 2
    brier = ((probs.to_numpy() - actual_df.to_numpy()) ** 2).sum(axis=1).mean()
    log_loss = -sum(math.log(max(float(probs.iloc[i, actual_df.iloc[i].to_numpy().argmax()]), 1e-15)) for i in range(len(rows))) / len(rows)
    accuracy = (probs.to_numpy().argmax(axis=1) == actual_df.to_numpy().argmax(axis=1)).mean()
    return {"games": len(rows), "rps": float(rps), "brier": float(brier), "log_loss": float(log_loss),
            "accuracy": float(accuracy)}


def qualification_metrics(rows: pd.DataFrame) -> dict[str, float | int]:
    required = {"top8_probability", "top8_actual", "top24_probability", "top24_actual"}
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"missing qualification fields: {', '.join(sorted(missing))}")
    output = {"clubs": len(rows)}
    for name in ("top8", "top24"):
        probability = rows[f"{name}_probability"].astype(float)
        actual = rows[f"{name}_actual"].astype(float)
        if ((probability < 0).any() or (probability > 1).any()):
            raise ValueError("qualification probabilities must be between zero and one")
        output[f"{name}_brier"] = float(((probability - actual) ** 2).mean())
        output[f"{name}_calibration_error"] = float(abs(probability.mean() - actual.mean()))
    return output


def run_status() -> dict[str, Any]:
    rows = pd.read_csv(MATCHES) if MATCHES.exists() else pd.DataFrame()
    if rows.empty:
        result = {"status": "ucl_backtest_blocked_no_sourced_matches", "games": 0,
                  "format_aware_seasons": ["2024/25", "2025/26"], "legacy_seasons_separate": True,
                  "fabricated_results": 0, "promotion_allowed": False,
                  "next_gate": "populate_sourced_matches_and_predictions"}
    else:
        result = {"status": "ucl_backtest_input_loaded_metrics_pending", "games": len(rows),
                  "promotion_allowed": False, "note": "prediction rows must be produced by walk-forward fits"}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run_status(), indent=2))
