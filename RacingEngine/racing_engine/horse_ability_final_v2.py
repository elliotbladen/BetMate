"""Final validation and research freeze for Horse Ability V2."""
from __future__ import annotations

import argparse,json,math,statistics
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any

from .achieved_run_breakout import ROOT
from .collateral_revision_v2 import MODEL_VERSION as RUN_MODEL_VERSION,build as build_runs,revised_current_states
from .evaluation_protocol import load_protocol
from .horse_ability_suitability_v2 import build_raw_examples
from .horse_ability_v2 import evaluate,fit_temperature,probabilities,utc_now
from .horse_ability_v2_3 import CONFIGS,configured_state
from .storage import RacingStore

MODEL_VERSION="horse-ability-v2.8-final-research-freeze"
BASE_CONFIG=next(config for config in CONFIGS if config.name=="responsive")


def final_decision(evaluation:dict[str,Any],named:dict[str,bool])->tuple[str,list[str]]:
    reasons=[];validation=evaluation["validation"];holdout=evaluation["historical_holdout"]
    for baseline in ("rejected_v2","v1","uniform"):
        if validation[f"candidate_vs_{baseline}"]["log_loss_delta"]>=0:
            reasons.append(f"validation did not beat {baseline}")
        if holdout[f"candidate_vs_{baseline}"]["log_loss_delta"]>=0:
            reasons.append(f"historical holdout did not beat {baseline}")
    if validation["candidate_vs_v1"]["paired_log_loss_interval"]["upper"]>=0:
        reasons.append("validation uncertainty versus V1 includes zero")
    reasons.extend(f"named audit failed: {name}" for name,passed in named.items() if not passed)
    # A locked research freeze is valid for a genuinely out-of-sample market
    # backtest. Production promotion retains the stricter uncertainty gate.
    decision="PRODUCTION_PROMOTION_ELIGIBLE" if not reasons else "FINAL_RESEARCH_FREEZE"
    return decision,reasons


def _losses(race:dict[str,Any],temperatures:dict[str,float])->dict[str,float]:
    winner=race["winner"];rows=race["runners"]
    result={}
    for name,field in (("candidate","ability"),("rejected_v2","rejected_v2"),("v1","v1")):
        result[name]=-math.log(max(probabilities([row[field] for row in rows],temperatures[name])[winner],1e-12))
    result["uniform"]=math.log(len(rows));return result


def _field_band(size:int)->str:
    if size<=7:return "small_4_7"
    if size<=11:return "medium_8_11"
    return "large_12_plus"


def segment_report(examples:list[dict[str,Any]],temperatures:dict[str,float])->dict[str,Any]:
    groups=defaultdict(list)
    for race in examples:
        if race["period"] not in ("validation","historical_holdout"):continue
        losses=_losses(race,temperatures);depth=statistics.median(row["rated_runs"] for row in race["runners"])
        labels={"period":race["period"],"distance":race["distance_band"],"going":race["going"],
            "class":race["class_family"],"field_size":_field_band(len(race["runners"])),
            "history_depth":"sparse_0_2" if depth<=2 else ("developing_3_5" if depth<=5 else "established_6_plus"),
            "season":race["race_date"][:4]}
        for dimension,label in labels.items():groups[(dimension,label)].append(losses)
    output={}
    for (dimension,label),rows in sorted(groups.items()):
        if len(rows)<30:continue
        candidate=statistics.mean(row["candidate"] for row in rows)
        output.setdefault(dimension,{})[label]={"races":len(rows),"candidate_log_loss":candidate,
            "vs_v1":candidate-statistics.mean(row["v1"] for row in rows),
            "vs_rejected_v2":candidate-statistics.mean(row["rejected_v2"] for row in rows),
            "vs_uniform":candidate-statistics.mean(row["uniform"] for row in rows)}
    return output


