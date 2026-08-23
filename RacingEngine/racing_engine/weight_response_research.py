"""Training-fitted and IFHA-distance carried-weight research candidates."""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from .horse_profiles import DERIVATION_VERSION
from .performance import MODEL_VERSION, build_horse_states, run_pipeline, utc_now
from .storage import RacingStore
from .wfa import standard_weight


ROOT = Path(__file__).resolve().parents[1]
TRAINING_CUTOFF = "2024-09-01"
SHRINKAGE_PAIRS = 200.0
VARIANTS = {
    "ifha_distance_weight": "performance-par-v1.0+ifha-distance-weight-research-v1.0",
    "learned_weight_response": "performance-par-v1.0+learned-weight-response-research-v1.0",
}


def race_type(value: str | None) -> str:
    text = (value or "").lower()
    if "handicap" in text or text.startswith("quality"): return "handicap"
    if "weight for age" in text: return "wfa"
    if "set weight" in text: return "set_weight"
    return "other"


def distance_segment(distance: int) -> str:
    return "sprint" if distance <= 1400 else ("middle" if distance <= 2000 else "staying")


def ifha_points_per_kg(distance: int) -> float:
    """Convert IFHA's approximate pounds-per-length curve to lengths per kg."""
    if distance <= 1000: pounds_per_length = 3.0
    elif distance <= 1600: pounds_per_length = 3.0 - (distance - 1000) / 600.0
    elif distance <= 2800: pounds_per_length = 2.0 - (distance - 1600) / 1200.0
    else: pounds_per_length = 1.0
    return 1.0 / (pounds_per_length * 0.45359237)


def _base_rows(store: RacingStore, as_of_date: str, before: str) -> list:
    return store.connection.execute(
        """SELECT p.*,rr.weight_carried_kg,r.distance_metres,r.race_class,l.horse_id,h.canonical_name,
                  dp.racing_age,dp.sex,dp.detail_json profile_detail_json
             FROM run_performances p JOIN runner_results rr USING(source,race_date,track_slug,race_number,runner_number)
             JOIN race_results r USING(source,race_date,track_slug,race_number)
             JOIN runner_horse_links l USING(source,race_date,track_slug,race_number,runner_number)
             JOIN horses h ON h.horse_id=l.horse_id
             LEFT JOIN runner_derived_profiles dp ON dp.derivation_version=? AND dp.source=p.source
               AND dp.race_date=p.race_date AND dp.track_slug=p.track_slug
               AND dp.race_number=p.race_number AND dp.runner_number=p.runner_number
            WHERE p.model_version=? AND p.as_of_date=? AND p.race_date<?
            ORDER BY p.source,p.race_date,p.track_slug,p.race_number,p.runner_number""",
        (DERIVATION_VERSION, MODEL_VERSION, as_of_date, before)).fetchall()


def _features(rows: list) -> list[dict[str, Any]]:
    grouped: dict[tuple, list] = defaultdict(list)
    for row in rows: grouped[(row["source"],row["race_date"],row["track_slug"],row["race_number"])].append(row)
    result = []
    for race_rows in grouped.values():
        raw = {}
        for row in race_rows:
            detail = json.loads(row["profile_detail_json"] or "{}")
            reference = (standard_weight(row["race_date"],int(row["distance_metres"]),int(row["racing_age"]),row["sex"],
                northern_sired_jan_jul_foal=bool(detail.get("ar170_eligible")))
                if row["racing_age"] is not None and row["sex"] and row["weight_carried_kg"] is not None else None)
            raw[row["runner_number"]] = float(row["weight_carried_kg"])-reference if reference is not None else None
        known=[value for value in raw.values() if value is not None]; centre=statistics.median(known) if len(known)>=2 else None
        for row in race_rows:
            burden=raw[row["runner_number"]]
            result.append({"row":row,"burden":burden-centre if burden is not None and centre is not None else None,
                "race_type":race_type(row["race_class"]),"distance_segment":distance_segment(int(row["distance_metres"]))})
    return result


