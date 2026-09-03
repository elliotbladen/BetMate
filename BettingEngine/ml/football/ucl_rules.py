"""Frozen UEFA Champions League competition rules for the UCL model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


RULES_VERSION = "ucl-2026-27-regulations-v1"
LEAGUE_PHASE_TEAMS = 36
LEAGUE_PHASE_MATCHES_PER_TEAM = 8
LEAGUE_PHASE_POTS = 4

STAGES = (
    "qualifying_phase",
    "league_phase",
    "knockout_phase_play_off",
    "round_of_16",
    "quarter_final",
    "semi_final",
    "final",
)


@dataclass(frozen=True)
class UCLRules:
    version: str = RULES_VERSION
    league_phase_teams: int = LEAGUE_PHASE_TEAMS
    league_phase_matches_per_team: int = LEAGUE_PHASE_MATCHES_PER_TEAM
    league_phase_home_matches: int = 4
    league_phase_away_matches: int = 4
    opponents_per_pot: int = 2
    coefficient_pots: int = LEAGUE_PHASE_POTS
    direct_round_of_16_places: tuple[int, int] = (1, 8)
    playoff_places: tuple[int, int] = (9, 24)
    eliminated_places: tuple[int, int] = (25, 36)
    same_association_max_opponents: int = 2
    knockout_legs: int = 2
    final_legs: int = 1
    away_goals_rule: bool = False
    extra_time_minutes: int = 30
    penalties_after_extra_time: bool = True

    def __post_init__(self) -> None:
        if self.league_phase_home_matches + self.league_phase_away_matches != self.league_phase_matches_per_team:
            raise ValueError("league phase home/away matches must sum to total matches")
        if self.opponents_per_pot * self.coefficient_pots != self.league_phase_matches_per_team:
            raise ValueError("pot allocation must sum to league phase matches")
        if self.playoff_places[0] != self.direct_round_of_16_places[1] + 1:
            raise ValueError("play-off places must follow direct qualifiers")
        if self.eliminated_places[0] != self.playoff_places[1] + 1:
            raise ValueError("eliminated places must follow play-off places")
        if self.eliminated_places[1] != self.league_phase_teams:
            raise ValueError("placement ranges must cover all league phase teams")
        if self.away_goals_rule:
            raise ValueError("away goals rule is prohibited")


RULES = UCLRules()


def validate_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    required = {"fixture_id", "season", "stage", "home_club", "away_club", "kickoff_utc"}
    missing = sorted(required - fixture.keys())
    if missing:
        raise ValueError(f"missing fixture fields: {', '.join(missing)}")
    if fixture["stage"] not in STAGES:
        raise ValueError("unknown UCL stage")
    if fixture["home_club"] == fixture["away_club"]:
        raise ValueError("home and away clubs must differ")
    if not str(fixture["kickoff_utc"]).endswith(("Z", "+00:00")):
        raise ValueError("kickoff_utc must be timezone-aware UTC")
    result = dict(fixture)
    result["rules_version"] = RULES_VERSION
    result["away_goals_rule"] = False
    result["qualification_resolution"] = "aggregate_then_extra_time_then_penalties" if fixture["stage"] != "league_phase" else "league_table"
    return result


def placement_route(place: int) -> str:
    if not 1 <= place <= LEAGUE_PHASE_TEAMS:
        raise ValueError("league phase place must be 1 through 36")
    if place <= 8:
        return "direct_round_of_16"
    if place <= 24:
        return "knockout_phase_play_off"
    return "eliminated"
