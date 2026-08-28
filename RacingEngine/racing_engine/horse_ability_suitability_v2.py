"""Point-in-time distance/going suitability profiles for Horse Ability."""
from __future__ import annotations

import argparse,json,statistics
from collections import Counter,defaultdict
from dataclasses import asdict,dataclass
from pathlib import Path
from typing import Any

from .achieved_run_breakout import ROOT
from .collateral_revision_v2 import MODEL_VERSION as RUN_MODEL_VERSION,build as build_runs
from .evaluation_protocol import load_protocol,period_for
from .horse_ability_v2 import (AbilityState,_v1_history,evaluate,fit_temperature,
    _performance_rows as base_performance_rows,rejected_v2_state,utc_now)
from .horse_ability_v2_3 import CONFIGS,configured_state
from .storage import RacingStore

ABILITY_VERSION="horse-ability-v2.7-distance-going-shadow"
BASE_CONFIG=next(config for config in CONFIGS if config.name=="responsive")
COEFFICIENTS=(0.0,0.25,0.5,0.75,1.0)
DISTANCE_BANDS=("sprint","mile","middle","staying")
GOING_BUCKETS=("dry","soft","heavy")


@dataclass(frozen=True)
class ContextRun:
    day:str;rating:float;distance_band:str;going:str


def distance_band(distance:int|None)->str:
    value=int(distance or 0)
    if value<=1400:return "sprint"
    if value<=1800:return "mile"
    if value<=2400:return "middle"
    return "staying"


def going_bucket(value:str|None)->str:
    text=(value or "").lower()
    if "heavy" in text:return "heavy"
    if "soft" in text:return "soft"
    if any(word in text for word in ("good","firm","dry")):return "dry"
    return "unknown"


def _dimension_signal(history:list[ContextRun],attribute:str,target:str)->tuple[float,int]:
    recent=history[-12:]
    matched=[run.rating for run in recent if getattr(run,attribute)==target]
    if target=="unknown" or len(matched)<2 or len(recent)<4:return 0.0,len(matched)
    # The horse-specific overall median removes its broad ability level. Sparse
    # context evidence is shrunk heavily and can never move a rating by >6.
    raw=statistics.median(matched)-statistics.median(run.rating for run in recent)
    shrunk=raw*len(matched)/(len(matched)+3.0)
    return max(-6.0,min(6.0,shrunk)),len(matched)


def suitability_signals(history:list[ContextRun],target_distance:str,target_going:str)->dict[str,float|int]:
    distance,n_distance=_dimension_signal(history,"distance_band",target_distance)
    going,n_going=_dimension_signal(history,"going",target_going)
    return {"distance":distance,"going":going,"distance_runs":n_distance,"going_runs":n_going}


def context_state(history:list[ContextRun],as_of_date:str,target_distance:str,target_going:str,
                  distance_coefficient:float,going_coefficient:float)->tuple[AbilityState,dict[str,float|int]]:
    prior=[run for run in history if run.day<as_of_date]
    base=configured_state([(run.day,run.rating) for run in prior],as_of_date,BASE_CONFIG)
    signals=suitability_signals(prior,target_distance,target_going)
    adjustment=distance_coefficient*float(signals["distance"])+going_coefficient*float(signals["going"])
    adjustment=max(-8.0,min(8.0,adjustment))
    state=AbilityState(base.ability_rating+adjustment,base.recency_rating,base.sustainable_peak,
                       base.uncertainty,base.rated_runs,base.last_run_date)
    return state,{**signals,"adjustment":adjustment,"base_ability":base.ability_rating}


def _going_by_race(store:RacingStore)->dict[str,str]:
    return {row["race_id"]:going_bucket(row["track_condition"]) for row in store.connection.execute(
        """SELECT c.race_id,r.track_condition FROM v2_clean_races c JOIN race_results r
             ON r.source=c.source AND r.race_date=c.race_date AND r.track_slug=c.track_slug
            AND r.race_number=c.race_number""")}


def _performance_rows(store:RacingStore)->list[Any]:
    return store.connection.execute("""SELECT p.*,p.achieved_rating performance_rating,r.race_date,
             r.distance_metres FROM v2_achieved_run_candidates p JOIN v2_clean_races r USING(race_id)
             WHERE p.model_version=? ORDER BY r.race_date,p.race_id,p.runner_number""",
             (RUN_MODEL_VERSION,)).fetchall()