def fit_training_coefficients(store: RacingStore) -> dict[str, Any]:
    run_pipeline(store, TRAINING_CUTOFF, min_par_sample=5, model_version=MODEL_VERSION)
    features=_features(_base_rows(store,TRAINING_CUTOFF,TRAINING_CUTOFF)); by_horse=defaultdict(list)
    for feature in features:
        if feature["burden"] is not None: by_horse[feature["row"]["horse_id"]].append(feature)
    pairs=defaultdict(list)
    for horse_rows in by_horse.values():
        horse_rows.sort(key=lambda value:value["row"]["race_date"])
        for previous,current in zip(horse_rows,horse_rows[1:]):
            key=(current["race_type"],current["distance_segment"])
            if key!=(previous["race_type"],previous["distance_segment"]): continue
            x=max(-8.0,min(8.0,current["burden"]-previous["burden"]))
            y=max(-12.0,min(12.0,float(current["row"]["performance_rating"])-float(previous["row"]["performance_rating"])))
            pairs[key].append((x,y))
    estimates={}
    for key,values in pairs.items():
        mean_x=statistics.mean(x for x,_ in values); mean_y=statistics.mean(y for _,y in values)
        denominator=sum((x-mean_x)**2 for x,_ in values)
        slope=sum((x-mean_x)*(y-mean_y) for x,y in values)/denominator if denominator else 0.0
        raw=max(0.0,-slope); shrink=len(values)/(len(values)+SHRINKAGE_PAIRS)
        estimates["|".join(key)]={"pairs":len(values),"raw_points_per_kg":raw,
            "shrinkage":shrink,"shrunk_points_per_kg":raw*shrink}
    return {"training_cutoff_exclusive":TRAINING_CUTOFF,"method":"within-horse consecutive-run differences",
            "winsorisation":{"weight_delta_kg":8,"performance_delta_points":12},
            "shrinkage_pairs":SHRINKAGE_PAIRS,"segments":estimates,"feature_rows":len(features)}


def build_candidates(store:RacingStore,as_of_date:str,*,min_par_sample:int=5)->dict[str,Any]:
    run_pipeline(store,as_of_date,min_par_sample=min_par_sample,model_version=MODEL_VERSION)
    fit=fit_training_coefficients(store); features=_features(_base_rows(store,as_of_date,as_of_date)); now=utc_now(); summaries={}
    for name,model in VARIANTS.items():
        nonzero=0; components=[]
        for feature in features:
            row=feature["row"]; burden=feature["burden"]
            if name=="ifha_distance_weight": coefficient=ifha_points_per_kg(int(row["distance_metres"]))
            else: coefficient=fit["segments"].get(f"{feature['race_type']}|{feature['distance_segment']}",{}).get("shrunk_points_per_kg",0.0)
            component=burden*coefficient if burden is not None else 0.0; nonzero+=abs(component)>1e-12;components.append(abs(component))
            detail={**json.loads(row["detail_json"]),"weight_response":{"variant":name,"burden_vs_race_median_kg":burden,
                "points_per_kg":coefficient,"component":component,"race_type":feature["race_type"],
                "distance_segment":feature["distance_segment"],"training_cutoff_exclusive":TRAINING_CUTOFF,
                "research_only":True}}
            store.connection.execute("""INSERT INTO run_performances
              (model_version,as_of_date,source,race_date,track_slug,race_number,runner_number,horse_key,horse_name,
               performance_rating,time_component,margin_component,sectional_component,pace_component,confidence,detail_json,created_at)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(model_version,as_of_date,source,race_date,track_slug,race_number,runner_number)
              DO UPDATE SET performance_rating=excluded.performance_rating,detail_json=excluded.detail_json,created_at=excluded.created_at""",
              (model,as_of_date,row["source"],row["race_date"],row["track_slug"],row["race_number"],row["runner_number"],
               row["horse_id"],row["canonical_name"],float(row["performance_rating"])+component,row["time_component"],
               row["margin_component"],row["sectional_component"],row["pace_component"],row["confidence"],json.dumps(detail,sort_keys=True),now))
        store.connection.commit();states=build_horse_states(store,as_of_date,model_version=model)
        summaries[name]={"model_version":model,"performances":len(features),"horse_states":states,"nonzero":nonzero,
            "mean_absolute_component":statistics.mean(components) if components else 0.0}
    return {"as_of_date":as_of_date,"training_fit":fit,"variants":summaries}
