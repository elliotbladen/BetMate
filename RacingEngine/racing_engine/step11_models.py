"""Step 11 daily-track-variant and carried-weight model candidates."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from .performance import MODEL_VERSION, SECONDS_PER_LENGTH, build_horse_states, run_pipeline, utc_now
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
VARIANT_VERSION = "daily-track-variant-v1.0"
SHRINKAGE_K = 6.0
MIN_RACES = 3
KG_TO_RATING_POINTS = 1.0
VARIANTS = {
    "daily_variant": "performance-par-v1.0+daily-variant-v1.0",
    "carried_weight": "performance-par-v1.0+carried-weight-v1.0",
    "daily_weight": "performance-par-v1.0+daily-variant-v1.0+carried-weight-v1.0",
}


def estimate_daily_variants(store: RacingStore, as_of_date: str,
                            *, base_model: str = MODEL_VERSION) -> dict[tuple[str, str, str], float]:
    pars = {(row["track_slug"], row["distance_metres"], row["going_bucket"]): row["par_time_seconds"]
            for row in store.connection.execute(
                "SELECT * FROM track_pars WHERE model_version=? AND as_of_date=?", (base_model, as_of_date))}
    rows = store.connection.execute(
        """SELECT source,race_date,track_slug,distance_metres,track_condition,official_time_seconds
             FROM race_results WHERE race_date<? AND distance_metres IS NOT NULL AND official_time_seconds IS NOT NULL""",
        (as_of_date,)).fetchall()
    from .performance import distance_bucket, going_bucket
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        par = pars.get((row["track_slug"], distance_bucket(row["distance_metres"]), going_bucket(row["track_condition"])))
        if par is not None:
            grouped[(row["source"], row["race_date"], row["track_slug"])].append(
                (float(par) - float(row["official_time_seconds"])) / SECONDS_PER_LENGTH)
    now = utc_now(); result = {}
    for key, residuals in grouped.items():
        raw = statistics.median(residuals) if residuals else None
        usable = len(residuals) >= MIN_RACES
        factor = len(residuals) / (len(residuals) + SHRINKAGE_K) if usable else 0.0
        shrunk = float(raw) * factor if usable and raw is not None else 0.0
        status = "outlier_review" if usable and abs(shrunk) > 8 else ("ok" if usable else "insufficient_races")
        result[key] = shrunk
        store.connection.execute(
            """INSERT INTO daily_track_variants
               (variant_version,as_of_date,source,race_date,track_slug,raw_variant_lengths,
                shrunk_variant_lengths,races_used,shrinkage_factor,quality_status,detail_json,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(variant_version,as_of_date,source,race_date,track_slug)
               DO UPDATE SET raw_variant_lengths=excluded.raw_variant_lengths,
                 shrunk_variant_lengths=excluded.shrunk_variant_lengths,races_used=excluded.races_used,
                 shrinkage_factor=excluded.shrinkage_factor,quality_status=excluded.quality_status,
                 detail_json=excluded.detail_json,created_at=excluded.created_at""",
            (VARIANT_VERSION, as_of_date, *key, raw, shrunk, len(residuals), factor, status,
             json.dumps({"median_race_residual": True, "minimum_races": MIN_RACES,
                         "shrinkage_k": SHRINKAGE_K, "post_meeting_historical_context_only": True}, sort_keys=True), now))
    store.connection.commit(); return result


def build_step11_variants(store: RacingStore, as_of_date: str, *, min_par_sample: int = 5) -> dict[str, Any]:
    base_counts = run_pipeline(store, as_of_date, min_par_sample=min_par_sample, model_version=MODEL_VERSION)
    daily = estimate_daily_variants(store, as_of_date)
    rows = store.connection.execute(
        """SELECT p.*,rr.weight_carried_kg
             FROM run_performances p JOIN runner_results rr
               USING(source,race_date,track_slug,race_number,runner_number)
            WHERE p.model_version=? AND p.as_of_date=? AND p.race_date<?
            ORDER BY p.race_date,p.track_slug,p.race_number,p.runner_number""",
        (MODEL_VERSION, as_of_date, as_of_date)).fetchall()
    race_weights: dict[tuple[str, str, str, int], list[float]] = defaultdict(list)
    for row in rows:
        if row["weight_carried_kg"] is not None:
            race_weights[(row["source"], row["race_date"], row["track_slug"], row["race_number"])].append(
                float(row["weight_carried_kg"]))
    medians = {key: statistics.median(values) for key, values in race_weights.items()}
    now = utc_now(); summaries = {}
    for name, model_version in VARIANTS.items():
        nonzero_daily = nonzero_weight = missing_weight = 0
        for row in rows:
            meeting_key = (row["source"], row["race_date"], row["track_slug"])
            race_key = (*meeting_key, row["race_number"])
            daily_component = -daily.get(meeting_key, 0.0) if name in ("daily_variant", "daily_weight") else 0.0
            if name in ("carried_weight", "daily_weight") and row["weight_carried_kg"] is not None and race_key in medians:
                weight_component = (float(row["weight_carried_kg"]) - medians[race_key]) * KG_TO_RATING_POINTS
            else:
                weight_component = 0.0
                missing_weight += int(name in ("carried_weight", "daily_weight") and row["weight_carried_kg"] is None)
            nonzero_daily += int(abs(daily_component) > 1e-12); nonzero_weight += int(abs(weight_component) > 1e-12)
            detail = {**json.loads(row["detail_json"]), "base_model": MODEL_VERSION,
                      "base_performance_rating": row["performance_rating"], "daily_variant_version": VARIANT_VERSION,
                      "daily_variant_component": daily_component, "carried_weight_component": weight_component,
                      "race_median_carried_weight_kg": medians.get(race_key),
                      "kg_to_rating_points": KG_TO_RATING_POINTS, "wfa_component": None,
                      "wfa_status": "unavailable: runner age and sex absent from historical result rows"}
            store.connection.execute(
                """INSERT INTO run_performances
                   (model_version,as_of_date,source,race_date,track_slug,race_number,runner_number,horse_key,horse_name,
                    performance_rating,time_component,margin_component,sectional_component,pace_component,confidence,
                    detail_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(model_version,as_of_date,source,race_date,track_slug,race_number,runner_number) DO UPDATE SET
                    horse_key=excluded.horse_key,horse_name=excluded.horse_name,
                    performance_rating=excluded.performance_rating,time_component=excluded.time_component,
                    margin_component=excluded.margin_component,sectional_component=excluded.sectional_component,
                    pace_component=excluded.pace_component,confidence=excluded.confidence,
                    detail_json=excluded.detail_json,created_at=excluded.created_at""",
                (model_version, as_of_date, row["source"], row["race_date"], row["track_slug"], row["race_number"],
                 row["runner_number"], row["horse_key"], row["horse_name"],
                 row["performance_rating"] + daily_component + weight_component, row["time_component"],
                 row["margin_component"], row["sectional_component"], row["pace_component"], row["confidence"],
                 json.dumps(detail, sort_keys=True), now))
        store.connection.commit(); states = build_horse_states(store, as_of_date, model_version=model_version)
        summaries[name] = {"model_version": model_version, "performances": len(rows), "horse_states": states,
                           "nonzero_daily": nonzero_daily, "nonzero_weight": nonzero_weight,
                           "missing_weight": missing_weight}
    return {"as_of_date": as_of_date, "base_counts": base_counts, "variants": summaries,
            "daily_variant_version": VARIANT_VERSION, "kg_to_rating_points": KG_TO_RATING_POINTS,
            "wfa_status": "GATED_MISSING_DATA", "wfa_missing_fields": ["runner_age", "runner_sex"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--as-of", required=True); parser.add_argument("--min-par-sample", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(); store = RacingStore(args.database)
    try: report = build_step11_variants(store, args.as_of, min_par_sample=args.min_par_sample)
    finally: store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output: args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered)
    else: print(rendered, end="")


if __name__ == "__main__":
    main()
