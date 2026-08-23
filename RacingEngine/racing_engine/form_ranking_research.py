"""Training-fitted current-form and race-level conditional-logit research."""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .benchmark import _summary
from .evaluation_protocol import assess_eligibility, load_protocol, period_for, protocol_hash, score_race
from .performance import MODEL_VERSION
from .promotion_evaluation import paired_interval
from .ratings import horse_key
from .storage import RacingStore, utc_now

ROOT = Path(__file__).resolve().parents[1]
FORM_VERSION = "current-form-conditional-v1.0"
RANK_VERSION = "race-level-conditional-logit-v1.0"
FEATURES = ("peak_gap", "uncertainty", "history", "official_rating", "prior_strength", "days_since", "campaign")
FORM_FEATURES = ("peak_gap", "uncertainty", "history")
FORM_SIMPLE_FEATURES = ("peak_gap", "history")
RACE_CORE_FEATURES = ("peak_gap", "uncertainty", "history", "official_rating", "days_since", "campaign")


def probabilities(utilities: list[float]) -> list[float]:
    maximum=max(utilities); values=[math.exp(max(-40.0,min(40.0,value-maximum))) for value in utilities]; total=sum(values)
    return [value/total for value in values]


def _centred(values: list[float | None], scale: float) -> list[float]:
    known=[value for value in values if value is not None]
    centre=sum(known)/len(known) if known else 0.0
    return [((value-centre)/scale if value is not None else 0.0) for value in values]


def _race_features(starters: tuple[dict[str,Any],...], states: dict[str,Any], pit: dict[tuple,Any]) -> list[dict[str,float]]:
    base=[]; rows=[]
    for runner in starters:
        state=states.get(horse_key(runner["runner_name"])); key=(runner["source"],runner["race_date"],runner["track_slug"],runner["race_number"],runner["runner_number"]); point=pit.get(key)
        overall=float(state["overall_rating"]) if state else 100.0; peak=float(state["peak_rating"]) if state else overall
        history=int(state["rated_runs"]) if state else 0; uncertainty=float(state["uncertainty"]) if state else 12.0
        rows.append({"base":overall/18.0,"peak_gap":(peak-overall)/10.0,"uncertainty":uncertainty/10.0,
            "history":math.log1p(history)/2.0,"official_rating_raw":float(point["prior_official_rating"]) if point and point["prior_official_rating"] is not None else None,
            "prior_strength_raw":float(point["prior_race_strength"]) if point and point["prior_race_strength"] is not None else None,
            "days_since":min(float(point["days_since_last_run"]),180.0)/100.0 if point and point["days_since_last_run"] is not None else 0.0,
            "campaign":min(float(point["campaign_run_number"]),8.0)/5.0 if point else 0.0})
    official=_centred([row["official_rating_raw"] for row in rows],10.0); strength=_centred([row["prior_strength_raw"] for row in rows],10.0)
    for row,o,s in zip(rows,official,strength): row["official_rating"]=o; row["prior_strength"]=s
    return rows


def load_races(store:RacingStore, protocol:dict[str,Any], periods:tuple[str,...]) -> tuple[list[dict[str,Any]],dict[str,int]]:
    dates=[row[0] for row in store.connection.execute("SELECT DISTINCT race_date FROM race_results ORDER BY race_date") if period_for(row[0],protocol) in periods]
    pit={tuple(row[x] for x in ("source","target_race_date","track_slug","race_number","runner_number")):row for row in store.connection.execute(
        "SELECT * FROM point_in_time_features WHERE feature_version='point-in-time-context-v1.0'")}
    races=[]; exclusions=Counter()
    for race_date in dates:
        states={row["horse_key"]:row for row in store.connection.execute("SELECT horse_key,overall_rating,peak_rating,consistency,rated_runs,uncertainty FROM horse_rating_states WHERE model_version=? AND as_of_date=?",(MODEL_VERSION,race_date))}
        identities=store.connection.execute("SELECT source,race_date,track_slug,race_number,state,distance_metres,track_condition FROM race_results WHERE race_date=? ORDER BY track_slug,race_number,source",(race_date,)).fetchall()
        for identity in identities:
            key=tuple(identity[x] for x in ("source","race_date","track_slug","race_number"))
            raw=[dict(row) for row in store.connection.execute("SELECT source,race_date,track_slug,race_number,runner_number,runner_name,finish_position,result_status FROM runner_results WHERE source=? AND race_date=? AND track_slug=? AND race_number=? ORDER BY runner_number",key)]
            eligible=assess_eligibility(raw,protocol)
            if not eligible.eligible: exclusions[eligible.reason or "unknown"]+=1; continue
            feats=_race_features(eligible.starters,states,pit); outcomes=[int(row["finish_position"]==1) for row in eligible.starters]
            races.append({"period":period_for(race_date,protocol),"source":identity["source"],"race_date":race_date,"track_slug":identity["track_slug"],"race_number":identity["race_number"],"state":identity["state"],"features":feats,"outcomes":outcomes})
    return races,dict(exclusions)


