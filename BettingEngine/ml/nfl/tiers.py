"""NFL tier application with caps, auditability and score coherence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .contracts import TierAdjustment, TierMode


@dataclass(frozen=True)
class AdjustedPrice:
    home_margin: float
    total: float
    expected_home_points: float
    expected_away_points: float
    applied: tuple[TierAdjustment, ...]
    shadow: tuple[TierAdjustment, ...]


def apply_tiers(
    base_home_margin: float,
    base_total: float,
    adjustments: Iterable[TierAdjustment],
) -> AdjustedPrice:
    """Apply active tiers only; retain shadow tiers for prospective evaluation."""

    rows = tuple(adjustments)
    active = tuple(row for row in rows if row.mode is TierMode.ACTIVE)
    shadow = tuple(row for row in rows if row.mode is TierMode.SHADOW)
    margin = base_home_margin + sum(row.margin_points for row in active)
    total = base_total + sum(row.total_points for row in active)
    home = (total + margin) / 2.0
    away = (total - margin) / 2.0
    if min(home, away) < 0:
        raise ValueError("tier adjustments imply a negative expected team score")
    return AdjustedPrice(margin, total, home, away, active, shadow)
