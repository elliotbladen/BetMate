"""Step 2: walk-forward, condition-specific targets for Expected Tempo.

The target is a description of the completed race, not a horse adjustment.
Physical sectional pars use only earlier race dates and progressively shrink
track/going/rail cells toward broader source-and-distance history. Race grade
and field size remain prediction features so their tempo signal is not
normalised away.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .expected_tempo_dataset import DATASET_VERSION as STEP1_VERSION
from .expected_tempo_dataset import PACE_VERSION, _going_bucket
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "expected-tempo-targets-v2.0-walk-forward"
MIN_BROAD = 10
MIN_CELL = 5
SHRINKAGE_K = 20.0


def rail_bucket(value: str | None) -> str | None:
    text = (value or "").strip().lower()
    if not text:
        return None
    if "true" in text and not re.search(r"\d+(?:\.\d+)?\s*m", text):
        return "true"
    metres = [float(item) for item in re.findall(r"(?:\+|out\s*)?(\d+(?:\.\d+)?)\s*m", text)]
    if not metres:
        return "other"
    outward = max(metres)
    if outward <= 3:
        return "out_1_3m"
    if outward <= 6:
        return "out_4_6m"
    return "out_7m_plus"


def robust_location_scale(values: list[float]) -> tuple[float, float]:
    median = statistics.median(values)
    mad = statistics.median(abs(value - median) for value in values)
    return median, max(0.10, 1.4826 * mad)


def fast_score(seconds: float, location: float, scale: float) -> float:
    return max(-4.0, min(4.0, (location - seconds) / scale))


def four_way_label(early: float, middle: float, late: float) -> str:
    if early >= 0.75 and late <= -0.75:
        return "very_fast_or_collapse"
    if early >= 1.25 or (early >= 0.75 and middle >= 0.50):
        return "very_fast_or_collapse"
    if early >= 0.50:
        return "fast"
    if early <= -0.50:
        return "slow"
    return "even"


def detailed_label(early: float, middle: float, late: float) -> str:
    if early >= 0.75 and late <= -0.75:
        return "pace_collapse"
    if early <= -0.75 and late >= 0.75:
        return "sprint_home"
    if early >= 0.50 and middle >= 0.35 and late >= 0:
        return "sustained_high_pressure"
    if early >= 1.25:
        return "very_fast_early"
    if early >= 0.50:
        return "fast_early"
    if early <= -1.25:
        return "very_slow_early"
    if early <= -0.50:
        return "slow_early"
    return "even"


def _blend_par(levels: list[tuple[str, list[float]]]) -> tuple[float, float, str, int, dict[str, int]] | None:
    """Blend broad-to-specific robust pars with partial pooling."""
    eligible = [(name, values) for name, values in levels if len(values) >= MIN_CELL]
    # Prefer the most specific adequately populated cell. Earlier/broader
    # levels are true fallbacks, not a permanent pull toward Good-track data.
    broad = next(((name, values) for name, values in reversed(eligible) if len(values) >= MIN_BROAD), None)
    if broad is None:
        return None
    start = eligible.index(broad)
    location, scale = robust_location_scale(broad[1])
    used = broad[0]
    counts = {name: len(values) for name, values in levels}
    for name, values in eligible[start + 1 :]:
        local_location, local_scale = robust_location_scale(values)
        weight = len(values) / (len(values) + SHRINKAGE_K)
        location = weight * local_location + (1 - weight) * location
        scale = max(0.10, weight * local_scale + (1 - weight) * scale)
        used = name
    return location, scale, used, len(dict(levels)[used]), counts


def _history_levels(history: dict[tuple, list[dict[str, Any]]], row: dict[str, Any], phase: str):
    source, track, distance, going, rail, phase_profile = (
        row["source"], row["track_slug"], row["distance_metres"], row["going"], row["rail_bucket"]
        , row["phase_profile"]
    )
    keys = [
        ("source_phase_profile", ("phase", source, phase_profile)),
        ("source_distance", (source, distance)),
        ("track_distance", (source, track, distance)),
        # Once a going-specific level is available, no later non-going cell is
        # allowed to override it. This is essential for Soft/Heavy targets.
        ("source_phase_profile_going", ("phase_going", source, phase_profile, going)),
        ("source_distance_going", (source, distance, going)),
        ("track_phase_profile_going", ("track_phase_going", source, track, phase_profile, going)),
        ("track_distance_going", (source, track, distance, going)),
        ("track_distance_going_rail", (source, track, distance, going, rail)),
    ]
    return [(name, [item[phase] for item in history[key]]) for name, key in keys]


def _add_history(history: dict[tuple, list[dict[str, Any]]], row: dict[str, Any]) -> None:
    source, track, distance, going, rail, phase_profile = (
        row["source"], row["track_slug"], row["distance_metres"], row["going"], row["rail_bucket"]
        , row["phase_profile"]
    )
    for key in (
        ("phase", source, phase_profile),
        ("phase_going", source, phase_profile, going),
        ("track_phase_going", source, track, phase_profile, going),
        (source, distance),
        (source, distance, going),
        (source, track, distance),
        (source, track, distance, going),
        (source, track, distance, going, rail),
    ):
        history[key].append(row)


def source_rows(store: RacingStore) -> list[dict[str, Any]]:
    rows = store.connection.execute(
        """SELECT r.race_id,r.source,r.race_date,r.state,r.track_slug,r.race_number,
                  r.distance_metres,r.race_class,p.early_seconds,p.middle_seconds,p.late_seconds,
                  p.coverage,p.sectional_runners,p.finished_runners,
                  c.class_family,c.group_grade,
                  rr.track_condition,rr.rail_position
             FROM v2_clean_races r
             JOIN v2_race_pace_shapes p ON p.race_id=r.race_id AND p.version=?
             LEFT JOIN race_classifications c
               ON c.source=r.source AND c.race_date=r.race_date
              AND c.track_slug=r.track_slug AND c.race_number=r.race_number
             LEFT JOIN race_results rr
               ON rr.source=r.source AND rr.race_date=r.race_date
              AND rr.track_slug=r.track_slug AND rr.race_number=r.race_number
            WHERE p.early_seconds IS NOT NULL AND p.middle_seconds IS NOT NULL AND p.late_seconds IS NOT NULL
            ORDER BY r.race_date,r.track_slug,r.race_number""",
        (PACE_VERSION,),
    ).fetchall()
    return [{
        **dict(row),
        "going": _going_bucket(row["track_condition"]),
        "rail_bucket": rail_bucket(row["rail_position"]),
        # Both authorised sources use 400m early/middle/late phases from 1200m
        # upward. NSW 1000m and 1100m races have shorter early phases and must
        # retain exact-distance semantics.
        "phase_profile": "standard_3x400" if row["distance_metres"] >= 1200 else f"distance_{row['distance_metres']}",
    } for row in rows]


def build_targets(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    history: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    output: list[dict[str, Any]] = []
    unscored = Counter()
    # Score a whole date before adding it. This is stricter than race-order
    # scoring and prevents accidental same-meeting information in offline targets.
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[row["race_date"]].append(row)
    for race_date in sorted(by_date):
        pending = by_date[race_date]
        for row in pending:
            pars = {}
            for phase in ("early_seconds", "middle_seconds", "late_seconds"):
                result = _blend_par(_history_levels(history, row, phase))
                if result is None:
                    unscored["insufficient_prior_comparable_races"] += 1
                    pars = {}
                    break
                pars[phase] = result
            if not pars:
                continue
            scores = {
                phase.replace("_seconds", ""): fast_score(row[phase], pars[phase][0], pars[phase][1])
                for phase in pars
            }
            output.append({
                "target_version": TARGET_VERSION,
                "race_id": row["race_id"],
                "race_date": row["race_date"],
                "source": row["source"],
                "state": row["state"],
                "track_slug": row["track_slug"],
                "race_number": row["race_number"],
                "distance_metres": row["distance_metres"],
                "going_bucket": row["going"],
                "rail_bucket": row["rail_bucket"],
                "class_family": row["class_family"],
                "group_grade": row["group_grade"],
                "field_size": row["finished_runners"],
                "sectional_coverage": row["coverage"],
                "early_score": scores["early"],
                "middle_score": scores["middle"],
                "late_score": scores["late"],
                "pace_label_4way": four_way_label(scores["early"], scores["middle"], scores["late"]),
                "pace_label_detailed": detailed_label(scores["early"], scores["middle"], scores["late"]),
                "par_early_seconds": pars["early_seconds"][0],
                "par_middle_seconds": pars["middle_seconds"][0],
                "par_late_seconds": pars["late_seconds"][0],
                "par_early_scale": pars["early_seconds"][1],
                "par_middle_scale": pars["middle_seconds"][1],
                "par_late_scale": pars["late_seconds"][1],
                "par_most_specific_level": pars["early_seconds"][2],
                "par_most_specific_sample": pars["early_seconds"][3],
                "par_level_counts_json": json.dumps(pars["early_seconds"][4], sort_keys=True),
                "information_cutoff_exclusive": race_date,
            })
        for row in pending:
            _add_history(history, row)
    report = {"input_rows": len(rows), "scored_rows": len(output), "unscored": dict(unscored)}
    return output, report


def _group_rates(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        key = str(row[field] if row[field] is not None else "missing")
        groups[key].append(row["pace_label_4way"])
    result = {}
    for key, labels in sorted(groups.items()):
        counts = Counter(labels)
        result[key] = {"n": len(labels), "rates": {label: count / len(labels) for label, count in sorted(counts.items())}}
    return result


def write_artifacts(rows: list[dict[str, Any]], report: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "expected_tempo_step2_targets.csv"
    manifest_path = output_dir / "expected_tempo_step2_manifest.json"
    columns = list(rows[0]) if rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns); writer.writeheader(); writer.writerows(rows)
    manifest = {
        "target_version": TARGET_VERSION,
        "input_dataset_version": STEP1_VERSION,
        "source_pace_version": PACE_VERSION,
        **report,
        "date_min": min((row["race_date"] for row in rows), default=None),
        "date_max": max((row["race_date"] for row in rows), default=None),
        "labels_4way": dict(Counter(row["pace_label_4way"] for row in rows)),
        "labels_detailed": dict(Counter(row["pace_label_detailed"] for row in rows)),
        "par_levels": dict(Counter(row["par_most_specific_level"] for row in rows)),
        "descriptive_rates_only": {
            "going": _group_rates(rows, "going_bucket"),
            "group_grade": _group_rates(rows, "group_grade"),
            "track": _group_rates(rows, "track_slug"),
        },
        "method": {
            "chronology": "all races on a date scored before that date enters history",
            "physical_par_factors": ["source", "sectional phase profile", "track", "exact distance", "going", "rail bucket"],
            "prediction_factors_not_normalised_away": ["race grade", "class family", "field size"],
            "pooling": {"minimum_broad": MIN_BROAD, "minimum_cell": MIN_CELL, "shrinkage_k": SHRINKAGE_K},
            "scores": "positive means faster than prior-only physical par; clipped to [-4,4]",
        },
        "production_effect": "none; research target layer only",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"csv": str(csv_path), "manifest": str(manifest_path), **manifest}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "expected_tempo")
    args = parser.parse_args()
    store = RacingStore(args.database)
    try:
        rows, report = build_targets(source_rows(store))
    finally:
        store.close()
    print(json.dumps(write_artifacts(rows, report, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
