"""Build auditable weight context and strictly point-in-time feature rows."""
from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from .horse_profiles import DERIVATION_VERSION
from .sectional_features import FEATURE_VERSION as SECTIONAL_VERSION
from .storage import RacingStore, utc_now
from .wfa import standard_weight

ROOT = Path(__file__).resolve().parents[1]
WEIGHT_VERSION = "weight-context-v1.0"
PIT_VERSION = "point-in-time-context-v1.0"


def weight_condition(race_type: str | None, raw_class: str | None) -> str:
    text = f"{race_type or ''} {raw_class or ''}".lower().replace("-", " ")
    if "weight for age" in text or " wfa" in f" {text}":
        return "weight_for_age"
    if "set weight" in text and "penalt" in text:
        return "set_weights_plus_penalties"
    if "set weight" in text:
        return "set_weights"
    if "quality" in text:
        return "quality_handicap"
    if "handicap" in text or "benchmark" in text or " bm" in f" {text}":
        return "handicap"
    return "unknown"


def _number(payload: dict[str, Any], *paths: tuple[str, ...]) -> float | None:
    for path in paths:
        value: Any = payload
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
        try:
            if value not in (None, ""):
                match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
                if match:
                    return float(match.group())
        except (TypeError, ValueError):
            pass
    return None


def build_weight_contexts(store: RacingStore) -> dict[str, Any]:
    rows = store.connection.execute(
        """SELECT rr.*,r.distance_metres,r.race_class,rc.race_type,rc.raw_class_text,rc.benchmark,
                  l.horse_id,dp.racing_age,dp.sex,dp.detail_json profile_detail,
                  cp.shrunk_field_rating class_rating
             FROM runner_results rr JOIN race_results r USING(source,race_date,track_slug,race_number)
             LEFT JOIN race_classifications rc USING(source,race_date,track_slug,race_number)
             LEFT JOIN runner_horse_links l USING(source,race_date,track_slug,race_number,runner_number)
             LEFT JOIN runner_derived_profiles dp ON dp.derivation_version=? AND dp.source=rr.source
              AND dp.race_date=rr.race_date AND dp.track_slug=rr.track_slug
              AND dp.race_number=rr.race_number AND dp.runner_number=rr.runner_number
             LEFT JOIN class_prior_research cp ON cp.research_version='class-prior-research-v1.0'
              AND cp.as_of_date='2026-08-16' AND cp.level='detail' AND cp.group_key=rc.class_family
            ORDER BY rr.race_date,rr.track_slug,rr.race_number,rr.runner_number""",
        (DERIVATION_VERSION,)).fetchall()
    races: dict[tuple, list] = defaultdict(list)
    for row in rows:
        races[tuple(row[x] for x in ("source","race_date","track_slug","race_number"))].append(row)
    histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    counts = Counter(); now = utc_now(); inserts=[]
    for race_rows in races.values():
        carried = [float(r["weight_carried_kg"]) for r in race_rows if r["weight_carried_kg"] is not None]
        median = statistics.median(carried) if carried else None
        for row in race_rows:
            payload = json.loads(row["raw_json"] or "{}")
            allocated = _number(payload, ("allocated_weight_kg",), ("weightAllocated",), ("raw_entry","weight"))
            actual = float(row["weight_carried_kg"]) if row["weight_carried_kg"] is not None else None
            claim = _number(payload, ("apprentice_claim_kg",), ("apprenticeClaim",), ("raw_entry","apprenticeClaim"))
            overweight = _number(payload, ("overweight_kg",), ("overweight",), ("raw_entry","overweight"))
            penalty = _number(payload, ("penalty_kg",), ("penalty",), ("raw_entry","penalty"))
            profile = json.loads(row["profile_detail"] or "{}")
            wfa = None
            if row["racing_age"] is not None and row["sex"] and row["distance_metres"]:
                wfa = standard_weight(row["race_date"], int(row["distance_metres"]), int(row["racing_age"]), row["sex"],
                    northern_sired_jan_jul_foal=bool(profile.get("ar170_eligible")))
            previous = histories[row["horse_id"]][-1] if row["horse_id"] and histories[row["horse_id"]] else None
            condition = weight_condition(row["race_type"], row["raw_class_text"] or row["race_class"])
            current_class = float(row["benchmark"] or row["class_rating"]) if (row["benchmark"] or row["class_rating"]) is not None else None
            class_change = current_class-previous["class"] if previous and current_class is not None and previous["class"] is not None else None
            evidence = {"timing":"post-race/result record; not automatically prediction-eligible",
                "missing": [name for name,value in {"carried":actual,"allocated":allocated,"claim":claim,"overweight":overweight,"penalty":penalty,"wfa":wfa}.items() if value is None],
                "official_benchmark_scale":"1 point = 0.5kg; kept separate from internal performance points"}
            values = (WEIGHT_VERSION,row["source"],row["race_date"],row["track_slug"],row["race_number"],row["runner_number"],row["horse_id"],condition,
                actual,allocated,claim,overweight,penalty,wfa,actual-wfa if actual is not None and wfa is not None else None,
                actual-median if actual is not None and median is not None else None,row["official_handicap_rating"],row["benchmark"],
                actual-previous["weight"] if previous and actual is not None and previous["weight"] is not None else None,
                float(row["official_handicap_rating"])-previous["rating"] if previous and row["official_handicap_rating"] is not None and previous["rating"] is not None else None,
                class_change,int(row["distance_metres"])-previous["distance"] if previous and row["distance_metres"] and previous["distance"] else None,
                int(class_change>0) if class_change is not None else None,json.dumps(evidence,sort_keys=True),now)
            inserts.append(values)
            counts[condition] += 1
            if row["horse_id"]:
                histories[row["horse_id"]].append({"weight":actual,"rating":float(row["official_handicap_rating"]) if row["official_handicap_rating"] is not None else None,
                    "class":current_class,"distance":int(row["distance_metres"]) if row["distance_metres"] else None})
    store.connection.execute("DELETE FROM runner_weight_contexts WHERE feature_version=?",(WEIGHT_VERSION,))
    store.connection.executemany("INSERT INTO runner_weight_contexts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",inserts)
    store.connection.commit()
    return {"feature_version":WEIGHT_VERSION,"rows":len(rows),"weight_conditions":dict(counts)}


