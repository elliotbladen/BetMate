"""Market-relative evaluation helpers for horse-racing confluence cards."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping


def evaluate(rows: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """Evaluate cards by tier against no-vig market expectation and realised ROI.

    Required fields: tier, market_probability, outcome (0/1), decimal_odds.
    Every input row represents one runner priced before its race cutoff.
    """
    buckets: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        outcome = int(row["outcome"])
        probability = float(row["market_probability"])
        odds = float(row["decimal_odds"])
        if outcome not in (0, 1) or not 0 < probability < 1 or odds <= 1:
            raise ValueError("invalid backtest row")
        buckets[str(row["tier"])].append(row)

    segments = {tier: _metrics(items) for tier, items in sorted(buckets.items())}
    return {"segments": segments, "overall": _metrics([r for rows_ in buckets.values() for r in rows_])}


def _metrics(rows: list[Mapping[str, object]]) -> dict[str, float | int]:
    if not rows:
        return {"bets": 0, "expected_wins": 0.0, "actual_wins": 0, "market_lift": 0.0, "roi": 0.0}
    expected = sum(float(row["market_probability"]) for row in rows)
    actual = sum(int(row["outcome"]) for row in rows)
    profit = sum(int(row["outcome"]) * float(row["decimal_odds"]) - 1.0 for row in rows)
    return {
        "bets": len(rows),
        "expected_wins": expected,
        "actual_wins": actual,
        "market_lift": actual / expected - 1.0 if expected else 0.0,
        "roi": profit / len(rows),
    }
