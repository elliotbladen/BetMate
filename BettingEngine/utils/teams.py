"""
Single source of truth for team name canonicalization.
Reads from shared/teams.json in the BetMate root.

Usage:
    from utils.teams import to_db_name, to_matrix_key, to_odds_api_name

    to_db_name("Cronulla Sutherland Sharks")   # → "Cronulla-Sutherland Sharks"
    to_matrix_key("Manly Warringah Sea Eagles") # → "Manly Sea Eagles"
    to_odds_api_name("cronulla-sutherland sharks") # → "Cronulla Sutherland Sharks"
"""

import json
from pathlib import Path

_TEAMS_JSON = Path(__file__).parent.parent.parent / "shared" / "teams.json"

def _load():
    with open(_TEAMS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return data["NRL"] + data["AFL"]

_teams = _load()

# alias (lowercase) → field value
_alias_to_db:       dict[str, str] = {}
_alias_to_matrix:   dict[str, str] = {}
_alias_to_odds_api: dict[str, str] = {}

for t in _teams:
    for alias in t["aliases"]:
        key = alias.lower()
        _alias_to_db[key]       = t["db"]
        _alias_to_matrix[key]   = t["matrix_key"]
        _alias_to_odds_api[key] = t["odds_api"]
    # also index by each canonical field itself
    for canonical in (t["db"], t["matrix_key"], t["odds_api"]):
        key = canonical.lower()
        _alias_to_db[key]       = t["db"]
        _alias_to_matrix[key]   = t["matrix_key"]
        _alias_to_odds_api[key] = t["odds_api"]


def to_db_name(name: str) -> str:
    """Return the DB-canonical team name (full official form, e.g. 'Cronulla-Sutherland Sharks')."""
    return _alias_to_db.get(name.lower().strip(), name)


def to_matrix_key(name: str) -> str:
    """Return the BettingEngine matrix key (short form, e.g. 'Cronulla Sharks')."""
    return _alias_to_matrix.get(name.lower().strip(), name)


def to_odds_api_name(name: str) -> str:
    """Return the Odds API team name (e.g. 'Cronulla Sutherland Sharks')."""
    return _alias_to_odds_api.get(name.lower().strip(), name)


def all_nrl_matrix_keys() -> list[str]:
    with open(_TEAMS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return [t["matrix_key"] for t in data["NRL"]]


def all_afl_matrix_keys() -> list[str]:
    with open(_TEAMS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return [t["matrix_key"] for t in data["AFL"]]
