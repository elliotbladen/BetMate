"""Training-only temperature calibration for complete multi-runner books."""

from __future__ import annotations

import math
from typing import Iterable


def temperature_book(probabilities: Iterable[float], temperature: float) -> list[float]:
    if temperature <= 0: raise ValueError("temperature must be positive")
    values = list(probabilities)
    if not values or any(value <= 0 for value in values): raise ValueError("probabilities must be positive")
    powered = [value ** (1.0 / temperature) for value in values]; total = sum(powered)
    return [value / total for value in powered]


def fit_temperature(races: list[tuple[list[float], int]], candidates: Iterable[float] | None = None) -> dict:
    """Grid fit on an explicitly supplied training population; no hidden test use."""
    grid = list(candidates or [value / 100 for value in range(50, 201)])
    if not races: return {"status": "INSUFFICIENT_TRAINING_PREDICTIONS", "temperature": None, "races": 0}
    scored = []
    for temperature in grid:
        loss = sum(-math.log(max(temperature_book(book, temperature)[winner], 1e-12))
                   for book, winner in races) / len(races)
        scored.append((loss, temperature))
    loss, temperature = min(scored)
    return {"status": "FIT", "temperature": temperature, "training_log_loss": loss,
            "races": len(races), "method": "training-only-grid-temperature-v1"}
