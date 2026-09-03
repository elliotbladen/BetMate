"""UCL tier stack: shared EPL/EFL shadows plus phase-specific diagnostics."""
from __future__ import annotations

TIERS = {
    "T0": {"name": "data_health", "mode": "active"},
    "T1": {"name": "club_strength", "mode": "active_paper"},
    "T2": {"name": "injury_availability_player_shadow", "mode": "shadow",
           "features": ["injury_status", "expected_minutes", "player_impact", "replacement_level", "suspension"]},
    "T3": {"name": "matchup_schedule_shadow", "mode": "shadow"},
    "T4": {"name": "league_phase_incentive_shadow", "mode": "shadow", "phase": "league_phase"},
    "T5": {"name": "knockout_aggregate_shadow", "mode": "shadow", "phase": "knockout"},
    "T6": {"name": "context_weather", "mode": "diagnostic"},
    "T7": {"name": "market_disagreement", "mode": "diagnostic"},
    "T8": {"name": "confluence", "mode": "diagnostic"},
}

def status(phase: str | None = None) -> dict:
    active = {k: v for k, v in TIERS.items() if phase is None or "phase" not in v or v["phase"] == phase or v["mode"] in ("active", "active_paper")}
    return {"tiers": active, "player_shadow": "T2", "production_price_influence": ["T0", "T1"], "phase": phase or "all"}
