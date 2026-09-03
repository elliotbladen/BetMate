"""Promotion evidence ledger for frozen NFL prospective shadow predictions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "data/nfl/predictions/prospective_promotion_ledger.csv"
REPORT = ROOT / "ml/nfl/reports/step12_promotion_status.json"

FIELDS = ["prediction_id", "game_id", "season", "week", "captured_at_utc", "cutoff_utc",
          "true_opener_verified", "obtainable_price_verified", "market_coverage", "model_edge_points",
          "closing_line_value", "opening_line_beat", "result", "threshold_version"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=FIELDS)


def validate_row(row: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in FIELDS if field not in row]
    if missing:
        raise ValueError(f"missing ledger fields: {', '.join(missing)}")
    if not row["prediction_id"] or not row["game_id"] or not row["threshold_version"]:
        raise ValueError("prediction_id, game_id and threshold_version are required")
    coverage = float(row["market_coverage"])
    if not 0.0 <= coverage <= 1.0:
        raise ValueError("market_coverage must be between zero and one")
    if row["result"] not in {"win", "loss", "push", "pending", "unresolved"}:
        raise ValueError("invalid result")
    return dict(row)


def promotion_status(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"status": "no_prospective_evidence", "predictions": 0, "seasons": 0,
                "market_coverage": 0.0, "mean_clv": None, "opening_line_beat_rate": None,
                "gates": {"minimum_predictions": False, "minimum_seasons": False,
                          "market_coverage": False, "positive_clv": False,
                          "positive_opening_beat_rate": False}, "promotion_allowed": False}
    settled = frame[frame.result.isin(["win", "loss", "push"])]
    beat = pd.to_numeric(frame.opening_line_beat, errors="coerce")
    clv = pd.to_numeric(frame.closing_line_value, errors="coerce")
    coverage = pd.to_numeric(frame.market_coverage, errors="coerce").mean()
    gates = {"minimum_predictions": len(frame) >= 500, "minimum_seasons": frame.season.nunique() >= 2,
             "market_coverage": coverage >= 0.90,
             "positive_clv": bool(clv.dropna().mean() > 0) if clv.notna().any() else False,
             "positive_opening_beat_rate": bool(beat.dropna().mean() > 0.5) if beat.notna().any() else False}
    return {"status": "promotion_candidate" if all(gates.values()) else "shadow_insufficient_for_promotion",
            "predictions": len(frame), "settled_results": len(settled), "seasons": int(frame.season.nunique()),
            "market_coverage": float(coverage), "mean_clv": float(clv.dropna().mean()) if clv.notna().any() else None,
            "opening_line_beat_rate": float(beat.dropna().mean()) if beat.notna().any() else None,
            "gates": gates, "promotion_allowed": False}


def run_status() -> dict[str, Any]:
    frame = pd.read_csv(LEDGER) if LEDGER.exists() else _empty()
    status = promotion_status(frame)
    status.update({"threshold_version_required": "nfl-t9-confluence-v1",
                   "staking_enabled": False, "manual_override_allowed": False,
                   "note": "promotion remains disabled until independent review after all gates pass"})
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return status


def main() -> None:
    if not LEDGER.exists():
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        _empty().to_csv(LEDGER, index=False)
    print(json.dumps(run_status(), indent=2))


if __name__ == "__main__":
    main()
