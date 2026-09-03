"""Champions League two-legged knockout and final probability simulator."""

from __future__ import annotations

from typing import Any

import numpy as np


def resolve_tie(aggregate_home: int, aggregate_away: int, rng: np.random.Generator,
                home_penalty_probability: float = 0.5) -> str:
    """Resolve a tied aggregate after extra time, then penalties (no away goals)."""
    if aggregate_home > aggregate_away:
        return "home"
    if aggregate_away > aggregate_home:
        return "away"
    # Extra time is represented as one additional 30-minute Poisson draw.
    et_home, et_away = int(rng.poisson(0.25)), int(rng.poisson(0.20))
    if et_home > et_away:
        return "home"
    if et_away > et_home:
        return "away"
    return "home" if rng.random() < home_penalty_probability else "away"


def simulate_two_leg_tie(first_leg: dict[str, Any], second_leg: dict[str, Any], simulations: int = 10000,
                         seed: int = 20260901) -> dict[str, Any]:
    """Return qualification probabilities for a tie with a known first leg."""
    required = {"home_club_id", "away_club_id", "home_goals", "away_goals", "home_xg", "away_xg"}
    for leg in (first_leg, second_leg):
        missing = required - leg.keys()
        if missing:
            raise ValueError(f"missing knockout fields: {', '.join(sorted(missing))}")
    if first_leg["home_club_id"] != second_leg["away_club_id"] or first_leg["away_club_id"] != second_leg["home_club_id"]:
        raise ValueError("second leg must reverse first-leg home and away clubs")
    if simulations <= 0:
        raise ValueError("simulations must be positive")
    if any(float(leg[field]) < 0 for leg in (first_leg, second_leg) for field in ("home_xg", "away_xg")):
        raise ValueError("expected goals cannot be negative")
    rng = np.random.default_rng(seed)
    home_id, away_id = first_leg["home_club_id"], first_leg["away_club_id"]
    counts = {home_id: 0, away_id: 0}
    for _ in range(simulations):
        second_home = int(rng.poisson(float(second_leg["home_xg"])))
        second_away = int(rng.poisson(float(second_leg["away_xg"])))
        # First-leg home becomes second-leg away; no away-goals weighting.
        aggregate_home = int(first_leg["home_goals"]) + second_away
        aggregate_away = int(first_leg["away_goals"]) + second_home
        winner = resolve_tie(aggregate_home, aggregate_away, rng)
        counts[home_id if winner == "home" else away_id] += 1
    return {"status": "simulated", "simulations": simulations, "home_club_id": home_id,
            "away_club_id": away_id, "home_qualification_probability": counts[home_id] / simulations,
            "away_qualification_probability": counts[away_id] / simulations,
            "away_goals_rule": False, "resolution": "aggregate_then_extra_time_then_penalties",
            "rules_version": "ucl-2026-27-regulations-v1"}


def simulate_final(home_xg: float, away_xg: float, simulations: int = 10000, seed: int = 20260901) -> dict[str, float | int | str]:
    """Simulate the neutral single-match final, including extra time and penalties."""
    if simulations <= 0 or home_xg < 0 or away_xg < 0:
        raise ValueError("invalid final simulation inputs")
    rng = np.random.default_rng(seed); home_wins = 0; away_wins = 0; regulation_draws = 0; extra_time_decisions = 0; penalty_decisions = 0
    for _ in range(simulations):
        hg, ag = int(rng.poisson(home_xg)), int(rng.poisson(away_xg))
        if hg == ag:
            regulation_draws += 1
            winner_before = resolve_tie(hg, ag, rng, home_penalty_probability=0.5)
            # resolve_tie includes ET and penalties; classify the final winner.
            if winner_before == "home": home_wins += 1
            else: away_wins += 1
        elif hg > ag:
            home_wins += 1
        else: away_wins += 1
    return {"status": "simulated", "simulations": simulations, "home_win_probability": home_wins / simulations,
            "away_win_probability": away_wins / simulations, "regulation_draw_probability": regulation_draws / simulations, "neutral_final": True,
            "rules_version": "ucl-2026-27-regulations-v1"}
