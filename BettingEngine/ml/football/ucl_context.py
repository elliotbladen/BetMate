"""Timestamped UCL squad, rotation, rest and travel context helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


ROLE_WEIGHTS = {"goalkeeper": 1.25, "defender": 1.0, "midfielder": 0.9, "forward": 1.1, "coach": 0.5}
VALID_STATUS = {"available", "doubtful", "injured", "suspended", "rested", "unconfirmed"}


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def validate_player_event(event: dict[str, Any], cutoff_utc: str, kickoff_utc: str) -> dict[str, Any]:
    required = {"event_id", "club_id", "player_id", "role", "status", "expected_minutes_share",
                "announced_at_utc", "source", "source_published_at_utc"}
    missing = sorted(required - event.keys())
    if missing:
        raise ValueError(f"missing player event fields: {', '.join(missing)}")
    if event["role"] not in ROLE_WEIGHTS or event["status"] not in VALID_STATUS:
        raise ValueError("invalid player role or status")
    share = float(event["expected_minutes_share"])
    if not 0.0 <= share <= 1.0:
        raise ValueError("expected_minutes_share must be between zero and one")
    announced, published = _utc(event["announced_at_utc"]), _utc(event["source_published_at_utc"])
    cutoff, kickoff = _utc(cutoff_utc), _utc(kickoff_utc)
    if announced > cutoff or published > cutoff:
        raise ValueError("player information was not public by cutoff")
    if cutoff >= kickoff:
        raise ValueError("cutoff must precede kickoff")
    result = dict(event)
    result["role_weight"] = ROLE_WEIGHTS[event["role"]]
    result["availability_signal"] = share if event["status"] == "available" else 0.0 if event["status"] in {"injured", "suspended", "rested"} else share * 0.5
    result["model_points"] = 0.0
    result["market_fields_used"] = False
    return result


@dataclass(frozen=True)
class MatchContext:
    match_id: str
    club_id: str
    rest_days: float
    travel_km: float
    timezone_shift_hours: float
    domestic_match_within_days: int
    as_of_utc: str

    def __post_init__(self) -> None:
        _utc(self.as_of_utc)
        if min(self.rest_days, self.travel_km, self.timezone_shift_hours, self.domestic_match_within_days) < 0:
            raise ValueError("context quantities cannot be negative")


def context_signal(context: MatchContext) -> dict[str, float | str]:
    """Return capped diagnostic features; no direct point adjustment."""
    return {"rest_days": float(context.rest_days), "travel_km": float(context.travel_km),
            "timezone_shift_hours": float(context.timezone_shift_hours),
            "domestic_match_within_days": float(context.domestic_match_within_days),
            "signal_mode": "shadow_no_points"}
