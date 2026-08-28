"""Training-selected campaign/layoff uncertainty layer for Horse Ability."""
from __future__ import annotations

import argparse,json,math
from dataclasses import dataclass,asdict
from datetime import date
from pathlib import Path

from .achieved_run_breakout import ROOT
from .collateral_revision_v2 import MODEL_VERSION as RUN_MODEL_VERSION,build as build_runs,revised_current_states
from .evaluation_protocol import load_protocol
from .horse_ability_v2 import AbilityState,build_point_in_time_examples,fit_temperature,run as run_ability
from .horse_ability_v2_3 import CONFIGS,configured_state
from .storage import RacingStore

ABILITY_VERSION="horse-ability-v2.6-campaign-layoff-shadow"
BASE_CONFIG=next(config for config in CONFIGS if config.name=="responsive")

@dataclass(frozen=True)
class CampaignConfig:
    name:str;grace_days:int;decay_half_life:float|None;uncertainty_per_30d:float

CONFIGS_CAMPAIGN=(CampaignConfig("no_decay",60,None,0.0),CampaignConfig("slow",60,365,.25),
                  CampaignConfig("medium",60,240,.50),CampaignConfig("fast",45,180,.75))


def campaign_state(history:list[tuple[str,float]],as_of_date:str,config:CampaignConfig)->AbilityState:
    state=configured_state(history,as_of_date,BASE_CONFIG)
    if state.last_run_date is None:return state
    gap=max(0,(date.fromisoformat(as_of_date)-date.fromisoformat(state.last_run_date)).days-config.grace_days)
    if config.decay_half_life is None:return state
    retention=math.exp(-math.log(2)*gap/config.decay_half_life)
    ability=100+retention*(state.ability_rating-100)
    uncertainty=state.uncertainty+config.uncertainty_per_30d*(gap/30)
    return AbilityState(ability,state.recency_rating,state.sustainable_peak,uncertainty,
                        state.rated_runs,state.last_run_date)


def select_config(store:RacingStore,protocol:dict)->dict:
    trials=[]
    for config in CONFIGS_CAMPAIGN:
        builder=lambda history,day,c=config:campaign_state(history,day,c)
        version=f"{ABILITY_VERSION}-selection-{config.name}"
        examples,_=build_point_in_time_examples(store,protocol,run_model_version=RUN_MODEL_VERSION,
            ability_version=version,state_builder=builder)
        training=[race for race in examples if race["period"]=="train"]
        fit=fit_temperature(training,"ability")
        trials.append({"config":asdict(config),"training_races":len(training),"temperature":fit["selected"],
          "training_log_loss":min(row["training_log_loss"] for row in fit["trials"])})
        store.connection.execute("DELETE FROM v2_horse_ability_states WHERE model_version=?",(version,))
    store.connection.commit();selected=min(trials,key=lambda row:(row["training_log_loss"],row["config"]["name"]))
    return {"selection_data":"training only","selected":selected,"trials":trials}


def run(store:RacingStore,protocol_path:Path,as_of_date:str)->dict:
    existing=store.connection.execute("SELECT count(*) FROM v2_achieved_run_candidates WHERE model_version=?",
                                      (RUN_MODEL_VERSION,)).fetchone()[0]
    if existing<29000:build_runs(store)
    protocol=load_protocol(protocol_path);selection=select_config(store,protocol)
    chosen=next(c for c in CONFIGS_CAMPAIGN if c.name==selection["selected"]["config"]["name"])
    builder=lambda history,day:campaign_state(history,day,chosen)
    report=run_ability(store,protocol_path,as_of_date,run_model_version=RUN_MODEL_VERSION,
      ability_version=ABILITY_VERSION,report_name="horse-ability-v2.6-campaign-layoff",state_builder=builder)
    report["campaign_selection"]=selection
    return report


def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    p.add_argument("--protocol",type=Path,default=ROOT/"config"/"evaluation_protocol_v1.json")
    p.add_argument("--as-of",default="2026-08-23");p.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"horse_ability_campaign_v2.json")
    a=p.parse_args();s=RacingStore(a.database)
    try:r=run(s,a.protocol,a.as_of)
    finally:s.close()
    rendered=json.dumps(r,indent=2,sort_keys=True)+"\n";a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered,encoding="utf-8");print(rendered,end="")


if __name__=="__main__":main()
