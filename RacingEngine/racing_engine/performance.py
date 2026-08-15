"""Auditable V1 historical performance and horse-state pipeline.

This module is intentionally a transparent research baseline.  It does not
claim to model class, weight, barrier, trip or market information yet.  Its
job is to turn authorised result history into evidence we can inspect, then
maintain a conservative current horse state with explicit uncertainty.
"""
from __future__ import annotations

import json
import math
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone

from .ratings import horse_key, softmax
from .storage import RacingStore


MODEL_VERSION = "performance-par-v1.0"
NEUTRAL = 100.0
SECONDS_PER_LENGTH = 0.17
RECENCY_HALF_LIFE_DAYS = 180.0


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def going_bucket(value: str | None) -> str:
    text = (value or "unknown").lower()
    for bucket in ("heavy", "soft", "good", "firm", "synthetic"):
        if bucket in text:
            return bucket
    return "unknown"


def distance_bucket(distance_metres: int) -> int:
    """Keep exact common distances; round unusual layouts to the nearest 10m."""
    return int(round(distance_metres / 10.0) * 10)


def parse_position(value: object) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group()) if match else None


@dataclass(frozen=True)
class Par:
    track_slug: str
    distance_metres: int
    going: str
    time_seconds: float
    sample_size: int


def build_pars(store: RacingStore, as_of_date: str, *, min_sample: int = 5,
               model_version: str = MODEL_VERSION) -> dict[tuple[str, int, str], Par]:
    """Build robust, as-of-only time pars from authorised past result races."""
    rows = store.connection.execute(
        """SELECT track_slug, distance_metres, track_condition, official_time_seconds
             FROM race_results
            WHERE race_date < ? AND official_time_seconds IS NOT NULL
              AND distance_metres IS NOT NULL AND distance_metres > 0""",
        (as_of_date,),
    ).fetchall()
    grouped: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for row in rows:
        key = (row["track_slug"], distance_bucket(row["distance_metres"]), going_bucket(row["track_condition"]))
        grouped[key].append(float(row["official_time_seconds"]))
    now = utc_now()
    result: dict[tuple[str, int, str], Par] = {}
    for key, values in grouped.items():
        if len(values) < min_sample:
            continue
        # Median is resistant to a pace collapse, timing anomaly or extreme day.
        par = Par(*key, time_seconds=statistics.median(values), sample_size=len(values))
        result[key] = par
        detail = {"statistic": "median", "raw_sample_size": len(values), "source_cutoff": as_of_date,
                  "rail_adjustment": "not yet applied", "class_adjustment": "not yet applied"}
        store.connection.execute(
            """INSERT INTO track_pars (model_version, as_of_date, track_slug, distance_metres, going_bucket, sample_size, par_time_seconds, method, detail_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(model_version, as_of_date, track_slug, distance_metres, going_bucket) DO UPDATE SET
                 sample_size=excluded.sample_size, par_time_seconds=excluded.par_time_seconds,
                 detail_json=excluded.detail_json, created_at=excluded.created_at""",
            (model_version, as_of_date, par.track_slug, par.distance_metres, par.going, par.sample_size,
             par.time_seconds, "median-authorised-history-v1", json.dumps(detail, sort_keys=True), now),
        )
    store.connection.commit()
    return result


def _last400_components(store: RacingStore, source: str, race_date: str, track_slug: str,
                        race_number: int) -> dict[int, float]:
    rows = store.connection.execute(
        """SELECT runner_number, section_seconds FROM runner_sectionals
             WHERE source = ? AND race_date = ? AND track_slug = ? AND race_number = ?
               AND marker_metres = 0 AND section_seconds IS NOT NULL""",
        (source, race_date, track_slug, race_number),
    ).fetchall()
    if len(rows) < 3:
        return {}
    median = statistics.median(float(row["section_seconds"]) for row in rows)
    # A late split is useful evidence, but it is deliberately capped and small
    # until pace/trip adjustment is implemented.
    return {int(row["runner_number"]): max(-2.0, min(2.0, (median - float(row["section_seconds"])) / SECONDS_PER_LENGTH * 0.20)) for row in rows}


