"""
Self-updating Elo rating system for EPL clubs.

Features:
  - K-factor starts high (40) for new/promoted teams, decays to 20 as sample grows
  - Between-season mean reversion: ratings pulled 30% toward league mean
  - Snapshot saved per gameweek for walk-forward use
  - Home advantage baked into expected score calculation

Usage:
    elo = EloTracker()
    elo.update(home="Arsenal", away="Chelsea", result="H", date=date)
    ratings = elo.ratings   # current dict {team: elo}
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_ELO      = 1500.0
HOME_ADVANTAGE   = 65.0       # Elo points added to home team's expected score
K_BASE           = 20.0       # K-factor for established teams
K_NEW            = 40.0       # K-factor for teams with < 20 games
K_NEW_THRESHOLD  = 20         # games played before dropping to K_BASE
BETWEEN_SEASON_REVERSION = 0.30  # 30% pull toward league mean at season start
MIN_REVERSION_ELO = 1400.0   # floor on reversion


class EloTracker:
    def __init__(
        self,
        initial_ratings: dict[str, float] | None = None,
        home_advantage: float = HOME_ADVANTAGE,
        k_base: float = K_BASE,
        k_new: float = K_NEW,
        k_new_threshold: int = K_NEW_THRESHOLD,
        between_season_reversion: float = BETWEEN_SEASON_REVERSION,
        draw_base: float = 0.27,
    ):
        self.ratings: dict[str, float]  = dict(initial_ratings or {})
        self.games_played: dict[str, int] = {}
        self.history: list[dict] = []   # one row per match processed
        self.home_advantage = home_advantage
        self.k_base = k_base
        self.k_new = k_new
        self.k_new_threshold = k_new_threshold
        self.reversion = between_season_reversion
        self.draw_base = draw_base

    # ── Core update ───────────────────────────────────────────────────────────

    def _k(self, team: str) -> float:
        gp = self.games_played.get(team, 0)
        if gp < self.k_new_threshold:
            # Linearly decay from K_NEW to K_BASE as games accumulate
            frac = gp / self.k_new_threshold
            return self.k_new * (1 - frac) + self.k_base * frac
        return self.k_base

    def _expected(self, elo_a: float, elo_b: float) -> float:
        """Expected score for team A (with home advantage already applied)."""
        return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400.0))

    def update(
        self,
        home: str,
        away: str,
        result: str,          # "H", "D", "A"
        date: datetime | str | None = None,
    ) -> None:
        elo_h = self.ratings.get(home, DEFAULT_ELO)
        elo_a = self.ratings.get(away, DEFAULT_ELO)

        # Apply home advantage to expected score
        exp_h = self._expected(elo_h + self.home_advantage, elo_a)
        exp_a = 1.0 - exp_h

        # Actual score
        if result == "H":
            score_h, score_a = 1.0, 0.0
        elif result == "D":
            score_h, score_a = 0.5, 0.5
        else:
            score_h, score_a = 0.0, 1.0

        k_h = self._k(home)
        k_a = self._k(away)

        new_elo_h = elo_h + k_h * (score_h - exp_h)
        new_elo_a = elo_a + k_a * (score_a - exp_a)

        self.ratings[home] = new_elo_h
        self.ratings[away] = new_elo_a
        self.games_played[home] = self.games_played.get(home, 0) + 1
        self.games_played[away] = self.games_played.get(away, 0) + 1

        if date is not None:
            self.history.append({
                "date":    str(date)[:10],
                "home":    home,
                "away":    away,
                "result":  result,
                "elo_h_before": round(elo_h, 1),
                "elo_a_before": round(elo_a, 1),
                "elo_h_after":  round(new_elo_h, 1),
                "elo_a_after":  round(new_elo_a, 1),
            })

    # ── Season boundary ────────────────────────────────────────────────────────

    def between_season_reversion(self) -> None:
        """Pull ratings toward league mean at season boundary."""
        if not self.ratings:
            return
        mean = sum(self.ratings.values()) / len(self.ratings)
        self.ratings = {
            t: max(MIN_REVERSION_ELO,
                   v * (1 - self.reversion) + mean * self.reversion)
            for t, v in self.ratings.items()
        }

    # ── Prediction ────────────────────────────────────────────────────────────

    def win_probabilities(self, home: str, away: str) -> dict[str, float]:
        """
        Estimate win/draw/loss probabilities from Elo.
        Uses the logistic transformation common in football Elo models.
        """
        elo_h = self.ratings.get(home, DEFAULT_ELO)
        elo_a = self.ratings.get(away, DEFAULT_ELO)

        exp_h = self._expected(elo_h + self.home_advantage, elo_a)

        # Approximate draw probability (declines as mismatch grows)
        draw_base = self.draw_base
        mismatch = abs(elo_h - elo_a) / 400.0
        p_draw = draw_base * (1.0 - 0.5 * mismatch)
        p_draw = max(0.05, min(0.35, p_draw))

        p_home = exp_h * (1 - p_draw)
        p_away = (1 - exp_h) * (1 - p_draw)

        # Normalise
        total = p_home + p_draw + p_away
        return {
            "p_home": round(p_home / total, 4),
            "p_draw": round(p_draw / total, 4),
            "p_away": round(p_away / total, 4),
            "elo_home": round(elo_h, 1),
            "elo_away": round(elo_a, 1),
            "elo_diff": round(elo_h - elo_a, 1),
        }

    # ── Utilities ─────────────────────────────────────────────────────────────

    def snapshot(self) -> dict[str, float]:
        return dict(self.ratings)

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"team": t, "elo": round(v, 1)}
            for t, v in sorted(self.ratings.items(), key=lambda x: -x[1])
        ])

    def save_ratings(self, path: str | Path) -> None:
        self.to_dataframe().to_csv(path, index=False)


def build_from_history(df: pd.DataFrame, as_of: datetime | None = None,
                       **elo_kwargs) -> EloTracker:
    """
    Build Elo ratings from scratch using match history.

    df must have: Date, HomeTeam, AwayTeam, FTR (H/D/A)
    as_of: only use matches before this date
    elo_kwargs: league-specific EloTracker parameters (home_advantage, k_base, ...)
    """
    elo = EloTracker(**elo_kwargs)
    data = df.sort_values("Date").copy()
    if as_of is not None:
        data = data[data["Date"] < as_of]

    current_season = None
    for _, row in data.iterrows():
        season = row.get("Season", "")
        # Apply between-season reversion at each new season
        if season and season != current_season and current_season is not None:
            elo.between_season_reversion()
        current_season = season

        elo.update(
            home=row["HomeTeam"],
            away=row["AwayTeam"],
            result=row["FTR"],
            date=row["Date"],
        )

    return elo
