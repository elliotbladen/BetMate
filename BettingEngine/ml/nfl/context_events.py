"""Point-in-time NFL context-event register; never an automatic points tier."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


EVENT_TYPES = {
    "head_coach_change",
    "bereavement",
    "milestone",
    "player_return",
    "rivalry",
    "playoff_elimination",
}


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate_context_event(event: dict[str, Any], kickoff_utc: str, cutoff_utc: str) -> dict[str, Any]:
    """Validate that an objective event was publicly knowable before cutoff."""
    required = {"event_id", "game_id", "team", "event_type", "announced_at", "source_url", "source_kind"}
    missing = sorted(required - event.keys())
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")
    if event["event_type"] not in EVENT_TYPES:
        raise ValueError("unknown event_type")
    if event["source_kind"] not in {"nfl", "team", "league_transaction", "reputable_news"}:
        raise ValueError("source_kind is not permitted")
    if not str(event["source_url"]).startswith("https://"):
        raise ValueError("source_url must be HTTPS")
    announced, cutoff, kickoff = _utc(event["announced_at"]), _utc(cutoff_utc), _utc(kickoff_utc)
    if announced > cutoff:
        raise ValueError("event was not public by the model cutoff")
    if cutoff >= kickoff:
        raise ValueError("model cutoff must precede kickoff")
    result = dict(event)
    result.update({
        "eligible_for_research": True,
        "model_points": 0.0,
        "betting_action": "none",
        "routing": "t2_availability" if event["event_type"] == "player_return" else
                   "t1_schedule" if event["event_type"] in {"rivalry", "playoff_elimination"} else
                   "context_diagnostic",
    })
    return result
