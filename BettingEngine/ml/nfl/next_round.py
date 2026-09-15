"""Fail-closed next-round NFL pricing with timestamped live inputs.

The overlay is explicitly partitioned so every signal is applied once. T1
contains team strength and injuries; T2 contains QB, continuity and weather;
T3 confluence is a selection gate and contributes zero football points.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .step8_live_tiers import MODEL_RETENTION_1, score_file, validate_record
from .features import PRIOR_SEASON_RETENTION

OVERLAY_POLICY = {
    "t1_included_points": ("t1_team_strength", "t1_injuries"),
    "t2_included_points": ("t2_quarterback_personnel", "t2_roster_continuity", "t2_weather"),
    "t3_included_gate_zero_points": ("t3_confluence",),
    "shadow_no_price": ("context_event_register",),
    "discarded": ("t4_venue_travel", "t5_rest_schedule", "t7_scheme_matchup"),
    "execution_only": ("t8_market_disagreement",),
    "adjustment_scale": {"t2_quarterback_personnel": 0.7830854193655986,
                         "t2_roster_continuity": 0.7830854193655986,
                         "t1_injuries": 0.7830854193655986,
                         "t2_weather": 0.0,
                         "t3_confluence": 0.0},
}

SELECTION_POLICY = {
    "spread_and_total": "model edge at least 2.0 points from captured market",
    "moneyline": "no selection until probability calibration and price-vig audit pass",
    "staking": "disabled",
}

def build(predictions: Path, live_input: Path, output: Path) -> dict:
    pred = pd.read_csv(predictions)
    tier_model = json.loads(MODEL_RETENTION_1.read_text(encoding="utf-8")) if MODEL_RETENTION_1.exists() else {}
    payload = json.loads(live_input.read_text(encoding="utf-8"))
    records = payload.get("games", [])
    by_id = {str(item.get("game_id")): item for item in records}
    blockers: list[str] = []
    if tier_model.get("structural_prior_season_retention") != PRIOR_SEASON_RETENTION:
        blockers.append("tier_model_retention_context_mismatch_retrain_required")
    for game_id in pred.game_id.astype(str):
        record = by_id.get(game_id)
        if record is None:
            blockers.append(f"missing_live_record:{game_id}")
            continue
        errors = validate_record(record)
        if errors:
            blockers.extend(f"{game_id}:{error}" for error in errors)
        if record.get("status") not in {"resolved", "live_inputs_complete"}:
            blockers.append(f"{game_id}:live_status_not_complete")
        for source in ("qb", "injuries", "roster"):
            if not record.get("source_timestamps", {}).get(source):
                blockers.append(f"{game_id}:missing_source_timestamp:{source}")
        for side in ("home", "away"):
            qb = record.get(side, {}).get("qb", {})
            required_qb = ("starter_id", "backup_id", "starter_probability", "starter_profile", "backup_profile")
            if any(qb.get(field) in (None, "") for field in required_qb):
                blockers.append(f"{game_id}:incomplete_{side}_qb")
            continuity = record.get(side, {}).get("continuity", {})
            required_continuity = ("weekly_roster_continuity", "returning_roster_share",
                                   "returning_ol_share", "returning_receiver_share")
            if any(continuity.get(field) is None for field in required_continuity):
                blockers.append(f"{game_id}:incomplete_{side}_continuity")
            availability = record.get(side, {}).get("availability", {})
            required_availability = ("injury_burden", "players_out", "players_questionable", "injury_report_rows")
            if any(availability.get(field) is None for field in required_availability):
                blockers.append(f"{game_id}:incomplete_{side}_injuries")
    result = {
        "status": "blocked_live_inputs_incomplete" if blockers else "live_inputs_ready_for_shadow_price",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "games": len(pred), "resolved_games": len(pred) - len({x.split(":", 1)[0] for x in blockers}),
        "blockers": sorted(set(blockers)), "staking_enabled": False,
        "weather_priced": False,
        "weather_reason": "T2 slot is reserved; no timestamped forecast model is promoted yet",
        "overlay_policy": OVERLAY_POLICY,
        "selection_policy": SELECTION_POLICY,
    }
    if blockers:
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result
    scored = score_file(live_input, predictions_path=predictions, model_path=MODEL_RETENTION_1)
    rows = pd.DataFrame(scored["rows"])
    result["adjusted_predictions"] = str(output)
    result["live_tier_model"] = str(MODEL_RETENTION_1)
    result["overlay_policy"] = OVERLAY_POLICY
    result["selection_rule"] = SELECTION_POLICY
    merged = pred.merge(rows[["game_id", "combined_shadow_fair_home_spread_uncapped", "t1_injury_margin_points",
                              "t2_qb_shadow_margin_points", "t3_continuity_shadow_margin_points"]], on="game_id", validate="one_to_one")
    merged["live_fair_home_spread"] = merged.combined_shadow_fair_home_spread_uncapped
    merged["live_total"] = merged.ridge_total
    merged["staking_enabled"] = False
    merged.to_csv(output, index=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--live-input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.predictions, args.live_input, args.output), indent=2))


if __name__ == "__main__":
    main()
