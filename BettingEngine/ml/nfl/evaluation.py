"""Opening-line and CLV evaluation for NFL spread predictions."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import mean
from typing import Iterable


@dataclass(frozen=True)
class OpeningBeatResult:
    model_error_to_close: float
    opener_error_to_close: float
    improvement_points: float
    beat_open: bool
    push: bool
    recommended_side: str
    clv_points: float


def grade_spread_against_open(
    fair_home_spread: float,
    opening_home_spread: float,
    closing_home_spread: float,
    *,
    tolerance: float = 0.25,
) -> OpeningBeatResult:
    """Grade a pre-open fair spread against the later opener and close.

    Primary win: the model is closer to the closing market than the opener was.
    CLV uses the side the model would take at open. Positive values mean that
    side received a better number at open than was available at close.
    """
    model_error = abs(fair_home_spread - closing_home_spread)
    opener_error = abs(opening_home_spread - closing_home_spread)
    improvement = opener_error - model_error
    if fair_home_spread < opening_home_spread:
        side = "home"
        clv = opening_home_spread - closing_home_spread
    elif fair_home_spread > opening_home_spread:
        side = "away"
        clv = closing_home_spread - opening_home_spread
    else:
        side = "no_bet"
        clv = 0.0
    return OpeningBeatResult(
        model_error_to_close=model_error,
        opener_error_to_close=opener_error,
        improvement_points=improvement,
        beat_open=improvement > tolerance,
        push=abs(improvement) <= tolerance,
        recommended_side=side,
        clv_points=clv,
    )


@dataclass(frozen=True)
class OpeningBeatSummary:
    games: int
    wins: int
    pushes: int
    losses: int
    win_rate_ex_pushes: float
    mean_improvement_points: float
    mean_clv_points: float
    model_rmse_to_close: float
    opener_rmse_to_close: float


def summarise(results: Iterable[OpeningBeatResult]) -> OpeningBeatSummary:
    rows = list(results)
    if not rows:
        raise ValueError("at least one result is required")
    wins = sum(row.beat_open for row in rows)
    pushes = sum(row.push for row in rows)
    losses = len(rows) - wins - pushes
    decisions = wins + losses
    return OpeningBeatSummary(
        games=len(rows),
        wins=wins,
        pushes=pushes,
        losses=losses,
        win_rate_ex_pushes=wins / decisions if decisions else 0.0,
        mean_improvement_points=mean(row.improvement_points for row in rows),
        mean_clv_points=mean(row.clv_points for row in rows),
        model_rmse_to_close=sqrt(mean(row.model_error_to_close ** 2 for row in rows)),
        opener_rmse_to_close=sqrt(mean(row.opener_error_to_close ** 2 for row in rows)),
    )
