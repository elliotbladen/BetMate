"""Research-only historical merit adjustment using official WFA references."""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from typing import Any

from .horse_profiles import DERIVATION_VERSION
from .performance import MODEL_VERSION, build_horse_states, run_pipeline, utc_now
from .storage import RacingStore
from .wfa import RULES_SOURCE, standard_weight


MODEL = "performance-par-v1.0+wfa-relative-weight-research-v1.0"
KG_TO_RATING_POINTS = 1.0


def build_candidate(store: RacingStore, as_of_date: str, *, min_par_sample: int = 5) -> dict[str, Any]:
    run_pipeline(store, as_of_date, min_par_sample=min_par_sample, model_version=MODEL_VERSION)
    rows = store.connection.execute(
        """SELECT p.*,rr.weight_carried_kg,race.distance_metres,l.horse_id,h.canonical_name,
                  dp.racing_age,dp.sex,dp.country_code,dp.age_method,dp.profile_source,dp.detail_json profile_detail_json
             FROM run_performances p JOIN runner_results rr
               USING(source,race_date,track_slug,race_number,runner_number)
             JOIN race_results race USING(source,race_date,track_slug,race_number)
             JOIN runner_horse_links l USING(source,race_date,track_slug,race_number,runner_number)
             JOIN horses h ON h.horse_id=l.horse_id
             LEFT JOIN runner_derived_profiles dp ON dp.derivation_version=? AND dp.source=p.source
               AND dp.race_date=p.race_date AND dp.track_slug=p.track_slug
               AND dp.race_number=p.race_number AND dp.runner_number=p.runner_number
            WHERE p.model_version=? AND p.as_of_date=? AND p.race_date<?
            ORDER BY p.source,p.race_date,p.track_slug,p.race_number,p.runner_number""",
        (DERIVATION_VERSION, MODEL_VERSION, as_of_date, as_of_date)).fetchall()
    grouped: dict[tuple, list] = defaultdict(list)
    for row in rows:
        grouped[(row["source"], row["race_date"], row["track_slug"], row["race_number"])].append(row)
    now = utc_now(); eligible = adjusted = 0; components: list[float] = []
    for race_rows in grouped.values():
        residuals = {}
        for row in race_rows:
            reference = None
            profile_detail = json.loads(row["profile_detail_json"] or "{}")
            ar170_eligible = bool(profile_detail.get("ar170_eligible"))
            if row["racing_age"] is not None and row["sex"] and row["distance_metres"]:
                reference = standard_weight(row["race_date"], int(row["distance_metres"]),
                                            int(row["racing_age"]), row["sex"],
                                            northern_sired_jan_jul_foal=ar170_eligible)
            residuals[row["runner_number"]] = (float(row["weight_carried_kg"]) - reference
                if reference is not None and row["weight_carried_kg"] is not None else None)
        known = [value for value in residuals.values() if value is not None]
        centre = statistics.median(known) if len(known) >= 2 else None
        eligible += len(known)
        for row in race_rows:
            profile_detail = json.loads(row["profile_detail_json"] or "{}")
            residual = residuals[row["runner_number"]]
            component = (residual - centre) * KG_TO_RATING_POINTS if residual is not None and centre is not None else 0.0
            adjusted += int(abs(component) > 1e-12); components.append(abs(component))
            reference = (float(row["weight_carried_kg"]) - residual
                         if residual is not None and row["weight_carried_kg"] is not None else None)
            detail = {**json.loads(row["detail_json"]), "wfa_relative_weight": {
                "model": MODEL, "rules_source": RULES_SOURCE, "racing_age": row["racing_age"],
                "age_method": row["age_method"], "sex": row["sex"], "country_code": row["country_code"],
                "profile_source": row["profile_source"], "official_wfa_kg": reference,
                "carried_kg": row["weight_carried_kg"], "carried_minus_wfa_kg": residual,
                "race_median_carried_minus_wfa_kg": centre, "rating_component": component,
                "research_only": True, "northern_hemisphere_ar170_status": profile_detail.get("ar170_status"),
                "ar170_applied": bool(profile_detail.get("ar170_eligible"))}}
            store.connection.execute(
                """INSERT INTO run_performances
                   (model_version,as_of_date,source,race_date,track_slug,race_number,runner_number,horse_key,horse_name,
                    performance_rating,time_component,margin_component,sectional_component,pace_component,confidence,
                    detail_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(model_version,as_of_date,source,race_date,track_slug,race_number,runner_number) DO UPDATE SET
                    horse_key=excluded.horse_key,horse_name=excluded.horse_name,
                    performance_rating=excluded.performance_rating,detail_json=excluded.detail_json,created_at=excluded.created_at""",
                (MODEL,as_of_date,row["source"],row["race_date"],row["track_slug"],row["race_number"],row["runner_number"],
                 row["horse_id"],row["canonical_name"],float(row["performance_rating"])+component,row["time_component"],
                 row["margin_component"],row["sectional_component"],row["pace_component"],row["confidence"],
                 json.dumps(detail,sort_keys=True),now))
    store.connection.commit(); states = build_horse_states(store, as_of_date, model_version=MODEL)
    return {"model_version": MODEL, "as_of_date": as_of_date, "performances": len(rows), "horse_states": states,
            "profile_eligible_performances": eligible, "nonzero_adjustments": adjusted,
            "mean_absolute_adjustment": statistics.mean(components) if components else 0.0,
            "status": "RESEARCH_ONLY_INCOMPLETE_PROFILE_COVERAGE"}
