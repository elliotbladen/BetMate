"""Final NFL research consolidation and fail-closed 2026 readiness card."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "ml/nfl/reports"
CARD = ROOT / "data/nfl/predictions/2026_week01_shadow_readiness.csv"
REPORT = REPORTS / "step10_nfl_readiness.json"


TIER_REGISTRY = {
    "T0 market data": ("active_gate", "abstain when quotes are missing or invalid"),
    "T1 team strength": ("active_paper", "official frozen structural baseline"),
    "T2 quarterback/personnel": ("prospective_shadow", "historically useful; live QB review unresolved"),
    "T3 continuity/injuries": ("prospective_shadow", "historically useful; pre-cut roster rejected"),
    "T4 venue/travel": ("rejected_spread_diagnostic", "spread MAE worsened; travel coordinates untested"),
    "T5 rest/schedule": ("rejected", "nonlinear additions worsened spread and total models"),
    "T6 weather": ("totals_shadow", "small oracle gain; timestamped live forecasts required"),
    "T7 scheme/matchup": ("rejected_diagnostic", "negligible spread gain and totals worsened"),
    "T8 market disagreement": ("after_open_watch", "promising direction signal; no betting authority"),
    "T9 confluence": ("frozen_prospective_shadow", "retrospective rule frozen; no betting authority"),
    "Context events": ("diagnostic", "objective timestamped register; always zero points"),
}


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assess_readiness() -> tuple[pd.DataFrame, dict[str, Any]]:
    prediction_path = ROOT / "data/nfl/predictions/2026_week01_paper_frozen.csv"
    prediction_manifest = _json(REPORTS / "step6_week01_prediction_manifest.json")
    source_manifest = _json(REPORTS / "step8_live_source_manifest.json")
    weather_manifest = _json(REPORTS / "step8_live_weather_archive_manifest.json")
    tier_audit = _json(REPORTS / "step8_tier_audit.json")
    t8 = _json(REPORTS / "step8_t8_market.json")
    t9 = _json(REPORTS / "step8_t9_confluence.json")
    predictions = pd.read_csv(prediction_path)
    qb_review = pd.read_csv(ROOT / "data/nfl/live_tiers/2026_week01_qb_review.csv")
    qb_required = ["as_of_utc", "source", "source_published_at_utc", "home_starter_id", "home_backup_id",
                   "home_starter_probability", "away_starter_id", "away_backup_id", "away_starter_probability"]
    valid_qb_rows = int(qb_review[qb_required].notna().all(axis=1).sum())
    market_files = list((ROOT / "data/nfl/markets/step7").rglob("*.csv")) if (ROOT / "data/nfl/markets/step7").exists() else []
    valid_market_quotes = 0
    for path in market_files:
        frame = pd.read_csv(path)
        if "valid_obtainable_quote" in frame:
            valid_market_quotes += int(frame.valid_obtainable_quote.astype(str).str.lower().eq("true").sum())
    blockers = []
    if _sha256(prediction_path) != prediction_manifest["sha256"]["prediction"]:
        blockers.append("frozen_prediction_hash_mismatch")
    if valid_market_quotes == 0:
        blockers.append("no_valid_timestamped_market_quotes")
    if valid_qb_rows < len(predictions):
        blockers.append("quarterback_review_incomplete")
    if not source_manifest["continuity_qualifies"]:
        blockers.append("post_cut_roster_continuity_missing")
    if source_manifest["injury_rows"] == 0:
        blockers.append("official_2026_injury_report_not_available")
    if weather_manifest["verified_coordinates"] < weather_manifest["games"]:
        blockers.append("stadium_coordinates_and_weather_capture_incomplete")

    card = predictions[["game_id", "home_team", "away_team", "ridge_fair_home_spread", "ridge_total"]].copy()
    card["t0_market"] = "FAIL" if valid_market_quotes == 0 else "PASS"
    card["t1_structural"] = "FROZEN"
    card["t2_qb"] = "UNRESOLVED"
    card["t3_continuity_injuries"] = "UNRESOLVED"
    card["t6_weather"] = "UNRESOLVED"
    card["t8_market_watch"] = "UNRESOLVED"
    card["t9_confluence"] = "UNRESOLVED"
    card["betting_decision"] = "ABSTAIN"
    card["staking_enabled"] = False

    report = {
        "status": "shadow_framework_ready_live_inputs_blocked",
        "games": len(card), "ready_to_publish_t1_paper": True, "ready_to_bet": False,
        "staking_enabled": False, "blockers": blockers,
        "tier_registry": {name: {"status": value[0], "reason": value[1]} for name, value in TIER_REGISTRY.items()},
        "historical_consolidation": {
            "development_games": tier_audit["games"],
            "t1_margin_mae": tier_audit["margin"]["t1_core"]["mae"],
            "t1_t2_t3_margin_mae": tier_audit["margin"]["t1_plus_t2_t3"]["mae"],
            "t2_t3_gain": tier_audit["stability"]["t1_plus_t2_t3"]["overall_mae_gain_vs_t1"],
            "t2_t3_better_seasons": tier_audit["stability"]["t1_plus_t2_t3"]["seasons_better_than_t1"],
            "t8_large_spread_direction": t8["spread"]["raw_ridge_direction"][-1],
            "t9_spread": t9["spread"]["overall"],
            "t9_total_oracle": t9["total"]["overall"],
        },
        "promotion_gates": {
            "minimum_frozen_predictions": 500,
            "minimum_seasons": 2,
            "market_coverage": 0.90,
            "required": ["audited_true_openers", "timestamped_obtainable_prices", "positive_mean_clv",
                         "positive_opening_beat_rate", "out_of_sample_score_gain", "no_threshold_retuning"],
            "current_promotion_allowed": False,
        },
        "next_live_actions": ["complete official QB probability review", "refresh post-cut rosters and injury reports",
                              "verify stadium coordinates and capture forecasts", "resume Odds API quote capture",
                              "run frozen T8/T9 shadow without changing thresholds"],
        "prediction_sha256": _sha256(prediction_path),
    }
    return card, report


def main() -> None:
    card, report = assess_readiness(); CARD.parent.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    card.to_csv(CARD, index=False); REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
