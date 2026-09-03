"""Champions League club identity and point-in-time data-contract helpers."""

from __future__ import annotations

import re
from typing import Any


REQUIRED_MATCH_FIELDS = {
    "match_id", "season", "stage", "kickoff_utc", "home_club_id", "away_club_id",
    "home_goals", "away_goals", "source", "source_published_at_utc",
}
REQUIRED_CLUB_FIELDS = {"club_id", "canonical_name", "country", "domestic_league", "valid_from", "valid_to"}


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not cleaned:
        raise ValueError("club name cannot produce an empty identity")
    return cleaned


def build_alias_index(clubs: list[dict[str, Any]]) -> dict[str, str]:
    """Build an unambiguous alias -> canonical club ID index."""
    index: dict[str, str] = {}
    for club in clubs:
        missing = REQUIRED_CLUB_FIELDS - club.keys()
        if missing:
            raise ValueError(f"missing club fields: {', '.join(sorted(missing))}")
        club_id = str(club["club_id"]).strip()
        if club_id != slug(club_id):
            raise ValueError("club_id must be a lowercase slug")
        names = [club["canonical_name"], *(club.get("aliases") or [])]
        for name in names:
            key = slug(str(name))
            if key in index and index[key] != club_id:
                raise ValueError(f"ambiguous club alias: {name}")
            index[key] = club_id
    return index


def normalize_club(name: str, alias_index: dict[str, str]) -> str:
    key = slug(name)
    if key not in alias_index:
        raise KeyError(f"unmapped UCL club: {name}")
    return alias_index[key]


def validate_match(record: dict[str, Any]) -> dict[str, Any]:
    missing = REQUIRED_MATCH_FIELDS - record.keys()
    if missing:
        raise ValueError(f"missing match fields: {', '.join(sorted(missing))}")
    if record["home_club_id"] == record["away_club_id"]:
        raise ValueError("home and away club IDs must differ")
    if not str(record["kickoff_utc"]).endswith(("Z", "+00:00")):
        raise ValueError("kickoff_utc must be timezone-aware UTC")
    if not str(record["source_published_at_utc"]).endswith(("Z", "+00:00")):
        raise ValueError("source_published_at_utc must be timezone-aware UTC")
    for field in ("home_goals", "away_goals"):
        if int(record[field]) < 0:
            raise ValueError("goals cannot be negative")
    result = dict(record)
    result["identity_contract_version"] = "ucl-identity-v1"
    return result
