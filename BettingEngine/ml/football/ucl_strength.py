"""Cross-league Champions League club-strength state and shrinkage helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClubStrength:
    club_id: str
    attack: float
    defence: float
    league_adjustment: float
    uefa_prior: float
    observed_matches: int
    as_of_utc: str


def shrink_to_uefa_prior(observed: float, prior: float, matches: int, prior_matches: float = 12.0) -> float:
    """Reliability-weight an observed domestic rating toward the UEFA prior."""
    if matches < 0 or prior_matches <= 0:
        raise ValueError("match counts must be non-negative and prior_matches positive")
    weight = matches / (matches + prior_matches)
    return weight * float(observed) + (1.0 - weight) * float(prior)


def cross_league_strength(observed_attack: float, observed_defence: float, league_adjustment: float,
                          uefa_prior: float, observed_matches: int, as_of_utc: str, club_id: str = "pending") -> ClubStrength:
    """Create a point-in-time state; league adjustment applies equally to both ratings."""
    if not as_of_utc.endswith(("Z", "+00:00")):
        raise ValueError("as_of_utc must be timezone-aware UTC")
    return ClubStrength(
        club_id=str(club_id),
        attack=shrink_to_uefa_prior(observed_attack + league_adjustment, uefa_prior, observed_matches),
        defence=shrink_to_uefa_prior(observed_defence + league_adjustment, uefa_prior, observed_matches),
        league_adjustment=float(league_adjustment), uefa_prior=float(uefa_prior),
        observed_matches=int(observed_matches), as_of_utc=as_of_utc,
    )


def validate_strength_row(row: dict) -> dict:
    required = {"club_id", "season", "as_of_utc", "attack", "defence", "league_adjustment", "uefa_prior", "matches"}
    missing = sorted(required - row.keys())
    if missing:
        raise ValueError(f"missing strength fields: {', '.join(missing)}")
    if not str(row["as_of_utc"]).endswith(("Z", "+00:00")):
        raise ValueError("as_of_utc must be timezone-aware UTC")
    if int(row["matches"]) < 0:
        raise ValueError("matches cannot be negative")
    result = dict(row)
    result["strength_contract_version"] = "ucl-strength-v1"
    result["market_fields_used"] = False
    return result
