"""Dan-aligned research layer over the point-in-time v3 run figures.

This is deliberately a separate shadow model.  It applies the published WFA
normalisation, removes the existing runner-level pace allowance from the
achieved figure, and compresses the inflated upper tail with an explicit,
versioned calibration.  It does not change accepted production ratings.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .horse_profiles import DERIVATION_VERSION
from .storage import RacingStore
from .wfa import RULES_SOURCE, standard_weight

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MODEL = "form-first-v3.0"
MODEL_VERSION = "dan-aligned-wfa-v0.1"
RECONSTRUCTED_MODEL_VERSION = "dan-aligned-wfa-v0.2-reconstructed"

# Research calibration, retained as named constants so the result is auditable.
# The published Dan scale is broad around 100 but substantially flatter in the
# elite tail; this first pass targets the known Via/Prognosis/Caulfield examples.
ELITE_KNEE = 106.0
ELITE_TAIL_SLOPE = 0.55
WFA_POINTS_PER_KG = 0.65
WFA_COMPONENT_CAP = 4.5


def calibrate_upper_tail(value: float) -> float:
    if value <= ELITE_KNEE:
        return value
    return ELITE_KNEE + (value - ELITE_KNEE) * ELITE_TAIL_SLOPE


def _wfa_reference(row: Any) -> tuple[float | None, str | None, str | None]:
    if row["racing_age"] is None or not row["sex"] or row["distance_metres"] is None:
        return None, None, None
    detail = json.loads(row["profile_detail_json"] or "{}")
    ar170 = bool(detail.get("ar170_eligible"))
    ref = standard_weight(row["race_date"], int(row["distance_metres"]),
                          int(row["racing_age"]), row["sex"],
                          northern_sired_jan_jul_foal=ar170)
    return ref, row["age_method"], row["profile_source"]


def schema(store: RacingStore) -> None:
    store.connection.execute("""
    CREATE TABLE IF NOT EXISTS dan_aligned_run_performances (
      model_version TEXT NOT NULL, source_model TEXT NOT NULL,
      race_id TEXT NOT NULL, runner_number INTEGER NOT NULL,
      horse_key TEXT NOT NULL, horse_name TEXT NOT NULL,
      performance_rating REAL NOT NULL, source_rating REAL NOT NULL,
      wfa_rating REAL NOT NULL, wfa_component REAL NOT NULL,
      pace_removed REAL NOT NULL, carried_kg REAL, wfa_kg REAL,
      confidence REAL NOT NULL, detail_json TEXT NOT NULL,
      PRIMARY KEY (model_version, race_id, runner_number)
    )""")
    store.connection.execute(
        "CREATE INDEX IF NOT EXISTS ix_dan_aligned_horse ON dan_aligned_run_performances(model_version, horse_key)")
    store.connection.commit()


def build(store: RacingStore, source_model: str = SOURCE_MODEL) -> dict[str, Any]:
    schema(store)
    store.connection.execute("DELETE FROM dan_aligned_run_performances WHERE model_version=?", (MODEL_VERSION,))
    rows = store.connection.execute(
        """SELECT p.*, r.source, r.race_date, r.track_slug, r.race_number,
                  rr.weight_carried_kg, rr.finish_position, race.distance_metres,
                  dp.racing_age, dp.sex, dp.age_method, dp.profile_source,
                  dp.detail_json AS profile_detail_json
             FROM v3_run_performances p
             JOIN v2_clean_races r ON r.race_id=p.race_id
             JOIN v2_clean_runner_results rr
               ON rr.race_id=p.race_id AND rr.runner_number=p.runner_number
             JOIN race_results race
               ON race.source=r.source AND race.race_date=r.race_date
              AND race.track_slug=r.track_slug AND race.race_number=r.race_number
             LEFT JOIN runner_derived_profiles dp
               ON dp.derivation_version=? AND dp.source=r.source
              AND dp.race_date=r.race_date AND dp.track_slug=r.track_slug
              AND dp.race_number=r.race_number AND dp.runner_number=p.runner_number
            WHERE p.model_version=?
            ORDER BY r.race_date, r.track_slug, r.race_number, p.runner_number""",
        (DERIVATION_VERSION, source_model)).fetchall()
    written = wfa_adjusted = pace_removed_count = 0
    for row in rows:
        detail = json.loads(row["detail_json"] or "{}")
        # v3 stores the applied runner pace term as a table column.  The detail
        # JSON contains the race-level pace note, so do not silently treat a
        # missing JSON key as proof that no runner adjustment was applied.
        pace = float(row["pace_component"] or 0.0)
        base = float(row["performance_rating"]) - pace
        if abs(pace) > 1e-9:
            pace_removed_count += 1
        ref, age_method, profile_source = _wfa_reference(row)
        carried = float(row["weight_carried_kg"]) if row["weight_carried_kg"] is not None else None
        component = 0.0
        if ref is not None and carried is not None:
            component = max(-WFA_COMPONENT_CAP,
                            min(WFA_COMPONENT_CAP, (carried - ref) * WFA_POINTS_PER_KG))
            wfa_adjusted += 1
        wfa_rating = base + component
        final = calibrate_upper_tail(wfa_rating)
        confidence = float(row["confidence"])
        if ref is None:
            confidence *= 0.92
        confidence = min(0.95, confidence)
        out_detail = {
            "method": "Dan-aligned WFA shadow v0.1",
            "source_model": source_model,
            "pace_runner_adjustment_removed": round(pace, 4),
            "wfa_rules_source": RULES_SOURCE,
            "wfa_age_method": age_method,
            "wfa_profile_source": profile_source,
            "elite_calibration": {"knee": ELITE_KNEE, "tail_slope": ELITE_TAIL_SLOPE},
            "wfa_points_per_kg": WFA_POINTS_PER_KG,
            "wfa_component_cap": WFA_COMPONENT_CAP,
            "wfa_coverage": ref is not None,
        }
        store.connection.execute(
            """INSERT INTO dan_aligned_run_performances VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (MODEL_VERSION, source_model, row["race_id"], int(row["runner_number"]),
             row["horse_key"], row["horse_name"], final, float(row["performance_rating"]),
             wfa_rating, component, pace, carried, ref, confidence,
             json.dumps(out_detail, sort_keys=True)))
        written += 1
    store.connection.commit()
    return {"model_version": MODEL_VERSION, "source_model": source_model,
            "performances": written, "wfa_adjusted": wfa_adjusted,
            "wfa_coverage": wfa_adjusted / written if written else 0.0,
            "pace_removed": pace_removed_count,
            "elite_knee": ELITE_KNEE, "elite_tail_slope": ELITE_TAIL_SLOPE,
            "status": "research_shadow"}


