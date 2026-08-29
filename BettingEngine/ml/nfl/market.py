"""Book-level market snapshot normalisation."""

from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Iterable

from .contracts import MarketSnapshot, SnapshotStage


def consensus_snapshot(
    snapshots: Iterable[MarketSnapshot],
    *,
    stage: SnapshotStage,
    captured_at: datetime,
) -> MarketSnapshot:
    rows = list(snapshots)
    if not rows:
        raise ValueError("cannot build consensus from no snapshots")
    game_ids = {row.game_id for row in rows}
    if len(game_ids) != 1:
        raise ValueError("consensus snapshots must belong to one game")

    def med(name: str) -> float | None:
        values = [getattr(row, name) for row in rows if getattr(row, name) is not None]
        return float(median(values)) if values else None

    return MarketSnapshot(
        game_id=rows[0].game_id,
        captured_at=captured_at,
        stage=stage,
        home_spread=med("home_spread"),
        total=med("total"),
        home_spread_price=med("home_spread_price"),
        away_spread_price=med("away_spread_price"),
        over_price=med("over_price"),
        under_price=med("under_price"),
    )