def loss_and_gradient(races:list[dict[str,Any]], weights:dict[str,float], active:tuple[str,...], l2:float) -> tuple[float,dict[str,float]]:
    gradient={name:0.0 for name in active}; loss=0.0
    for race in races:
        utilities=[row["base"]+sum(weights[name]*row[name] for name in active) for row in race["features"]]; probs=probabilities(utilities); winner=race["outcomes"].index(1); loss-=math.log(max(probs[winner],1e-12))
        for index,(prob,outcome) in enumerate(zip(probs,race["outcomes"])):
            for name in active: gradient[name]+=(prob-outcome)*race["features"][index][name]
    count=max(1,len(races)); loss=loss/count + .5*l2*sum(weights[name]**2 for name in active)
    return loss,{name:gradient[name]/count+l2*weights[name] for name in active}


def fit(races:list[dict[str,Any]], active:tuple[str,...], *, iterations:int=800, learning_rate:float=.08, l2:float=.05) -> dict[str,Any]:
    weights={name:0.0 for name in active}; best_loss=float("inf"); best=weights.copy(); stale=0
    for iteration in range(iterations):
        loss,gradient=loss_and_gradient(races,weights,active,l2); step=learning_rate/math.sqrt(1+iteration/100)
        for name in active: weights[name]-=step*max(-5.0,min(5.0,gradient[name]))
        if loss < best_loss-1e-9: best_loss=loss; best=weights.copy(); stale=0
        else: stale+=1
        if stale>=100: break
    return {"weights":best,"regularization":l2,"iterations":iteration+1,"training_penalized_log_loss":best_loss}


def fit_chronological_cv(races:list[dict[str,Any]], active:tuple[str,...]) -> dict[str,Any]:
    """Choose regularisation inside training only, then refit all training."""
    ordered=sorted(races,key=lambda race:(race["race_date"],race["track_slug"],race["race_number"])); split=max(1,int(len(ordered)*.7)); early=ordered[:split]; late=ordered[split:]
    trials=[]
    for l2 in (.01,.05,.10,.20):
        fitted=fit(early,active,iterations=600,l2=l2); loss,_=loss_and_gradient(late,fitted["weights"],active,0.0)
        trials.append({"regularization":l2,"internal_late_train_log_loss":loss})
    selected=min(trials,key=lambda row:row["internal_late_train_log_loss"])["regularization"]; final=fit(ordered,active,l2=selected)
    return {**final,"selection":"chronological 70/30 split within training only","selection_trials":trials}


def evaluate(races:list[dict[str,Any]], weights:dict[str,float], active:tuple[str,...], protocol:dict[str,Any]) -> tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    scored=[]; paired=[]
    for race in races:
        base_probs=probabilities([row["base"] for row in race["features"]]); candidate_probs=probabilities([row["base"]+sum(weights[name]*row[name] for name in active) for row in race["features"]])
        baseline=score_race(base_probs,race["outcomes"],protocol); candidate=score_race(candidate_probs,race["outcomes"],protocol)
        detail={key:race[key] for key in ("period","source","race_date","track_slug","race_number")}; detail["field_size"]=len(race["outcomes"])
        scored.append({**detail,**candidate}); paired.append({**detail,"baseline_log_loss":baseline["log_loss"],"candidate_log_loss":candidate["log_loss"],"baseline_race_brier":baseline["race_brier"],"candidate_race_brier":candidate["race_brier"],"baseline_winner_rank":baseline["winner_rank"]})
    return scored,paired


def _comparison(scored:list[dict[str,Any]],paired:list[dict[str,Any]],period:str,protocol:dict[str,Any],seed:int) -> dict[str,Any]:
    s=[row for row in scored if row["period"]==period]; p=[row for row in paired if row["period"]==period]; metric=_summary(s)
    baseline_ll=sum(row["baseline_log_loss"] for row in p)/len(p) if p else None; baseline_brier=sum(row["baseline_race_brier"] for row in p)/len(p) if p else None
    baseline_top1=sum(row["baseline_winner_rank"]<=1 for row in p)/len(p) if p else None
    interval=paired_interval(p,int(protocol["resampling"]["repetitions"]),float(protocol["resampling"]["confidence_level"]),seed)
    return {**metric,"baseline_mean_log_loss":baseline_ll,"log_loss_delta":metric["mean_log_loss"]-baseline_ll if p else None,
        "baseline_mean_race_brier":baseline_brier,"race_brier_delta":metric["mean_race_brier"]-baseline_brier if p else None,
        "baseline_top_1":baseline_top1,"top_1_delta":metric["top_1"]-baseline_top1 if p else None,"paired_log_loss_interval":interval}


