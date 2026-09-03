"""Build the Step 1 race-level dataset for the standalone Expected Tempo Engine.

The builder is deliberately research-only.  ``feature_*`` values describe the
race environment and field using information available no later than that race;
``target_*`` values are post-race sectional outcomes and must never be supplied
to a live prediction.  Horse ratings and prices are not read or changed.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .horse_identity import identity_key
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
DATASET_VERSION = "expected-tempo-step1-v1"
PACE_VERSION = "pace-shape-v2.1-pit-shadow"
EXCLUDED_STATUSES = {"scratched", "non_starter", "abandoned"}


def _going_bucket(value: str | None) -> str | None:
    text = (value or "").strip().lower()
    for bucket in ("firm", "good", "soft", "heavy", "synthetic"):
        if bucket in text:
            return bucket
    return None


def _as_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _starter_rows(store: RacingStore, race_id: str) -> list[Any]:
    return store.connection.execute(
        """SELECT c.*, r.barrier, r.jockey, r.trainer
             FROM v2_clean_runner_results c
             LEFT JOIN v2_clean_races race ON race.race_id=c.race_id
             LEFT JOIN runner_results r
               ON r.source=race.source AND r.race_date=race.race_date
              AND r.track_slug=race.track_slug AND r.race_number=race.race_number
              AND r.runner_number=c.runner_number
            WHERE c.race_id=? AND c.result_status NOT IN ('scratched','non_starter','abandoned')
            ORDER BY c.runner_number""",
        (race_id,),
    ).fetchall()


def _prior_runner_profiles(store: RacingStore) -> dict[str, list[dict[str, Any]]]:
    """Return chronological, post-race observations keyed by canonical horse.

    These observations are consumed only when their race date is strictly
    earlier than the row being built.  Same-day and future leakage is excluded.
    """
    profiles: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows = store.connection.execute(
        """SELECT p.horse_key,p.horse_name,r.race_date,p.early_relative,p.detail_json
             FROM v2_runner_pace_ratings p
             JOIN v2_clean_races r ON r.race_id=p.race_id
            WHERE p.version=? ORDER BY r.race_date,p.race_id""",
        (PACE_VERSION,),
    ).fetchall()
    for row in rows:
        detail = json.loads(row["detail_json"] or "{}")
        key = row["horse_key"] or identity_key(row["horse_name"])
        profiles[key].append(
            {
                "race_date": row["race_date"],
                "early_relative": row["early_relative"],
                "position_800": detail.get("position_800"),
            }
        )
    return profiles


def build_rows(store: RacingStore) -> list[dict[str, Any]]:
    profiles = _prior_runner_profiles(store)
    races = store.connection.execute(
        """SELECT r.*,p.sectional_runners,p.finished_runners,p.coverage,
                  p.early_score,p.middle_score,p.late_score,p.pace_label,p.confidence,
                  c.race_type,c.group_grade,c.benchmark,c.class_number,
                  c.age_condition,c.sex_condition,c.raw_class_text
             FROM v2_clean_races r
             JOIN v2_race_pace_shapes p ON p.race_id=r.race_id AND p.version=?
             LEFT JOIN race_classifications c
               ON c.source=r.source AND c.race_date=r.race_date
              AND c.track_slug=r.track_slug AND c.race_number=r.race_number
            ORDER BY r.race_date,r.track_slug,r.race_number""",
        (PACE_VERSION,),
    ).fetchall()
    output: list[dict[str, Any]] = []
    for race in races:
        official = store.connection.execute(
            """SELECT track_condition,rail_position,scheduled_start_at
                 FROM race_results WHERE source=? AND race_date=? AND track_slug=? AND race_number=?""",
            (race["source"], race["race_date"], race["track_slug"], race["race_number"]),
        ).fetchone()
        weather = store.connection.execute(
            """SELECT * FROM race_weather
                WHERE race_date=? AND track_slug=? AND race_number=?
                ORDER BY CASE WHEN source=? THEN 0 ELSE 1 END LIMIT 1""",
            (race["race_date"], race["track_slug"], race["race_number"], race["source"]),
        ).fetchone()
        starters = _starter_rows(store, race["race_id"])
        barriers = [float(row["barrier"]) for row in starters if row["barrier"] is not None]
        runner_early: list[float] = []
        runner_positions: list[float] = []
        profiled = 0
        likely_leaders = 0
        on_pace = 0
        for runner in starters:
            key = runner["horse_key"] or identity_key(runner["horse_name"])
            prior = [item for item in profiles.get(key, []) if item["race_date"] < race["race_date"]]
            if not prior:
                continue
            profiled += 1
            early = [float(item["early_relative"]) for item in prior[-6:] if item["early_relative"] is not None]
            positions = [float(item["position_800"]) for item in prior[-6:] if item["position_800"] is not None]
            median_early = _median(early)
            median_position = _median(positions)
            if median_early is not None:
                runner_early.append(median_early)
            if median_position is not None:
                runner_positions.append(median_position)
                likely_leaders += int(median_position <= 2.0)
                on_pace += int(median_position <= 4.0)
        start_at = _as_utc(official["scheduled_start_at"] if official else None)
        observed_at = _as_utc(weather["observed_at"] if weather else None)
        weather_safe = bool(start_at and observed_at and observed_at <= start_at)
        row = {
            "dataset_version": DATASET_VERSION,
            "race_id": race["race_id"],
            "race_date": race["race_date"],
            "source": race["source"],
            "state": race["state"],
            "track_slug": race["track_slug"],
            "race_number": race["race_number"],
            "scheduled_start_at": official["scheduled_start_at"] if official else None,
            "feature_distance_metres": race["distance_metres"],
            "feature_track_condition_raw": official["track_condition"] if official else None,
            "feature_going_bucket": _going_bucket(official["track_condition"] if official else None),
            "feature_rail_position": official["rail_position"] if official else None,
            "feature_race_class_raw": race["race_class"],
            "feature_race_type": race["race_type"],
            "feature_class_family": race["class_family"],
            "feature_group_grade": race["group_grade"],
            "feature_benchmark": race["benchmark"],
            "feature_class_number": race["class_number"],
            "feature_age_condition": race["age_condition"],
            "feature_sex_condition": race["sex_condition"],
            "feature_field_size": len(starters),
            "feature_barrier_coverage": len(barriers) / len(starters) if starters else 0.0,
            "feature_barrier_mean": sum(barriers) / len(barriers) if barriers else None,
            "feature_barrier_spread": max(barriers) - min(barriers) if barriers else None,
            "feature_profiled_runner_count": profiled,
            "feature_profiled_runner_coverage": profiled / len(starters) if starters else 0.0,
            "feature_likely_leader_count": likely_leaders,
            "feature_on_pace_count": on_pace,
            "feature_field_median_prior_early_relative": _median(runner_early),
            "feature_field_median_prior_position_800": _median(runner_positions),
            "feature_temperature_c": weather["temperature_c"] if weather else None,
            "feature_humidity_pct": weather["humidity_pct"] if weather else None,
            "feature_precipitation_mm": weather["precipitation_mm"] if weather else None,
            "feature_wind_direction_deg": weather["wind_direction_deg"] if weather else None,
            "feature_wind_speed_kmh": weather["wind_speed_kmh"] if weather else None,
            "feature_weather_observed_at": weather["observed_at"] if weather else None,
            "feature_weather_point_in_time_safe": int(weather_safe),
            "feature_headwind_component_kmh": None,
            "feature_crosswind_component_kmh": None,
            "feature_course_geometry_available": 0,
            "feature_rail_timestamp_verified": 0,
            "feature_condition_timestamp_verified": 0,
            "target_sectional_runners": race["sectional_runners"],
            "target_finished_runners": race["finished_runners"],
            "target_sectional_coverage": race["coverage"],
            "target_early_score": race["early_score"],
            "target_middle_score": race["middle_score"],
            "target_late_score": race["late_score"],
            "target_pace_label": race["pace_label"],
            "target_label_confidence": race["confidence"],
        }
        output.append(row)
    return output


def _coverage(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    present = sum(row.get(field) is not None and row.get(field) != "" for row in rows)
    return {"present": present, "total": len(rows), "rate": present / len(rows) if rows else 0.0}


def write_artifacts(rows: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "expected_tempo_step1.csv"
    schema_path = output_dir / "expected_tempo_step1_schema.json"
    manifest_path = output_dir / "expected_tempo_step1_manifest.json"
    columns = list(rows[0]) if rows else []
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    schema = {
        "dataset_version": DATASET_VERSION,
        "pace_target_version": PACE_VERSION,
        "unit": "one row per completed race",
        "feature_prefix": "pre-race input; timestamp-quality flags must be respected",
        "target_prefix": "post-race outcome; prohibited from prediction inputs",
        "field_pressure_policy": "runner pace observations from strictly earlier race dates, last six available",
        "likely_leader_definition": "median prior 800m position <= 2",
        "on_pace_definition": "median prior 800m position <= 4",
        "null_policy": "missing evidence remains null; no synthetic rail, condition, wind geometry or sectional value",
        "columns": columns,
    }
    schema_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    important = [
        "feature_going_bucket", "feature_rail_position", "feature_group_grade",
        "feature_profiled_runner_coverage", "feature_temperature_c", "feature_wind_speed_kmh",
        "target_early_score", "target_middle_score", "target_late_score", "target_pace_label",
    ]
    manifest = {
        "dataset_version": DATASET_VERSION,
        "pace_target_version": PACE_VERSION,
        "rows": len(rows),
        "date_min": min((row["race_date"] for row in rows), default=None),
        "date_max": max((row["race_date"] for row in rows), default=None),
        "states": dict(Counter(row["state"] for row in rows)),
        "going": dict(Counter(row["feature_going_bucket"] or "missing" for row in rows)),
        "pace_labels": dict(Counter(row["target_pace_label"] for row in rows)),
        "coverage": {field: _coverage(rows, field) for field in important},
        "field_profile_summary": {
            "mean_profiled_runner_coverage": (
                sum(row["feature_profiled_runner_coverage"] for row in rows) / len(rows) if rows else 0.0
            ),
            "races_with_any_profiled_runner": sum(
                row.get("feature_profiled_runner_count", 0) > 0 for row in rows
            ),
            "mean_likely_leader_count": (
                sum(row.get("feature_likely_leader_count", 0) for row in rows) / len(rows) if rows else 0.0
            ),
            "mean_on_pace_count": (
                sum(row.get("feature_on_pace_count", 0) for row in rows) / len(rows) if rows else 0.0
            ),
        },
        "point_in_time": {
            "runner_history": "strictly prior race dates only",
            "weather_safe_rows": sum(row["feature_weather_point_in_time_safe"] for row in rows),
            "rail_and_condition": "historical official values available, timestamp not verified; flags remain 0",
        },
        "production_effect": "none; standalone research dataset only",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"csv": str(csv_path), "schema": str(schema_path), "manifest": str(manifest_path), **manifest}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "expected_tempo")
    args = parser.parse_args()
    store = RacingStore(args.database)
    try:
        report = write_artifacts(build_rows(store), args.output_dir)
    finally:
        store.close()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