def build_reconstructed(store: RacingStore, review_database: Path,
                        source_model: str = SOURCE_MODEL) -> dict[str, Any]:
    """Build a full shadow layer using the retrospective profile review.

    The review database is read-only evidence produced by
    ``wfa_profile_review``.  Its reconstructed references are kept separate
    from the point-in-time profile table and therefore cannot silently alter
    the existing v0.1 model.
    """
    schema(store)
    review_database = review_database.resolve()
    alias = "wfa_review"
    store.connection.execute(f"ATTACH DATABASE ? AS {alias}", (str(review_database),))
    try:
        store.connection.execute("DELETE FROM dan_aligned_run_performances WHERE model_version=?",
                                 (RECONSTRUCTED_MODEL_VERSION,))
        rows = store.connection.execute(
            f"""SELECT p.*, r.source, r.race_date, r.track_slug, r.race_number,
                      rr.weight_carried_kg, rr.finish_position, race.distance_metres,
                      dp.racing_age, dp.sex, dp.age_method, dp.profile_source,
                      dp.detail_json AS profile_detail_json,
                      wr.detail_json AS reconstructed_detail_json
                 FROM v3_run_performances p
                 JOIN v2_clean_races r ON r.race_id=p.race_id
                 JOIN v2_clean_runner_results rr
                   ON rr.race_id=p.race_id AND rr.runner_number=p.runner_number
                 JOIN race_results race
                   ON race.source=r.source AND race.race_date=r.race_date
                  AND race.track_slug=r.track_slug AND race.race_number=r.race_number
                 LEFT JOIN runner_derived_profiles dp
                   ON dp.derivation_version=? AND dp.source=r.source
                  AND dp.race_date=r.race_date AND dp.track_slug=r.track_slug
                  AND dp.race_number=r.race_number AND dp.runner_number=p.runner_number
                 LEFT JOIN {alias}.wfa_profile_review wr
                   ON wr.race_id=p.race_id AND wr.runner_number=p.runner_number
                WHERE p.model_version=?
                ORDER BY r.race_date, r.track_slug, r.race_number, p.runner_number""",
            (DERIVATION_VERSION, source_model)).fetchall()
        written = reconstructed = fallback = pace_removed_count = 0
        for row in rows:
            detail = json.loads(row["detail_json"] or "{}")
            pace = float(row["pace_component"] or 0.0)
            base = float(row["performance_rating"]) - pace
            if abs(pace) > 1e-9:
                pace_removed_count += 1
            review = json.loads(row["reconstructed_detail_json"] or "{}") if row["reconstructed_detail_json"] else {}
            ref = review.get("base_wfa_kg") if review.get("status") == "base_reference_available" else None
            ref_source = "retrospective-profile-reconstruction" if ref is not None else None
            if ref is None:
                ref, age_method, profile_source = _wfa_reference(row)
                ref_source = profile_source
                fallback += ref is not None
            else:
                age_method = "reconstructed-race-season-age"
                reconstructed += 1
            carried = float(row["weight_carried_kg"]) if row["weight_carried_kg"] is not None else None
            component = 0.0
            if ref is not None and carried is not None:
                component = max(-WFA_COMPONENT_CAP,
                                min(WFA_COMPONENT_CAP, (carried - ref) * WFA_POINTS_PER_KG))
            wfa_rating = base + component
            final = calibrate_upper_tail(wfa_rating)
            confidence = min(0.95, float(row["confidence"]) * (1.0 if ref is not None else 0.92))
            out_detail = {
                "method": "Dan-aligned WFA shadow v0.2 reconstructed profiles",
                "source_model": source_model,
                "pace_runner_adjustment_removed": round(pace, 4),
                "wfa_rules_source": RULES_SOURCE,
                "wfa_age_method": age_method,
                "wfa_profile_source": ref_source,
                "elite_calibration": {"knee": ELITE_KNEE, "tail_slope": ELITE_TAIL_SLOPE},
                "wfa_points_per_kg": WFA_POINTS_PER_KG,
                "wfa_component_cap": WFA_COMPONENT_CAP,
                "wfa_coverage": ref is not None,
                "reconstructed_profile_status": review.get("status"),
            }
            store.connection.execute(
                """INSERT INTO dan_aligned_run_performances VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (RECONSTRUCTED_MODEL_VERSION, source_model, row["race_id"], int(row["runner_number"]),
                 row["horse_key"], row["horse_name"], final, float(row["performance_rating"]),
                 wfa_rating, component, pace, carried, ref, confidence,
                 json.dumps(out_detail, sort_keys=True)))
            written += 1
        store.connection.commit()
        return {"model_version": RECONSTRUCTED_MODEL_VERSION, "source_model": source_model,
                "performances": written, "reconstructed_wfa": reconstructed,
                "fallback_wfa": fallback, "wfa_coverage": (reconstructed + fallback) / written if written else 0.0,
                "pace_removed": pace_removed_count, "elite_knee": ELITE_KNEE,
                "elite_tail_slope": ELITE_TAIL_SLOPE, "status": "research_shadow"}
    finally:
        store.connection.execute(f"DETACH DATABASE {alias}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    ap.add_argument("--reconstructed-review", type=Path,
                    help="Build the v0.2 reconstructed-profile shadow from a review database")
    args = ap.parse_args()
    store = RacingStore(args.database)
    try:
        report = (build_reconstructed(store, args.reconstructed_review)
                  if args.reconstructed_review else build(store))
        out = ROOT / "reports" / "v2_ratings" / "dan_aligned_build_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        store.close()


if __name__ == "__main__":
    main()