def run_research(store:RacingStore, protocol_path:Path) -> dict[str,Any]:
    protocol=load_protocol(protocol_path); races,exclusions=load_races(store,protocol,("train","validation","historical_holdout")); train=[race for race in races if race["period"]=="train"]
    specifications={
        "form_peak_history":{"version":FORM_VERSION+"-simple","features":FORM_SIMPLE_FEATURES},
        "current_form":{"version":FORM_VERSION,"features":FORM_FEATURES},
        "race_core":{"version":RANK_VERSION+"-core","features":RACE_CORE_FEATURES},
        "race_core_cv":{"version":RANK_VERSION+"-core-cv","features":RACE_CORE_FEATURES,"chronological_cv":True},
        "race_level":{"version":RANK_VERSION,"features":FEATURES},
    }
    results={}; seed=int(protocol["resampling"]["seed"])
    for offset,(name,spec) in enumerate(specifications.items()):
        fitted=fit_chronological_cv(train,spec["features"]) if spec.get("chronological_cv") else fit(train,spec["features"]); scored,paired=evaluate(races,fitted["weights"],spec["features"],protocol)
        periods={period:_comparison(scored,paired,period,protocol,seed+offset) for period in ("train","validation","historical_holdout")}
        validation=periods["validation"]; holdout=periods["historical_holdout"]; reasons=[]
        if validation["log_loss_delta"]>=0: reasons.append("validation log loss did not improve")
        if validation["paired_log_loss_interval"]["upper"]>=0: reasons.append("validation interval includes no improvement")
        if holdout["log_loss_delta"]>=0: reasons.append("holdout direction did not agree")
        if validation["top_1_delta"] < -.005 or holdout["top_1_delta"] < -.005: reasons.append("top-pick strike rate materially declined")
        results[name]={"model_version":spec["version"],"fitted_on":"train only","fit":fitted,"periods":periods,
            "decision":"RESEARCH_PASS" if not reasons else "FREEZE_OR_REVISE","reasons":reasons}
    now=utc_now(); report={"report_name":"current-form-and-race-ranking-research","protocol_hash":protocol_hash(protocol),"baseline_model":MODEL_VERSION,
        "training_policy":"coefficients fitted only on 2023-08-12 through 2024-08-31","market_policy":{"comparison_window":"2025 through 2026-08-15 only","ratings_engine_first":True,"future_bet_rule":"15% EV versus opening price, reported separately against opening and close"},
        "races":dict(Counter(race["period"] for race in races)),"exclusions":exclusions,"candidates":results,
        "promotion_warning":"historical validation and holdout have been observed; prospective confirmation remains required","generated_at":now}
    return report


def render_markdown(report:dict[str,Any])->str:
    lines=["# Current-form and race-level ranking research","",f"Baseline: `{report['baseline_model']}`","","| Candidate | Train Δ log loss | Validation Δ | Holdout Δ | Validation interval | Decision |","| --- | ---: | ---: | ---: | ---: | --- |"]
    for name,item in report["candidates"].items():
        p=item["periods"]; interval=p["validation"]["paired_log_loss_interval"]
        lines.append(f"| {name} | {p['train']['log_loss_delta']:.6f} | {p['validation']['log_loss_delta']:.6f} | {p['historical_holdout']['log_loss_delta']:.6f} | [{interval['lower']:.6f}, {interval['upper']:.6f}] | {item['decision']} |")
    lines += ["","Negative differences favour the candidate. Coefficients were fitted on training only.","",f"Market policy: {report['market_policy']}",""]
    return "\n".join(lines)


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite"); parser.add_argument("--protocol",type=Path,default=ROOT/"config"/"evaluation_protocol_v1.json"); parser.add_argument("--output",type=Path)
    args=parser.parse_args(); store=RacingStore(args.database)
    try: report=run_research(store,args.protocol)
    finally: store.close()
    rendered=json.dumps(report,indent=2,sort_keys=True)+"\n"
    if args.output: args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(rendered); args.output.with_suffix(".md").write_text(render_markdown(report))
    else: print(rendered,end="")

if __name__=="__main__": main()