def build_point_in_time_features(store: RacingStore) -> dict[str, Any]:
    rows = store.connection.execute(
        """SELECT rr.source,rr.race_date,rr.track_slug,rr.race_number,rr.runner_number,rr.runner_name,l.horse_id,
                  r.distance_metres,r.track_condition,rr.distance_travelled_vs_winner_metres,
                  rc.class_family,wc.weight_condition,wc.carried_weight_kg,wc.weight_change_kg,wc.official_rating,
                  rs.combined_rating race_strength_rating,dv.variant_seconds,cs.quality_status,
                  COALESCE(se.event_count,0) steward_count
             FROM runner_results rr JOIN race_results r USING(source,race_date,track_slug,race_number)
             LEFT JOIN race_classifications rc USING(source,race_date,track_slug,race_number)
             LEFT JOIN runner_horse_links l USING(source,race_date,track_slug,race_number,runner_number)
             LEFT JOIN runner_weight_contexts wc ON wc.feature_version=? AND wc.source=rr.source
              AND wc.race_date=rr.race_date AND wc.track_slug=rr.track_slug AND wc.race_number=rr.race_number AND wc.runner_number=rr.runner_number
             LEFT JOIN race_strength_ratings rs ON rs.race_strength_version='race-strength-v1.0' AND rs.source=rr.source AND rs.race_date=rr.race_date AND rs.track_slug=rr.track_slug AND rs.race_number=rr.race_number
             LEFT JOIN (SELECT source,race_date,track_slug,MAX(shrunk_variant_lengths) variant_seconds FROM daily_track_variants WHERE variant_version='daily-track-variant-v1.0' GROUP BY source,race_date,track_slug) dv
               ON dv.source=rr.source AND dv.race_date=rr.race_date AND dv.track_slug=rr.track_slug
             LEFT JOIN canonical_sectionals cs ON cs.feature_version=? AND cs.source=rr.source AND cs.race_date=rr.race_date AND cs.track_slug=rr.track_slug AND cs.race_number=rr.race_number AND cs.runner_number=rr.runner_number
             LEFT JOIN (SELECT race_date,track_slug,race_number,horse_name,count(*) event_count FROM steward_events GROUP BY race_date,track_slug,race_number,horse_name) se
               ON se.race_date=rr.race_date AND se.track_slug=rr.track_slug AND se.race_number=rr.race_number AND se.horse_name=rr.runner_name COLLATE NOCASE
            ORDER BY rr.race_date,rr.track_slug,rr.race_number,rr.runner_number""",(WEIGHT_VERSION,SECTIONAL_VERSION)).fetchall()
    history: dict[str,list[dict[str,Any]]] = defaultdict(list); now=utc_now(); debutants=0; inserts=[]
    for row in rows:
        prior = history[row["horse_id"]] if row["horse_id"] else []
        last = prior[-1] if prior else None; debutants += not bool(last)
        days = (date.fromisoformat(row["race_date"])-date.fromisoformat(last["race_date"])).days if last else None
        campaign = 1
        if last and days is not None and days <= 90: campaign=last["campaign"]+1
        availability={"cutoff_exclusive":row["race_date"],"lookahead_checked":True,
            "current_result_weight_excluded":True,"unknown_is_not_zero":True}
        values=(PIT_VERSION,row["source"],row["race_date"],row["track_slug"],row["race_number"],row["runner_number"],row["horse_id"],len(prior),days,campaign,
            last.get("weight") if last else None,last.get("weight_change") if last else None,last.get("rating") if last else None,last.get("strength") if last else None,
            last.get("variant") if last else None,last.get("going") if last else None,last.get("section_conf") if last else None,last.get("dtw") if last else None,last.get("stewards") if last else None,
            row["distance_metres"],row["weight_condition"],row["class_family"],json.dumps(availability,sort_keys=True),now)
        inserts.append(values)
        if row["horse_id"]:
            history[row["horse_id"]].append({"race_date":row["race_date"],"campaign":campaign,"weight":row["carried_weight_kg"],"weight_change":row["weight_change_kg"],
                "rating":row["official_rating"],"strength":row["race_strength_rating"],"variant":row["variant_seconds"],"going":row["track_condition"],
                "section_conf":1.0 if row["quality_status"]=="ok" else (0.5 if row["quality_status"] else None),"dtw":row["distance_travelled_vs_winner_metres"],"stewards":row["steward_count"]})
    store.connection.execute("DELETE FROM point_in_time_features WHERE feature_version=?",(PIT_VERSION,))
    store.connection.executemany("INSERT INTO point_in_time_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",inserts)
    store.connection.commit()
    return {"feature_version":PIT_VERSION,"rows":len(rows),"debutant_rows":debutants,"strict_prior_history":True}


def build_all(store: RacingStore) -> dict[str, Any]:
    return {"baseline":{"model_version":"performance-par-v1.0","status":"frozen","weight_candidates":"shadow_only"},
            "weight_context":build_weight_contexts(store),"point_in_time":build_point_in_time_features(store)}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite"); parser.add_argument("--output",type=Path)
    parser.add_argument("--component",choices=("all","weight","point-in-time"),default="all")
    args=parser.parse_args(); store=RacingStore(args.database)
    try:
        if args.component=="weight": report={"weight_context":build_weight_contexts(store)}
        elif args.component=="point-in-time": report={"point_in_time":build_point_in_time_features(store)}
        else: report=build_all(store)
    finally: store.close()
    text=json.dumps(report,indent=2,sort_keys=True)+"\n"
    if args.output: args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(text)
    else: print(text,end="")

if __name__ == "__main__": main()
