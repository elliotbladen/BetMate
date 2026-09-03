"""Validation of the UEFA Champions League league-phase draw graph."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .ucl_rules import RULES


def validate_draw_graph(clubs: list[dict[str, Any]], fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate sourced league-phase fixtures against the frozen UCL rules."""
    if len(clubs) != RULES.league_phase_teams:
        raise ValueError(f"league phase requires {RULES.league_phase_teams} clubs")
    ids = [str(club.get("club_id", "")) for club in clubs]
    if len(set(ids)) != len(ids) or any(not club_id for club_id in ids):
        raise ValueError("club IDs must be present and unique")
    expected_fixtures = RULES.league_phase_teams * RULES.league_phase_matches_per_team // 2
    if len(fixtures) != expected_fixtures:
        raise ValueError(f"league phase requires {expected_fixtures} unique fixtures, got {len(fixtures)}")
    pots = {club["club_id"]: int(club.get("coefficient_pot", 0)) for club in clubs}
    associations = {club["club_id"]: str(club.get("association", "")) for club in clubs}
    if set(pots.values()) != {1, 2, 3, 4} or any(list(pots.values()).count(pot) != 9 for pot in (1, 2, 3, 4)):
        raise ValueError("each of four coefficient pots must contain nine clubs")
    seen: set[tuple[str, str]] = set()
    opponents: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for fixture in fixtures:
        home, away = fixture.get("home_club_id"), fixture.get("away_club_id")
        if home not in pots or away not in pots or home == away:
            raise ValueError("fixture contains unknown or duplicate club")
        pair = tuple(sorted((home, away)))
        if pair in seen:
            raise ValueError("duplicate club pairing")
        seen.add(pair)
        opponents[home].append((away, "home")); opponents[away].append((home, "away"))
    errors = []
    for club_id in ids:
        rows = opponents[club_id]
        if len(rows) != RULES.league_phase_matches_per_team:
            errors.append(f"{club_id}: expected eight opponents, got {len(rows)}")
            continue
        if sum(side == "home" for _, side in rows) != RULES.league_phase_home_matches:
            errors.append(f"{club_id}: home-match count is not four")
        pot_counts = Counter(pots[opponent] for opponent, _ in rows)
        if any(pot_counts[pot] != RULES.opponents_per_pot for pot in (1, 2, 3, 4)):
            errors.append(f"{club_id}: opponents are not two per coefficient pot")
        association_counts = Counter(associations[opponent] for opponent, _ in rows)
        if any(count > RULES.same_association_max_opponents for count in association_counts.values()):
            errors.append(f"{club_id}: exceeds same-association opponent limit")
    if errors:
        raise ValueError("; ".join(errors))
    return {"status": "valid", "clubs": len(clubs), "fixtures": len(fixtures),
            "matches_per_club": RULES.league_phase_matches_per_team,
            "rules_version": RULES.version}
