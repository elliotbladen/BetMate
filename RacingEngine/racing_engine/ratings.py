"""Transparent V0 performance ratings from authorised official results.

This is a deliberately conservative starting point, not a finished wagering
model. It uses relative beaten-length performance within each race, shrinks
lightly raced horses to neutral, and persists reproducible snapshots. Track
pars, class, weight and sectionals are separate additions once their history is
in the canonical database.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from .storage import RacingStore


MODEL_VERSION = "base-lengths-v0.1"
NEUTRAL_RATING = 100.0
RATING_SCALE = 18.0
LENGTH_DECAY = 2.25
UPDATE_K = 6.0


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def horse_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def softmax(values: list[float]) -> list[float]:
    maximum = max(values)
    weights = [math.exp((value - maximum) / RATING_SCALE) for value in values]
    total = sum(weights)
    return [weight / total for weight in weights]


def reliability(races_rated: int) -> float:
    """Shrink an unproven horse to neutral; reaches 63% after four runs."""
    return 1.0 - math.exp(-races_rated / 4.0)


@dataclass(frozen=True)
class Rating:
    name: str
    rating: float
    races_rated: int

    @property
    def reliability(self) -> float:
        return reliability(self.races_rated)

    @property
    def effective_rating(self) -> float:
        return NEUTRAL_RATING + self.reliability * (self.rating - NEUTRAL_RATING)


def _race_rows(store: RacingStore, as_of_date: str) -> Iterable[list[dict[str, object]]]:
    rows = store.connection.execute(
        """SELECT rr.race_date, rr.track_slug, rr.race_number, rr.runner_number,
                  rr.runner_name, rr.finish_position, rr.beaten_lengths
             FROM runner_results rr
            WHERE rr.race_date < ? AND rr.result_status = 'finished'
              AND rr.finish_position IS NOT NULL AND rr.beaten_lengths IS NOT NULL
            ORDER BY rr.race_date, rr.track_slug, rr.race_number, rr.runner_number""",
        (as_of_date,),
    ).fetchall()
    grouped: dict[tuple[str, str, int], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(row["race_date"], row["track_slug"], row["race_number"])].append(dict(row))
    return grouped.values()


def build_ratings(store: RacingStore, as_of_date: str, model_version: str = MODEL_VERSION) -> dict[str, Rating]:
    """Replay all prior result races and store an as-of rating snapshot."""
    ratings: dict[str, float] = defaultdict(lambda: NEUTRAL_RATING)
    names: dict[str, str] = {}
    race_counts: dict[str, int] = defaultdict(int)

    for runners in _race_rows(store, as_of_date):
        if len(runners) < 2:
            continue
        keys = [horse_key(str(row["runner_name"])) for row in runners]
        for key, row in zip(keys, runners):
            names[key] = str(row["runner_name"])
        expected = softmax([ratings[key] for key in keys])
        raw_actual = [math.exp(-float(row["beaten_lengths"]) / LENGTH_DECAY) for row in runners]
        actual_total = sum(raw_actual)
        actual = [value / actual_total for value in raw_actual]
        field_size = len(runners)
        for key, actual_share, expected_share in zip(keys, actual, expected):
            ratings[key] += UPDATE_K * field_size * (actual_share - expected_share)
            race_counts[key] += 1

    result = {
        key: Rating(name=names[key], rating=value, races_rated=race_counts[key])
        for key, value in ratings.items()
    }
    now = utc_now()
    for key, value in result.items():
        detail = {
            "method": "relative beaten-length update",
            "length_decay": LENGTH_DECAY,
            "update_k": UPDATE_K,
            "sectional_adjustment": "not yet applied",
            "track_par_adjustment": "not yet applied",
        }
        store.connection.execute(
            """INSERT INTO rating_snapshots (model_version, as_of_date, horse_key, horse_name, rating, races_rated, reliability, detail_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(model_version, as_of_date, horse_key) DO UPDATE SET
                 horse_name=excluded.horse_name, rating=excluded.rating, races_rated=excluded.races_rated,
                 reliability=excluded.reliability, detail_json=excluded.detail_json, created_at=excluded.created_at""",
            (model_version, as_of_date, key, value.name, value.rating, value.races_rated, value.reliability, json.dumps(detail, sort_keys=True), now),
        )
    store.connection.commit()
    return result
