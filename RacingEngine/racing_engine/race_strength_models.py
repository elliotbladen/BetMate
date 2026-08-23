"""Integrate frozen Race Strength components into isolated Horse Ability variants."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .performance import MODEL_VERSION, build_horse_states, run_pipeline, utc_now
from .race_strength import RACE_STRENGTH_VERSION
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
VARIANTS = {
    "identity_only": "performance-par-v1.0+identity-v1.0",
    "class_only": "performance-par-v1.0+race-class-v1.0",
    "field_only": "performance-par-v1.0+race-field-v1.0",
    "combined": "performance-par-v1.0+race-strength-v1.0",
}
RATING_COLUMNS = {"identity_only": None, "class_only": "class_only_rating", "field_only": "field_only_rating",
                  "combined": "combined_rating"}


def adjustment(race_rating: float | None) -> float:
    """One transparent candidate point per Race Strength point from neutral."""
    return float(race_rating) - 100.0 if race_rating is not None else 0.0


def build_variants(store: RacingStore, as_of_date: str, *, min_par_sample: int = 5,
                   base_model: str = MODEL_VERSION) -> dict[str, Any]:
    base_counts = run_pipeline(store, as_of_date, min_par_sample=min_par_sample, model_version=base_model)
    base_rows = store.connection.execute(
        """SELECT p.*,l.horse_id,h.canonical_name,rs.class_only_rating,rs.field_only_rating,rs.combined_rating,
                  rs.class_reliability,rs.field_reliability
             FROM run_performances p
             JOIN runner_horse_links l USING(source,race_date,track_slug,race_number,runner_number)
             JOIN horses h ON h.horse_id=l.horse_id
             LEFT JOIN race_strength_ratings rs
               ON rs.race_strength_version=? AND rs.source=p.source AND rs.race_date=p.race_date
              AND rs.track_slug=p.track_slug AND rs.race_number=p.race_number
            WHERE p.model_version=? AND p.as_of_date=? AND p.race_date<?
            ORDER BY p.race_date,p.track_slug,p.race_number,p.runner_number""",
        (RACE_STRENGTH_VERSION, base_model, as_of_date, as_of_date)).fetchall()
    now = utc_now(); summary = {}
    for variant, model_version in VARIANTS.items():
        rating_column = RATING_COLUMNS[variant]
        adjusted = nonzero = missing_race_strength = 0
        for row in base_rows:
            race_rating = row[rating_column] if rating_column else 100.0
            delta = adjustment(race_rating)
            nonzero += int(abs(delta) > 1e-12)
            missing_race_strength += int(race_rating is None)
            base_detail = json.loads(row["detail_json"])
            detail = {**base_detail, "base_model": base_model, "base_performance_rating": row["performance_rating"],
                      "race_strength_version": RACE_STRENGTH_VERSION, "race_strength_variant": variant,
                      "race_strength_rating": race_rating, "race_strength_adjustment": delta,
                      "race_strength_coefficient": 1.0, "class_reliability": row["class_reliability"],
                      "field_reliability": row["field_reliability"],
                      "weight_weather_trip_adjustments": "not included"}
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
                 row["runner_number"], row["horse_id"], row["canonical_name"], row["performance_rating"] + delta,
                 row["time_component"], row["margin_component"], row["sectional_component"], row["pace_component"],
                 row["confidence"], json.dumps(detail, sort_keys=True), now))
            adjusted += 1
        store.connection.commit()
        states = build_horse_states(store, as_of_date, model_version=model_version)
        summary[variant] = {"model_version": model_version, "performances": adjusted, "horse_states": states,
                            "nonzero_adjustments": nonzero, "missing_race_strength": missing_race_strength}
    return {"as_of_date": as_of_date, "base_model": base_model, "base_counts": base_counts,
            "race_strength_version": RACE_STRENGTH_VERSION, "coefficient": 1.0,
            "race_strength_feedback": "frozen Step 8 values; no recursive candidate feedback",
            "excluded_context": ["weight", "WFA", "weather", "daily_variant", "trip", "stewards", "map"],
            "variants": summary}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--as-of", required=True, help="Exclusive YYYY-MM-DD cutoff")
    parser.add_argument("--min-par-sample", type=int, default=5); parser.add_argument("--output", type=Path)
    args = parser.parse_args(); store = RacingStore(args.database)
    try:
        report = build_variants(store, args.as_of, min_par_sample=args.min_par_sample)
    finally:
        store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
