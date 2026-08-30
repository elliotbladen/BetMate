"""Season-level NFL rule flags available before kickoff.

These flags describe the rules in force, never an event that occurred in the
game.  They are therefore safe for historical and future pre-game features.
"""

from __future__ import annotations


def rule_era_features(season: int) -> dict[str, int]:
    """Return point-in-time rule flags for an NFL season."""
    year = int(season)
    return {
        "dynamic_kickoff_rule": int(year >= 2024),
        "onside_anytime_when_trailing": int(year >= 2025),
        "kickoff_touchback_to_35": int(year >= 2025),
        "regular_season_ot_both_possess": int(year >= 2025),
        "onside_2026_alignment_rule": int(year >= 2026),
    }