def build_raw_examples(store:RacingStore,protocol:dict)->tuple[list[dict[str,Any]],dict[str,int],dict[str,list[ContextRun]]]:
    going=_going_by_race(store);performances=defaultdict(list)
    for row in _performance_rows(store):performances[row["race_id"]].append(row)
    rejected_performances=defaultdict(list)
    for row in base_performance_rows(store,"form-first-v2.0"):rejected_performances[row["race_id"]].append(row)
    races_by_date=defaultdict(list)
    for race in store.connection.execute("SELECT * FROM v2_clean_races ORDER BY race_date,track_slug,race_number"):
        races_by_date[race["race_date"]].append(race)
    histories=defaultdict(list);rejected=defaultdict(list);v1=_v1_history(store);examples=[];excluded=Counter()
    for day in sorted(races_by_date):
        for race in races_by_date[day]:
            band=distance_band(race["distance_metres"]);surface=going.get(race["race_id"],"unknown")
            runners=[]
            result_rows=store.connection.execute("""SELECT * FROM v2_clean_runner_results WHERE race_id=?
                AND result_status='finished' AND finish_position IS NOT NULL ORDER BY runner_number""",
                (race["race_id"],)).fetchall()
            for runner in result_rows:
                key=runner["horse_key"]
                base=configured_state([(x.day,x.rating) for x in histories[key]],day,BASE_CONFIG)
                signals=suitability_signals(histories[key],band,surface)
                v1_values=[rating for run_day,rating in v1[key] if run_day<day]
                runners.append({"runner_number":int(runner["runner_number"]),"horse_key":key,
                    "horse_name":runner["horse_name"],"finish_position":int(runner["finish_position"]),
                    "base":base.ability_rating,"distance_signal":signals["distance"],"going_signal":signals["going"],
                    "rated_runs":base.rated_runs,
                    "rejected_v2":rejected_v2_state(rejected[key],day),
                    "v1":statistics.median(v1_values[-3:]) if v1_values else 100.0})
            if len(runners)<4:excluded["insufficient_starters"]+=1;continue
            winners=[i for i,row in enumerate(runners) if row["finish_position"]==1]
            if len(winners)!=1:excluded["invalid_winner_count"]+=1;continue
            period=period_for(day,protocol)
            if period is None:excluded["outside_protocol"]+=1;continue
            examples.append({"race_id":race["race_id"],"race_date":day,"period":period,"source":race["source"],
                "state":race["state"],"track_slug":race["track_slug"],"race_number":int(race["race_number"]),
                "distance_metres":race["distance_metres"],"distance_band":band,"going":surface,
                "class_family":race["class_family"],"winner":winners[0],"runners":runners})
        for race in races_by_date[day]:
            band=distance_band(race["distance_metres"]);surface=going.get(race["race_id"],"unknown")
            for row in performances.get(race["race_id"],[]):
                rating=float(row["performance_rating"]);histories[row["horse_key"]].append(ContextRun(day,rating,band,surface))
            for row in rejected_performances.get(race["race_id"],[]):
                rejected[row["horse_key"]].append((day,float(row["performance_rating"])))
    return examples,dict(excluded),histories


def select_coefficients(examples:list[dict[str,Any]])->dict[str,Any]:
    training=[race for race in examples if race["period"]=="train"];trials=[]
    for dc in COEFFICIENTS:
        for gc in COEFFICIENTS:
            for race in training:
                for runner in race["runners"]:runner["ability"]=runner["base"]+dc*runner["distance_signal"]+gc*runner["going_signal"]
            fit=fit_temperature(training,"ability")
            trials.append({"distance_coefficient":dc,"going_coefficient":gc,"temperature":fit["selected"],
                "training_log_loss":min(row["training_log_loss"] for row in fit["trials"]),"training_races":len(training)})
    selected=min(trials,key=lambda row:(row["training_log_loss"],row["distance_coefficient"],row["going_coefficient"]))
    return {"selection_data":"training only","selected":selected,"trials":trials}


def _apply(examples:list[dict[str,Any]],dc:float,gc:float)->None:
    for race in examples:
        for runner in race["runners"]:
            runner["ability"]=runner["base"]+max(-8.0,min(8.0,dc*runner["distance_signal"]+gc*runner["going_signal"]))


