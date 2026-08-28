"""Training-only audit of handicap carried-weight response on V2.7 figures."""
from __future__ import annotations

import argparse,json
from pathlib import Path
from typing import Any

from .achieved_run_breakout import MODEL_VERSION as PARENT_VERSION,ROOT,build as build_parent
from .evaluation_protocol import load_protocol
from .horse_ability_v2 import build_point_in_time_examples,fit_temperature,run as run_ability
from .horse_ability_v2_3 import CONFIGS,configured_state
from .storage import RacingStore

MODEL_VERSION="achieved-run-v2.8-handicap-weight-shadow"
ABILITY_VERSION="horse-ability-v2.4-handicap-weight-shadow"
COEFFICIENTS=(0.0,0.25,0.5,0.75,1.0)
STATE_CONFIG=next(config for config in CONFIGS if config.name=="responsive")


def materialise(store:RacingStore,model_version:str,coefficient:float)->dict[str,int]:
    store.connection.execute("DELETE FROM v2_achieved_run_candidates WHERE model_version=?",(model_version,))
    rows=store.connection.execute("SELECT * FROM v2_achieved_run_candidates WHERE model_version=?",(PARENT_VERSION,)).fetchall()
    changed=0
    for row in rows:
        detail=json.loads(row["detail_json"]);old=float(row["weight_component"])
        handicap=detail.get("race_weight_policy")=="handicap_relative_burden"
        new=old*coefficient if handicap else old;delta=new-old
        detail={**detail,"candidate_version":model_version,"handicap_weight_parent":PARENT_VERSION,
                "handicap_weight_coefficient":coefficient,"original_weight_component":old,
                "candidate_weight_component":new,"training_selected":model_version==MODEL_VERSION}
        store.connection.execute("""INSERT INTO v2_achieved_run_candidates VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (model_version,row["race_id"],row["runner_number"],row["horse_key"],row["horse_name"],
             float(row["achieved_rating"])+delta,row["base_rating"],row["race_strength"],row["base_race_strength"],
             row["winner_margin_component"],row["beaten_margin_component"],new,row["time_variant_component"],
             row["sectional_component"],row["collateral_revision_component"],row["confidence"],json.dumps(detail,sort_keys=True)))
        changed+=int(abs(delta)>1e-9)
    store.connection.commit();return {"performances":len(rows),"changed_handicap_rows":changed}


def select_coefficient(store:RacingStore,protocol:dict)->dict[str,Any]:
    trials=[];builder=lambda history,day:configured_state(history,day,STATE_CONFIG)
    for coefficient in COEFFICIENTS:
        version=f"{MODEL_VERSION}-selection-{coefficient:.2f}"
        build=materialise(store,version,coefficient)
        examples,_=build_point_in_time_examples(store,protocol,run_model_version=version,
            ability_version=f"{ABILITY_VERSION}-selection-{coefficient:.2f}",state_builder=builder)
        training=[race for race in examples if race["period"]=="train"]
        fit=fit_temperature(training,"ability")
        trials.append({"coefficient":coefficient,"training_races":len(training),
            "training_log_loss":min(x["training_log_loss"] for x in fit["trials"]),
            "temperature":fit["selected"],**build})
        store.connection.execute("DELETE FROM v2_achieved_run_candidates WHERE model_version=?",(version,))
        store.connection.execute("DELETE FROM v2_horse_ability_states WHERE model_version=?",
                                 (f"{ABILITY_VERSION}-selection-{coefficient:.2f}",))
    store.connection.commit();selected=min(trials,key=lambda row:(row["training_log_loss"],row["coefficient"]))
    return {"selection_data":"training period only","selected":selected,"trials":trials}


def named_runs(store:RacingStore)->list[dict]:
    return [dict(row) for row in store.connection.execute("""SELECT a.horse_name,r.race_date,r.track_slug,r.race_number,
        c.finish_position,c.beaten_lengths,c.weight_carried_kg,a.achieved_rating,a.weight_component
        FROM v2_achieved_run_candidates a JOIN v2_clean_races r USING(race_id)
        JOIN v2_clean_runner_results c USING(race_id,runner_number) WHERE a.model_version=? AND
        ((a.horse_key='gringotts' AND r.race_date='2026-04-04') OR
         (a.horse_key='jigsaw' AND r.race_date='2026-03-14') OR
         (a.horse_key='tropicus' AND r.race_date='2026-02-21')) ORDER BY r.race_date""",(MODEL_VERSION,))]


def run(store:RacingStore,protocol_path:Path,as_of_date:str)->dict[str,Any]:
    build_parent(store);protocol=load_protocol(protocol_path);selection=select_coefficient(store,protocol)
    coefficient=float(selection["selected"]["coefficient"]);build=materialise(store,MODEL_VERSION,coefficient)
    builder=lambda history,day:configured_state(history,day,STATE_CONFIG)
    ability=run_ability(store,protocol_path,as_of_date,run_model_version=MODEL_VERSION,
        ability_version=ABILITY_VERSION,report_name="horse-ability-v2.4-handicap-weight",state_builder=builder)
    return {"model_version":MODEL_VERSION,"selection":selection,"build":build,"named_run_audits":named_runs(store),
            "ability":ability,"sheza_above_gringotts":bool(ability["named_horses"]["Sheza Alibi"]["ability_rating"]>
                ability["named_horses"]["Gringotts"]["ability_rating"]),"accepted_ratings_changed":False}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    p.add_argument("--protocol",type=Path,default=ROOT/"config"/"evaluation_protocol_v1.json")
    p.add_argument("--as-of",default="2026-08-23");p.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"handicap_weight_v2.json")
    a=p.parse_args();s=RacingStore(a.database)
    try:r=run(s,a.protocol,a.as_of)
    finally:s.close()
    rendered=json.dumps(r,indent=2,sort_keys=True)+"\n";a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered,encoding="utf-8");print(rendered,end="")


if __name__=="__main__":main()
