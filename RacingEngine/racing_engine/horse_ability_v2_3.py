"""Training-selected history-depth, recency and trajectory Horse Ability V2.3."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import dataclass,asdict
from datetime import date
from pathlib import Path

from .achieved_run_breakout import MODEL_VERSION as RUN_MODEL_VERSION, ROOT, build as build_runs
from .evaluation_protocol import load_protocol
from .horse_ability_v2 import (AbilityState, NEUTRAL, build_point_in_time_examples,
    fit_temperature, run as run_ability)
from .storage import RacingStore

ABILITY_VERSION="horse-ability-v2.3-history-trajectory-shadow"


@dataclass(frozen=True)
class StateConfig:
    name:str; window:int; half_life:float; peak_blend:float; reliability_prior:float; trajectory_blend:float


CONFIGS=(
    StateConfig("baseline",6,180,.35,2.0,0.0),
    StateConfig("responsive",4,90,.25,1.5,.10),
    StateConfig("recent",3,60,.15,1.0,.15),
    StateConfig("trajectory",4,120,.25,1.5,.20),
)


def configured_state(history:list[tuple[str,float]],as_of_date:str,config:StateConfig)->AbilityState:
    prior=[(day,float(rating)) for day,rating in history if day<as_of_date]
    if not prior:return AbilityState(NEUTRAL,NEUTRAL,NEUTRAL,12.0,0,None)
    recent=prior[-config.window:];cutoff=date.fromisoformat(as_of_date)
    values=[rating for _,rating in recent]
    weights=[math.exp(-math.log(2)*max(0,(cutoff-date.fromisoformat(day)).days)/config.half_life)
             for day,_ in recent]
    recency=sum(v*w for v,w in zip(values,weights))/sum(weights)
    peak=statistics.mean(sorted(values,reverse=True)[:min(2,len(values))])
    repeatability=min(1.0,len(values)/3.0)
    trajectory=0.0
    if len(values)>=3:
        earlier=statistics.mean(values[:-1]);trajectory=max(-8.0,min(8.0,values[-1]-earlier))
    raw=recency+config.peak_blend*repeatability*(peak-recency)+config.trajectory_blend*trajectory
    reliability=len(prior)/(len(prior)+config.reliability_prior)
    ability=NEUTRAL+reliability*(raw-NEUTRAL)
    median=statistics.median(values);mad=statistics.median(abs(v-median) for v in values)
    uncertainty=max(2.0,10.0/math.sqrt(len(prior))+.5*mad)
    return AbilityState(ability,recency,peak,uncertainty,len(prior),prior[-1][0])


def select_config(store:RacingStore,protocol:dict)->dict:
    trials=[]
    for config in CONFIGS:
        builder=lambda history,day,c=config:configured_state(history,day,c)
        examples,_=build_point_in_time_examples(store,protocol,run_model_version=RUN_MODEL_VERSION,
            ability_version=f"{ABILITY_VERSION}-selection-{config.name}",state_builder=builder)
        training=[race for race in examples if race["period"]=="train"]
        fit=fit_temperature(training,"ability")
        trials.append({"config":asdict(config),"training_races":len(training),
                       "temperature":fit["selected"],
                       "training_log_loss":min(x["training_log_loss"] for x in fit["trials"])})
        store.connection.execute("DELETE FROM v2_horse_ability_states WHERE model_version=?",
                                 (f"{ABILITY_VERSION}-selection-{config.name}",))
    store.connection.commit()
    selected=min(trials,key=lambda row:(row["training_log_loss"],row["config"]["name"]))
    return {"selection_data":"training period only","named_ordering_not_a_fit_target":True,
            "selected":selected,"trials":trials}


def top_performances(store:RacingStore)->list[dict]:
    return [dict(row) for row in store.connection.execute(
        """SELECT a.horse_name,a.achieved_rating,r.race_date,r.track_slug,r.race_number,
                  r.class_family,c.finish_position,c.beaten_lengths,c.weight_carried_kg
             FROM v2_achieved_run_candidates a JOIN v2_clean_races r USING(race_id)
             JOIN v2_clean_runner_results c USING(race_id,runner_number)
            WHERE a.model_version=? ORDER BY a.achieved_rating DESC LIMIT 10""",(RUN_MODEL_VERSION,))]


def run(store:RacingStore,protocol_path:Path,as_of_date:str)->dict:
    build_runs(store);protocol=load_protocol(protocol_path);selection=select_config(store,protocol)
    chosen=next(c for c in CONFIGS if c.name==selection["selected"]["config"]["name"])
    builder=lambda history,day:configured_state(history,day,chosen)
    report=run_ability(store,protocol_path,as_of_date,run_model_version=RUN_MODEL_VERSION,
        ability_version=ABILITY_VERSION,report_name="horse-ability-v2.3-history-trajectory",
        state_builder=builder)
    report["state_config_selection"]=selection
    report["named_ordering_audit"]={"required":"Sheza Alibi slightly above Gringotts after direct WFA defeat; audit only",
        "passed":bool(report["named_horses"]["Sheza Alibi"]["ability_rating"]>
                      report["named_horses"]["Gringotts"]["ability_rating"]),
        "sheza_alibi":report["named_horses"]["Sheza Alibi"],"gringotts":report["named_horses"]["Gringotts"]}
    report["top_10_achieved_performances"]=top_performances(store)
    return report


def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    p.add_argument("--protocol",type=Path,default=ROOT/"config"/"evaluation_protocol_v1.json")
    p.add_argument("--as-of",default="2026-08-23");p.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"horse_ability_v2_3_history.json")
    a=p.parse_args();s=RacingStore(a.database)
    try:r=run(s,a.protocol,a.as_of)
    finally:s.close()
    rendered=json.dumps(r,indent=2,sort_keys=True)+"\n";a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered,encoding="utf-8");print(rendered,end="")


if __name__=="__main__":main()