def profiles(histories:dict[str,list[ContextRun]],as_of_date:str,dc:float,gc:float)->dict[str,Any]:
    output={}
    for key,name in (("naturalfling","Natural Fling"),("shezaalibi","Sheza Alibi"),("gringotts","Gringotts"),("autumnglow","Autumn Glow")):
        history=histories.get(key,[]);base=configured_state([(x.day,x.rating) for x in history],as_of_date,BASE_CONFIG)
        distance={band:context_state(history,as_of_date,band,"unknown",dc,gc)[1]["adjustment"] for band in DISTANCE_BANDS}
        going={surface:context_state(history,as_of_date,"unknown",surface,dc,gc)[1]["adjustment"] for surface in GOING_BUCKETS}
        output[name]={"base_ability":base.ability_rating,"rated_runs":base.rated_runs,
                      "distance_adjustments":distance,"going_adjustments":going}
    return output


def run(store:RacingStore,protocol_path:Path,as_of_date:str)->dict[str,Any]:
    if store.connection.execute("SELECT count(*) FROM v2_achieved_run_candidates WHERE model_version=?",(RUN_MODEL_VERSION,)).fetchone()[0]<29000:build_runs(store)
    protocol=load_protocol(protocol_path);examples,exclusions,histories=build_raw_examples(store,protocol)
    selection=select_coefficients(examples);chosen=selection["selected"]
    _apply(examples,chosen["distance_coefficient"],chosen["going_coefficient"])
    training=[race for race in examples if race["period"]=="train"]
    fits={name:fit_temperature(training,field) for name,field in (("candidate","ability"),("rejected_v2","rejected_v2"),("v1","v1"))}
    evaluation=evaluate(examples,protocol,{name:fit["selected"] for name,fit in fits.items()})
    validation=evaluation["validation"];holdout=evaluation["historical_holdout"];reasons=[]
    for baseline in ("rejected_v2","v1","uniform"):
        if validation[f"candidate_vs_{baseline}"]["log_loss_delta"]>=0:reasons.append(f"validation did not beat {baseline}")
        if validation[f"candidate_vs_{baseline}"]["paired_log_loss_interval"]["upper"]>=0:reasons.append(f"validation uncertainty includes no improvement vs {baseline}")
        if holdout[f"candidate_vs_{baseline}"]["log_loss_delta"]>=0:reasons.append(f"historical holdout did not beat {baseline}")
    named=profiles(histories,as_of_date,chosen["distance_coefficient"],chosen["going_coefficient"])
    runner_rows=[runner for race in examples for runner in race["runners"]]
    return {"report_name":"horse-ability-v2.7-distance-going","model_version":ABILITY_VERSION,
        "run_model_version":RUN_MODEL_VERSION,"as_of_date":as_of_date,"selection":selection,
        "specification":{"distance_bands":DISTANCE_BANDS,"going_buckets":GOING_BUCKETS,
            "minimum_context_runs":2,"maximum_dimension_adjustment":6.0,"maximum_combined_adjustment":8.0,
            "current_condition_boundary":"known target distance/going modifies expected performance, not base ability"},
        "race_counts":dict(Counter(race["period"] for race in examples)),"exclusions":exclusions,
        "context_coverage":{"known_going_races":sum(race["going"]!="unknown" for race in examples),"races":len(examples),
            "runner_states":len(runner_rows),
            "nonzero_distance_signal":sum(float(row["distance_signal"])!=0 for row in runner_rows),
            "nonzero_going_signal":sum(float(row["going_signal"])!=0 for row in runner_rows)},
        "temperature_fits":fits,"evaluation":evaluation,"named_profiles":named,
        "decision":"PROMOTION_ELIGIBLE" if not reasons else "REVISE_OR_FREEZE","reasons":reasons,"generated_at":utc_now()}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    p.add_argument("--protocol",type=Path,default=ROOT/"config"/"evaluation_protocol_v1.json")
    p.add_argument("--as-of",default="2026-08-23");p.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"horse_ability_suitability_v2.json")
    a=p.parse_args();store=RacingStore(a.database)
    try:report=run(store,a.protocol,a.as_of)
    finally:store.close()
    rendered=json.dumps(report,indent=2,sort_keys=True)+"\n";a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered,encoding="utf-8");print(rendered,end="")


if __name__=="__main__":main()
