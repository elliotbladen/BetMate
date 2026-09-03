"""Champions League league-phase table and qualification simulator."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from .ucl_draw import validate_draw_graph


def rank_table(records: list[dict[str, Any]], clubs: list[dict[str, Any]]) -> list[str]:
    """Rank one simulated table using the published league-phase ordering."""
    stats = {club["club_id"]: {"points": 0, "gf": 0, "ga": 0, "away_gf": 0, "wins": 0, "away_wins": 0} for club in clubs}
    for record in records:
        home, away = record["home_club_id"], record["away_club_id"]
        hg, ag = int(record["home_goals"]), int(record["away_goals"])
        stats[home]["gf"] += hg; stats[home]["ga"] += ag; stats[home]["away_gf"] += 0
        stats[away]["gf"] += ag; stats[away]["ga"] += hg; stats[away]["away_gf"] += ag
        if hg > ag:
            stats[home]["points"] += 3; stats[home]["wins"] += 1
        elif ag > hg:
            stats[away]["points"] += 3; stats[away]["wins"] += 1; stats[away]["away_wins"] += 1
        else:
            stats[home]["points"] += 1; stats[away]["points"] += 1
    return sorted(stats, key=lambda club: (stats[club]["points"], stats[club]["gf"] - stats[club]["ga"],
                                           stats[club]["gf"], stats[club]["away_gf"], stats[club]["wins"],
                                           stats[club]["away_wins"], club), reverse=True)


def simulate_league_phase(clubs: list[dict[str, Any]], fixtures: list[dict[str, Any]],
                          expected_goals: dict[str, tuple[float, float]], simulations: int = 10000,
                          seed: int = 20260901) -> pd.DataFrame:
    """Simulate remaining single-leg league-phase fixtures."""
    if simulations <= 0:
        raise ValueError("simulations must be positive")
    validate_draw_graph(clubs, fixtures)
    club_ids = {club["club_id"] for club in clubs}
    if set(expected_goals) != club_ids:
        raise ValueError("expected_goals must contain every league-phase club")
    if any(min(pair) < 0 for pair in expected_goals.values()):
        raise ValueError("expected goals cannot be negative")
    rng = np.random.default_rng(seed)
    counts = defaultdict(lambda: {"top8": 0, "playoff9_24": 0, "eliminated25_36": 0, "position_sum": 0.0})
    for _ in range(simulations):
        results = []
        for fixture in fixtures:
            home, away = fixture["home_club_id"], fixture["away_club_id"]
            home_xg, away_xg = expected_goals[home][0], expected_goals[away][1]
            results.append({"home_club_id": home, "away_club_id": away,
                            "home_goals": int(rng.poisson(home_xg)), "away_goals": int(rng.poisson(away_xg))})
        ranking = rank_table(results, clubs)
        for position, club_id in enumerate(ranking, start=1):
            counts[club_id]["position_sum"] += position
            if position <= 8: counts[club_id]["top8"] += 1
            elif position <= 24: counts[club_id]["playoff9_24"] += 1
            else: counts[club_id]["eliminated25_36"] += 1
    rows = []
    for club in sorted(club_ids):
        values = counts[club]
        rows.append({"club_id": club, "simulations": simulations,
                     "top8_probability": values["top8"] / simulations,
                     "playoff9_24_probability": values["playoff9_24"] / simulations,
                     "eliminated25_36_probability": values["eliminated25_36"] / simulations,
                     "expected_position": values["position_sum"] / simulations,
                     "rules_version": "ucl-2026-27-regulations-v1"})
    return pd.DataFrame(rows)