def _named_audits(store:RacingStore,current:list[dict[str,Any]])->tuple[dict[str,Any],dict[str,bool]]:
    by_key={row["horse_key"]:row for row in current}
    natural=store.connection.execute("""SELECT a.achieved_rating,r.race_date,r.track_slug,r.race_number
        FROM v2_achieved_run_candidates a JOIN v2_clean_races r USING(race_id)
        WHERE a.model_version=? AND a.horse_key='naturalfling' ORDER BY r.race_date DESC LIMIT 1""",
        (RUN_MODEL_VERSION,)).fetchone()
    rematch=[dict(row) for row in store.connection.execute("""SELECT a.horse_key,a.horse_name,a.achieved_rating,
        c.finish_position,c.beaten_lengths FROM v2_achieved_run_candidates a
        JOIN v2_clean_runner_results c USING(race_id,runner_number) JOIN v2_clean_races r USING(race_id)
        WHERE a.model_version=? AND r.race_date='2026-08-22' AND r.track_slug='randwick' AND r.race_number=9
        AND a.horse_key IN ('shezaalibi','gringotts')""",(RUN_MODEL_VERSION,))]
    rematch_by={row["horse_key"]:row for row in rematch}
    checks={"natural_fling_achieved_100_110":bool(natural and 100<=natural["achieved_rating"]<=110),
        "sheza_wfa_run_above_gringotts":bool(rematch_by.get("shezaalibi") and rematch_by.get("gringotts") and
            rematch_by["shezaalibi"]["achieved_rating"]>rematch_by["gringotts"]["achieved_rating"]),
        "sheza_initial_ability_above_gringotts":by_key["shezaalibi"]["ability_rating"]>by_key["gringotts"]["ability_rating"]}
    detail={"natural_fling_latest":dict(natural) if natural else None,"wfa_rematch":rematch,
        "initial_current":{"Natural Fling":by_key["naturalfling"],"Sheza Alibi":by_key["shezaalibi"],
            "Gringotts":by_key["gringotts"],"Autumn Glow":by_key["autumnglow"]},"checks":checks}
    return detail,checks


def run(store:RacingStore,protocol_path:Path,as_of_date:str)->dict[str,Any]:
    if store.connection.execute("SELECT count(*) FROM v2_achieved_run_candidates WHERE model_version=?",(RUN_MODEL_VERSION,)).fetchone()[0]<29000:build_runs(store)
    protocol=load_protocol(protocol_path);examples,exclusions,histories=build_raw_examples(store,protocol)
    for race in examples:
        for row in race["runners"]:row["ability"]=row["base"]
    training=[race for race in examples if race["period"]=="train"]
    fits={name:fit_temperature(training,field) for name,field in (("candidate","ability"),("rejected_v2","rejected_v2"),("v1","v1"))}
    temperatures={name:fit["selected"] for name,fit in fits.items()};evaluation=evaluate(examples,protocol,temperatures)
    names={row["horse_key"]:row["horse_name"] for row in store.connection.execute(
        "SELECT horse_key,max(horse_name) horse_name FROM v2_achieved_run_candidates WHERE model_version=? GROUP BY horse_key",
        (RUN_MODEL_VERSION,))}
    current=[]
    for key,history in histories.items():
        state=configured_state([(run.day,run.rating) for run in history],as_of_date,BASE_CONFIG)
        current.append({"horse_key":key,"horse_name":names[key],"ability_rating":state.ability_rating,"uncertainty":state.uncertainty,
            "rated_runs":state.rated_runs,"last_run_date":state.last_run_date})
    current.sort(key=lambda row:row["ability_rating"],reverse=True)
    audits,checks=_named_audits(store,current);decision,reasons=final_decision(evaluation,checks)
    revised=revised_current_states(store,as_of_date)
    revised_named={row["horse_name"]:row for row in revised if row["horse_key"] in ("shezaalibi","gringotts")}
    return {"report_name":"horse-ability-v2-final-validation","model_version":MODEL_VERSION,
        "run_model_version":RUN_MODEL_VERSION,"as_of_date":as_of_date,"frozen_configuration":{
            "history":"responsive: four runs, 90-day half-life, 0.25 peak blend, 1.5 reliability prior, 0.10 trajectory",
            "handicap_weight":"25% initial; later collateral revision stored by effective date","campaign_decay":"zero",
            "distance_suitability":"zero","going_suitability":"zero","probability_temperature":temperatures["candidate"]},
        "race_counts":dict(Counter(race["period"] for race in examples)),"exclusions":exclusions,
        "evaluation":evaluation,"segment_validation":segment_report(examples,temperatures),"named_audits":audits,
        "revised_current_named":revised_named,"current_top_50":current[:50],"decision":decision,"reasons":reasons,
        "production_ratings_changed":False,"backtest_status":"configuration locked; eligible for untouched Betfair backtest",
        "generated_at":utc_now()}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    p.add_argument("--protocol",type=Path,default=ROOT/"config"/"evaluation_protocol_v1.json")
    p.add_argument("--as-of",default="2026-08-23");p.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"horse_ability_final_v2.json")
    a=p.parse_args();store=RacingStore(a.database)
    try:report=run(store,a.protocol,a.as_of)
    finally:store.close()
    rendered=json.dumps(report,indent=2,sort_keys=True)+"\n";a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered,encoding="utf-8");print(rendered,end="")


if __name__=="__main__":main()
