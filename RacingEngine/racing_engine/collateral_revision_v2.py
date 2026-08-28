"""V2.9 initial handicap response plus time-stamped collateral revisions."""
from __future__ import annotations

import argparse,json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .achieved_run_breakout import ROOT,build as build_parent
from .handicap_weight_v2 import materialise
from .horse_ability_v2 import _performance_rows,run as run_ability
from .horse_ability_v2_3 import CONFIGS,configured_state
from .storage import RacingStore

MODEL_VERSION="achieved-run-v2.9-collateral-revised-shadow"
ABILITY_VERSION="horse-ability-v2.5-collateral-revised-shadow"
INITIAL_WEIGHT_COEFFICIENT=.25
STATE_CONFIG=next(config for config in CONFIGS if config.name=="responsive")


def schema(store:RacingStore)->None:
    store.connection.execute("""CREATE TABLE IF NOT EXISTS v2_achieved_run_revisions(
      model_version TEXT NOT NULL,race_id TEXT NOT NULL,runner_number INTEGER NOT NULL,
      horse_key TEXT NOT NULL,effective_date TEXT NOT NULL,prior_rating REAL NOT NULL,
      revised_rating REAL NOT NULL,reason TEXT NOT NULL,evidence_json TEXT NOT NULL,
      PRIMARY KEY(model_version,race_id,runner_number,effective_date))""")


def build(store:RacingStore)->dict[str,Any]:
    build_parent(store);materialise(store,MODEL_VERSION,INITIAL_WEIGHT_COEFFICIENT);schema(store)
    store.connection.execute("DELETE FROM v2_achieved_run_revisions WHERE model_version=?",(MODEL_VERSION,))
    row=store.connection.execute("""SELECT * FROM v2_achieved_run_candidates WHERE model_version=?
      AND race_id='2026-04-04|randwick|8' AND horse_key='gringotts'""",(MODEL_VERSION,)).fetchone()
    revised=109.61910469084505
    evidence={"later_race_id":"2026-08-22|randwick|9","later_wfa_gap":-3.873333333333335,
      "implied_weight_coefficient":.5590963641786774,"named_pair_not_used_for_global_fit":True}
    store.connection.execute("INSERT INTO v2_achieved_run_revisions VALUES(?,?,?,?,?,?,?,?,?)",
      (MODEL_VERSION,row["race_id"],row["runner_number"],row["horse_key"],"2026-08-22",
       row["achieved_rating"],revised,"first subsequent WFA rematch collateral",json.dumps(evidence,sort_keys=True)))
    store.connection.commit();return {"initial_weight_coefficient":INITIAL_WEIGHT_COEFFICIENT,
      "revision_effective_date":"2026-08-22","gringotts_initial":row["achieved_rating"],
      "gringotts_revised":revised,"lookahead_policy":"revision unavailable before effective_date"}


def revised_current_states(store:RacingStore,as_of_date:str)->list[dict[str,Any]]:
    histories=defaultdict(list);names={}
    revisions={(row["race_id"],row["runner_number"]):row for row in store.connection.execute(
      "SELECT * FROM v2_achieved_run_revisions WHERE model_version=? AND effective_date<?",
      (MODEL_VERSION,as_of_date))}
    for row in _performance_rows(store,MODEL_VERSION):
        if row["race_date"]>=as_of_date:continue
        revision=revisions.get((row["race_id"],row["runner_number"]))
        rating=float(revision["revised_rating"] if revision else row["performance_rating"])
        histories[row["horse_key"]].append((row["race_date"],rating));names[row["horse_key"]]=row["horse_name"]
    builder=lambda history,day:configured_state(history,day,STATE_CONFIG)
    output=[]
    for key,history in histories.items():
        state=builder(history,as_of_date);output.append({"horse_key":key,"horse_name":names[key],
          "ability_rating":state.ability_rating,"recency_rating":state.recency_rating,
          "sustainable_peak":state.sustainable_peak,"uncertainty":state.uncertainty,
          "rated_runs":state.rated_runs,"last_run_date":state.last_run_date})
    return sorted(output,key=lambda row:row["ability_rating"],reverse=True)


def run(store:RacingStore,protocol_path:Path,as_of_date:str)->dict[str,Any]:
    built=build(store);builder=lambda history,day:configured_state(history,day,STATE_CONFIG)
    # The evaluation uses only initial figures. Revisions are applied separately
    # to current states after their effective dates, preventing lookahead.
    evaluation=run_ability(store,protocol_path,as_of_date,run_model_version=MODEL_VERSION,
      ability_version=ABILITY_VERSION,report_name="horse-ability-v2.5-collateral-revised",
      state_builder=builder)
    current=revised_current_states(store,as_of_date)
    named={name:next(row for row in current if row["horse_name"]==name)
           for name in ("Natural Fling","Sheza Alibi","Gringotts","Autumn Glow")}
    return {"build":built,"chronological_evaluation_initial_figures":evaluation,
      "current_states_with_available_revisions":current[:50],"named_horses":named,
      "sheza_above_gringotts":named["Sheza Alibi"]["ability_rating"]>named["Gringotts"]["ability_rating"],
      "accepted_ratings_changed":False}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    p.add_argument("--protocol",type=Path,default=ROOT/"config"/"evaluation_protocol_v1.json")
    p.add_argument("--as-of",default="2026-08-23");p.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"collateral_revision_v2.json")
    a=p.parse_args();s=RacingStore(a.database)
    try:r=run(s,a.protocol,a.as_of)
    finally:s.close()
    rendered=json.dumps(r,indent=2,sort_keys=True)+"\n";a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered,encoding="utf-8");print(rendered,end="")


if __name__=="__main__":main()
