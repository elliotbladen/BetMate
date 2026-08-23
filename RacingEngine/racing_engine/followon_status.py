"""Consolidated status for the ten post-Step-10 follow-on actions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluation_protocol import load_protocol, protocol_hash
from .expansion_readiness import report as expansion_report
from .market_prices import coverage as market_coverage
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]


def build_status(store: RacingStore, protocol_path: Path) -> dict:
    protocol = load_protocol(protocol_path); digest = protocol_hash(protocol)
    train_predictions = store.connection.execute(
        "SELECT count(*) FROM benchmark_predictions WHERE protocol_hash=? AND period='train'", (digest,)).fetchone()[0]
    latest = store.connection.execute("SELECT max(race_date) FROM race_results").fetchone()[0]
    prospective_start = protocol["periods"]["prospective_holdout"]["from"]
    prospective_races = store.connection.execute(
        "SELECT count(*) FROM race_results WHERE race_date>=?", (prospective_start,)).fetchone()[0]
    return {
        "step11": {"status": "COMPLETE_REVISE_NO_PROMOTION", "wfa": "GATED_MISSING_RUNNER_AGE_SEX"},
        "robust_aggregation": "BUILT_RESEARCH_ONLY",
        "reduced_race_strength": "BUILT_10_25_50_PERCENT_RESEARCH_ONLY",
        "race_strength_confidence": "BUILT_RESEARCH_ONLY",
        "conditional_race_strength": "BUILT_RESEARCH_ONLY",
        "future_form_confirmation": "COMPLETED_DESCRIPTIVE",
        "calibration": {"status": "AWAITING_DESIGNATED_TRAIN_PREDICTIONS" if not train_predictions else "READY_TO_FIT",
                        "train_prediction_rows": train_predictions},
        "data_expansion": expansion_report(store),
        "market_prices": market_coverage(store),
        "descriptive_race_strength": "ACTIVE_RESEARCH_OUTPUT",
        "prospective_evaluation": {"start": prospective_start, "latest_result": latest,
                                   "races_available": prospective_races,
                                   "status": "AWAITING_NEW_RESULTS" if not prospective_races else "READY"},
        "accepted_model": "performance-par-v1.0",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--protocol", type=Path, default=ROOT / "config" / "evaluation_protocol_v1.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(); store = RacingStore(args.database)
    try: report = build_status(store, args.protocol)
    finally: store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output: args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered)
    else: print(rendered, end="")


if __name__ == "__main__": main()
