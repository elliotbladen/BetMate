"""Champions League match and tournament-market quote contract."""

from __future__ import annotations

from datetime import datetime
from typing import Any


MATCH_MARKETS = {"h2h", "asian_handicap", "totals"}
TOURNAMENT_MARKETS = {"top8", "top24", "eliminated", "final_position", "qualify", "winner"}


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("quote timestamp must include timezone")
    return parsed


def no_vig_probabilities(decimal_odds: list[float]) -> list[float]:
    if not decimal_odds or any(float(odd) <= 1.0 for odd in decimal_odds):
        raise ValueError("decimal odds must be greater than 1")
    implied = [1.0 / float(odd) for odd in decimal_odds]
    total = sum(implied)
    return [value / total for value in implied]


def validate_quote(quote: dict[str, Any], cutoff_utc: str, kickoff_utc: str | None = None) -> dict[str, Any]:
    required = {"quote_id", "market_id", "market_type", "captured_at_utc", "published_at_utc", "source", "outcomes"}
    missing = sorted(required - quote.keys())
    if missing:
        raise ValueError(f"missing quote fields: {', '.join(missing)}")
    market_type = str(quote["market_type"])
    if market_type not in MATCH_MARKETS | TOURNAMENT_MARKETS:
        raise ValueError("unknown UCL market type")
    captured, published = (_utc(quote[field]) for field in ("captured_at_utc", "published_at_utc"))
    cutoff_dt = _utc(cutoff_utc)
    if published > cutoff_dt or captured < published:
        raise ValueError("quote timing is inconsistent with cutoff")
    if kickoff_utc and cutoff_dt >= _utc(kickoff_utc):
        raise ValueError("cutoff must precede kickoff")
    outcomes = quote["outcomes"]
    if not isinstance(outcomes, list) or len(outcomes) < 2:
        raise ValueError("quote requires at least two outcomes")
    odds = [float(item["decimal_odds"]) for item in outcomes]
    result = dict(quote)
    result["no_vig_probability"] = no_vig_probabilities(odds)
    result["market_fields_used_in_model"] = False
    result["qualification_status"] = "valid"
    return result


def validate_unverified_closing_quote(quote: dict[str, Any]) -> dict[str, Any]:
    """Validate a static bookmaker close when no timestamp is supplied."""
    required = {"quote_id", "market_id", "market_type", "source", "outcomes"}
    missing = sorted(required - quote.keys())
    if missing:
        raise ValueError(f"missing static quote fields: {', '.join(missing)}")
    if quote["market_type"] not in MATCH_MARKETS | TOURNAMENT_MARKETS:
        raise ValueError("unknown UCL market type")
    outcomes = quote["outcomes"]
    if not isinstance(outcomes, list) or len(outcomes) < 2:
        raise ValueError("quote requires at least two outcomes")
    result = dict(quote)
    result["no_vig_probability"] = no_vig_probabilities([float(item["decimal_odds"]) for item in outcomes])
    result["closing_status"] = "unverified_static_close"
    result["market_fields_used_in_model"] = False
    result["qualification_status"] = "provisional"
    return result