def build_performances(store: RacingStore, as_of_date: str, *, min_par_sample: int = 5,
                       model_version: str = MODEL_VERSION) -> int:
    """Store one transparent time/margin/sectional performance per finished run."""
    pars = build_pars(store, as_of_date, min_sample=min_par_sample, model_version=model_version)
    races = store.connection.execute(
        """SELECT source, race_date, track_slug, race_number, distance_metres,
                  track_condition, official_time_seconds
             FROM race_results
            WHERE race_date < ? AND distance_metres IS NOT NULL
              AND official_time_seconds IS NOT NULL
            ORDER BY race_date, track_slug, race_number""",
        (as_of_date,),
    ).fetchall()
    inserted = 0
    now = utc_now()
    for race in races:
        key = (race["track_slug"], distance_bucket(race["distance_metres"]), going_bucket(race["track_condition"]))
        par = pars.get(key)
        if par is None:
            continue
        runners = store.connection.execute(
            """SELECT runner_number, runner_name, finish_position, beaten_lengths,
                      finish_time_seconds
                 FROM runner_results
                WHERE source = ? AND race_date = ? AND track_slug = ? AND race_number = ?
                  AND result_status = 'finished' AND finish_position IS NOT NULL
                ORDER BY runner_number""",
            (race["source"], race["race_date"], race["track_slug"], race["race_number"]),
        ).fetchall()
        sectional = _last400_components(store, race["source"], race["race_date"], race["track_slug"], race["race_number"])
        for runner in runners:
            finish_time = runner["finish_time_seconds"]
            if finish_time is not None:
                time_component = (par.time_seconds - float(finish_time)) / SECONDS_PER_LENGTH
                margin_component = 0.0
            elif runner["beaten_lengths"] is not None:
                # NSW V1 result rows have official winner time but not each
                # runner clock.  Use margin once, rather than double-counting.
                time_component = (par.time_seconds - float(race["official_time_seconds"])) / SECONDS_PER_LENGTH
                margin_component = -float(runner["beaten_lengths"])
            else:
                continue
            sectional_component = sectional.get(int(runner["runner_number"]), 0.0)
            confidence = min(0.80, 0.35 + 0.05 * min(par.sample_size, 8) + (0.10 if sectional else 0.0))
            rating = NEUTRAL + time_component + margin_component + sectional_component
            detail = {
                "par_seconds": par.time_seconds, "par_sample_size": par.sample_size,
                "going_bucket": par.going, "seconds_per_length": SECONDS_PER_LENGTH,
                "finish_time_used": finish_time is not None,
                "sectional": "last-400-relative-to-race-median-capped" if sectional else "not available",
                "pace_trip_adjustment": "not yet applied", "weight_class_adjustment": "not yet applied",
            }
            store.connection.execute(
                """INSERT INTO run_performances (model_version, as_of_date, source, race_date, track_slug, race_number, runner_number, horse_key, horse_name, performance_rating, time_component, margin_component, sectional_component, pace_component, confidence, detail_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(model_version, as_of_date, source, race_date, track_slug, race_number, runner_number) DO UPDATE SET
                     performance_rating=excluded.performance_rating, time_component=excluded.time_component,
                     margin_component=excluded.margin_component, sectional_component=excluded.sectional_component,
                     confidence=excluded.confidence, detail_json=excluded.detail_json, created_at=excluded.created_at""",
                (model_version, as_of_date, race["source"], race["race_date"], race["track_slug"], race["race_number"],
                 runner["runner_number"], horse_key(runner["runner_name"]), runner["runner_name"], rating,
                 time_component, margin_component, sectional_component, None, confidence, json.dumps(detail, sort_keys=True), now),
            )
            inserted += 1
    store.connection.commit()
    return inserted


def build_horse_states(store: RacingStore, as_of_date: str, *, model_version: str = MODEL_VERSION) -> int:
    """Convert prior run ratings into conservative current horse states."""
    rows = store.connection.execute(
        """SELECT horse_key, horse_name, race_date, performance_rating, confidence
             FROM run_performances
            WHERE model_version = ? AND as_of_date = ?
            ORDER BY horse_key, race_date""",
        (model_version, as_of_date),
    ).fetchall()
    grouped: dict[str, list] = defaultdict(list)
    for row in rows:
        grouped[row["horse_key"]].append(row)
    cutoff = date.fromisoformat(as_of_date)
    now = utc_now()
    for key, runs in grouped.items():
        weights = []
        values = []
        for run in runs:
            age = max(0, (cutoff - date.fromisoformat(run["race_date"])).days)
            weight = math.exp(-math.log(2) * age / RECENCY_HALF_LIFE_DAYS) * float(run["confidence"])
            weights.append(weight); values.append(float(run["performance_rating"]))
        mean = sum(weight * value for weight, value in zip(weights, values)) / sum(weights)
        reliability = 1.0 - math.exp(-len(runs) / 4.0)
        overall = NEUTRAL + reliability * (mean - NEUTRAL)
        consistency = statistics.pstdev(values) if len(values) > 1 else None
        uncertainty = max(2.0, 12.0 * (1.0 - reliability) + (consistency or 0.0) * 0.5)
        detail = {"recency_half_life_days": RECENCY_HALF_LIFE_DAYS, "shrinkage_target": NEUTRAL,
                  "profile_adjustments": "not yet applied"}
        store.connection.execute(
            """INSERT INTO horse_rating_states (model_version, as_of_date, horse_key, horse_name, overall_rating, peak_rating, consistency, rated_runs, uncertainty, detail_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(model_version, as_of_date, horse_key) DO UPDATE SET
                 horse_name=excluded.horse_name, overall_rating=excluded.overall_rating, peak_rating=excluded.peak_rating,
                 consistency=excluded.consistency, rated_runs=excluded.rated_runs, uncertainty=excluded.uncertainty,
                 detail_json=excluded.detail_json, created_at=excluded.created_at""",
            (model_version, as_of_date, key, runs[-1]["horse_name"], overall, max(values), consistency,
             len(runs), uncertainty, json.dumps(detail, sort_keys=True), now),
        )
    store.connection.commit()
    return len(grouped)


def run_pipeline(store: RacingStore, as_of_date: str, *, min_par_sample: int = 5,
                 model_version: str = MODEL_VERSION) -> dict[str, int]:
    performances = build_performances(store, as_of_date, min_par_sample=min_par_sample, model_version=model_version)
    states = build_horse_states(store, as_of_date, model_version=model_version)
    return {"performances": performances, "horse_states": states}


def main() -> None:
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, help="Exclusive YYYY-MM-DD cutoff")
    parser.add_argument("--min-par-sample", type=int, default=5)
    args = parser.parse_args()
    store = RacingStore(Path(__file__).resolve().parents[1] / "data" / "racing_engine.sqlite")
    try:
        print(json.dumps(run_pipeline(store, args.as_of, min_par_sample=args.min_par_sample), sort_keys=True))
    finally:
        store.close()


if __name__ == "__main__":
    main()
