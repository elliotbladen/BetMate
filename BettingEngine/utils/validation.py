"""
Pydantic validation models for BettingEngine ingestion boundaries.

Use these at the point where external data (scrapers, CSV, JSON) enters
the system. A ValidationError here means the scraper output changed format
or contains a bad team name — catch it early rather than silently pricing wrong.

Usage:
    from utils.validation import validate_injuries, validate_fixture

    records = validate_injuries(json.load(open("latest-injuries.json")))
    fixture = validate_fixture(json.load(open("latest-fixture.json")))
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator, ValidationError

log = logging.getLogger(__name__)

# Load valid team names from shared/teams.json
_TEAMS_JSON = Path(__file__).parent.parent.parent / "shared" / "teams.json"
_data = json.loads(_TEAMS_JSON.read_text(encoding="utf-8"))
_VALID_TEAMS: set[str] = set()
for _league in _data.values():
    for _t in _league:
        _VALID_TEAMS.add(_t["db"])
        _VALID_TEAMS.add(_t["matrix_key"])
        _VALID_TEAMS.add(_t["odds_api"])
        for _a in _t["aliases"]:
            _VALID_TEAMS.add(_a)
            _VALID_TEAMS.add(_a.title())


# ─── Injury record ───────────────────────────────────────────────────────────

class InjuryRecord(BaseModel):
    season: int
    round: int
    team: str
    player: str
    role: Literal["fullback", "halfback", "five_eighth", "hooker", "pack", "other"]
    importance_tier: Literal["elite", "key", "rotation"]
    status: Literal["out", "doubtful", "managed", "available"]
    notes: str = ""
    scraped_at: str = ""

    @field_validator("team")
    @classmethod
    def team_must_be_known(cls, v: str) -> str:
        if v not in _VALID_TEAMS:
            raise ValueError(
                f"Unknown team name: {v!r}. "
                "Add to shared/teams.json if this is a new team."
            )
        return v


def validate_injuries(raw: list[dict]) -> list[InjuryRecord]:
    """
    Validate a list of injury dicts. Returns validated records.
    Logs a warning for each invalid record but does NOT raise — bad records
    are skipped rather than blocking the whole pipeline.
    """
    valid: list[InjuryRecord] = []
    for i, item in enumerate(raw):
        try:
            valid.append(InjuryRecord(**item))
        except ValidationError as exc:
            log.warning("Injury record %d invalid — skipping: %s", i, exc)
    if len(valid) < len(raw):
        log.warning("%d of %d injury records failed validation", len(raw) - len(valid), len(raw))
    return valid


# ─── Fixture game ─────────────────────────────────────────────────────────────

class FixtureGame(BaseModel):
    season: int
    round: int
    home_team: str
    away_team: str
    venue: str
    kickoff_utc: str
    kickoff_local: str = ""

    @field_validator("home_team", "away_team")
    @classmethod
    def team_must_be_known(cls, v: str) -> str:
        if v not in _VALID_TEAMS:
            raise ValueError(
                f"Unknown team name: {v!r}. "
                "Add to shared/teams.json if this is a new team."
            )
        return v


class FixtureFile(BaseModel):
    season: int
    round: int
    scraped_at: str = ""
    game_count: int = 0
    games: list[FixtureGame]


def validate_fixture(raw: dict) -> FixtureFile:
    """
    Validate a fixture JSON dict. Raises ValidationError if structure is wrong.
    Team name errors are logged per-game and those games are dropped.
    """
    # Validate games individually so one bad team doesn't block the round
    games_raw = raw.get("games", [])
    valid_games = []
    for i, g in enumerate(games_raw):
        try:
            valid_games.append(FixtureGame(**g))
        except ValidationError as exc:
            log.warning("Fixture game %d invalid — skipping: %s", i, exc)

    patched = {**raw, "games": [g.model_dump() for g in valid_games]}
    return FixtureFile(**patched)
