"""Timestamped contracts for leakage-safe NFL pricing.

Spread convention throughout: the home team's handicap. Buffalo -3 is ``-3.0``;
Buffalo +3 is ``+3.0``. A fair spread is the model's equivalent home handicap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping

from .data_contract import validate_game_identity


class SnapshotStage(str, Enum):
    PRE_OPEN = "pre_open"
    OPEN = "open"
    CURRENT = "current"
    CLOSE = "close"


class EngineKind(str, Enum):
    STRUCTURAL = "structural"
    ML_SHADOW = "ml_shadow"
    MARKET_SHADOW = "market_shadow"


class TierMode(str, Enum):
    ACTIVE = "active"
    SHADOW = "shadow"
    DISABLED = "disabled"


@dataclass(frozen=True)
class TierAdjustment:
    """Auditable adjustment in football points, before the spread sign flip."""

    tier: str
    margin_points: float = 0.0
    total_points: float = 0.0
    cap_points: float = 0.0
    mode: TierMode = TierMode.SHADOW
    reason: str = ""

    def __post_init__(self) -> None:
        if self.cap_points < 0:
            raise ValueError("cap_points cannot be negative")
        if self.cap_points and (
            abs(self.margin_points) > self.cap_points
            or abs(self.total_points) > self.cap_points
        ):
            raise ValueError(f"{self.tier} adjustment exceeds its cap")


def _aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True)
class MarketSnapshot:
    game_id: str
    captured_at: datetime
    stage: SnapshotStage
    home_spread: float | None = None
    total: float | None = None
    home_spread_price: float | None = None
    away_spread_price: float | None = None
    over_price: float | None = None
    under_price: float | None = None
    bookmaker: str = "consensus"

    def __post_init__(self) -> None:
        _aware(self.captured_at, "captured_at")
        if not self.game_id:
            raise ValueError("game_id is required")
        if not self.bookmaker.strip():
            raise ValueError("bookmaker is required")
        if self.home_spread is None and self.total is None:
            raise ValueError("market snapshot must contain a spread or total")
        if self.home_spread is not None and not -40.0 <= self.home_spread <= 40.0:
            raise ValueError("home_spread is outside the NFL contract range")
        if self.total is not None and not 10.0 <= self.total <= 100.0:
            raise ValueError("total is outside the NFL contract range")
        for name in ("home_spread_price", "away_spread_price", "over_price", "under_price"):
            price = getattr(self, name)
            if price is not None and price <= 1.0:
                raise ValueError(f"{name} must use decimal odds greater than 1")


@dataclass(frozen=True)
class GameFeatures:
    game_id: str
    season: int
    week: int
    home_team: str
    away_team: str
    kickoff_at: datetime
    as_of: datetime
    values: Mapping[str, float | int | str | bool | None]
    source_timestamps: Mapping[str, datetime] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _aware(self.kickoff_at, "kickoff_at")
        _aware(self.as_of, "as_of")
        validate_game_identity(self.game_id, self.season, self.week, self.home_team, self.away_team)
        if self.as_of >= self.kickoff_at:
            raise ValueError("features must be frozen before kickoff")
        future = [name for name, timestamp in self.source_timestamps.items() if timestamp > self.as_of]
        if future:
            raise ValueError(f"feature sources newer than as_of: {', '.join(sorted(future))}")


@dataclass(frozen=True)
class PricePrediction:
    game_id: str
    generated_at: datetime
    fair_home_spread: float
    fair_total: float
    home_win_probability: float
    margin_sigma: float
    total_sigma: float
    model_version: str
    feature_as_of: datetime
    engine: EngineKind = EngineKind.STRUCTURAL
    abstain_reason: str | None = None
    adjustments: tuple[TierAdjustment, ...] = ()

    def __post_init__(self) -> None:
        _aware(self.generated_at, "generated_at")
        _aware(self.feature_as_of, "feature_as_of")
        if not self.game_id or not self.model_version.strip():
            raise ValueError("game_id and model_version are required")
        if self.feature_as_of > self.generated_at:
            raise ValueError("feature_as_of cannot be after prediction generation")
        if not 0.0 < self.home_win_probability < 1.0:
            raise ValueError("home_win_probability must be strictly between 0 and 1")
        if self.margin_sigma <= 0 or self.total_sigma <= 0:
            raise ValueError("prediction uncertainty must be positive")

    @property
    def expected_home_margin(self) -> float:
        return -self.fair_home_spread

    @property
    def expected_scores(self) -> tuple[float, float]:
        home = (self.fair_total + self.expected_home_margin) / 2.0
        away = (self.fair_total - self.expected_home_margin) / 2.0
        return home, away


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
