"""Step 3: isolate and evaluate conservative time/form-anchored margin blends."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .benchmark import _summary
from .evaluation_protocol import load_protocol, protocol_hash, score_race
from .promotion_evaluation import paired_interval
from .ratings import softmax
from .storage import RacingStore, utc_now
from .winning_margin import MODEL as FULL_MARGIN_MODEL

ROOT=Path(__file__).resolve().parents[1]
IDENTITY_MODEL="performance-par-v1.0+identity-v1.0"
OFFICIAL_MODEL="performance-par-v1.0"
VARIANTS={"margin_25":.25,"margin_50":.50,"margin_100":1.0}


def blend_ratings(identity:list[float],margin:list[float],strength:float)->list[float]:
    if len(identity)!=len(margin): raise ValueError("rating books must have the same runners")
    return [base+strength*(candidate-base) for base,candidate in zip(identity,margin)]


def _books(store:RacingStore,protocol_digest:str)->list[dict[str,Any]]:
    models=(OFFICIAL_MODEL,IDENTITY_MODEL,FULL_MARGIN_MODEL); rows=store.connection.execute(
        """SELECT model_version,period,source,race_date,track_slug,race_number,runner_number,
                  raw_rating,outcome
             FROM benchmark_predictions WHERE protocol_hash=? AND model_version IN (?,?,?)
            ORDER BY race_date,track_slug,race_number,source,runner_number,model_version""",
        (protocol_digest,*models)).fetchall()
    grouped:dict[tuple,dict[str,list]]=defaultdict(lambda:defaultdict(list))
    for row in rows:
        key=(row["period"],row["source"],row["race_date"],row["track_slug"],row["race_number"])
        grouped[key][row["model_version"]].append(row)
    books=[]
    for key,by_model in grouped.items():
        if any(model not in by_model for model in models): continue
        runner_sets=[[(row["runner_number"],row["outcome"]) for row in by_model[model]] for model in models]
        if not all(value==runner_sets[0] for value in runner_sets[1:]): continue
        books.append({"period":key[0],"source":key[1],"race_date":key[2],"track_slug":key[3],"race_number":key[4],
            "outcomes":[int(row["outcome"]) for row in by_model[IDENTITY_MODEL]],
            "official":[float(row["raw_rating"]) for row in by_model[OFFICIAL_MODEL]],
            "identity":[float(row["raw_rating"]) for row in by_model[IDENTITY_MODEL]],
            "margin":[float(row["raw_rating"]) for row in by_model[FULL_MARGIN_MODEL]]})
    return books


def _evaluate(books:list[dict[str,Any]],strength:float,protocol:dict[str,Any])->tuple[list[dict],list[dict]]:
    scored=[];paired=[]
    for book in books:
        identity=score_race(softmax(book["identity"]),book["outcomes"],protocol)
        official=score_race(softmax(book["official"]),book["outcomes"],protocol)
        candidate=score_race(softmax(blend_ratings(book["identity"],book["margin"],strength)),book["outcomes"],protocol)
        detail={key:book[key] for key in ("period","source","race_date","track_slug","race_number")}; detail["field_size"]=len(book["outcomes"])
        scored.append({**detail,**candidate});paired.append({**detail,"baseline_log_loss":identity["log_loss"],"candidate_log_loss":candidate["log_loss"],
            "official_log_loss":official["log_loss"],"baseline_brier":identity["race_brier"],"candidate_brier":candidate["race_brier"],
            "official_brier":official["race_brier"],"baseline_rank":identity["winner_rank"],"official_rank":official["winner_rank"]})
    return scored,paired


def _period(scored:list[dict],paired:list[dict],period:str,protocol:dict[str,Any],seed:int)->dict[str,Any]:
    s=[row for row in scored if row["period"]==period];p=[row for row in paired if row["period"]==period]; metric=_summary(s)
    mean=lambda key:sum(row[key] for row in p)/len(p) if p else None
    baseline_ll=mean("baseline_log_loss"); official_ll=mean("official_log_loss"); baseline_brier=mean("baseline_brier"); official_brier=mean("official_brier")
    interval=paired_interval(p,int(protocol["resampling"]["repetitions"]),float(protocol["resampling"]["confidence_level"]),seed)
    baseline_top=sum(row["baseline_rank"]==1 for row in p)/len(p) if p else None; official_top=sum(row["official_rank"]==1 for row in p)/len(p) if p else None
    return {**metric,"identity_baseline_log_loss":baseline_ll,"official_baseline_log_loss":official_ll,
        "delta_vs_identity":metric["mean_log_loss"]-baseline_ll,"delta_vs_official":metric["mean_log_loss"]-official_ll,
        "race_brier_delta_vs_identity":metric["mean_race_brier"]-baseline_brier,"race_brier_delta_vs_official":metric["mean_race_brier"]-official_brier,
        "identity_top_1":baseline_top,"official_top_1":official_top,"top_1_delta_vs_identity":metric["top_1"]-baseline_top,
        "paired_interval_vs_identity":interval}


def run_stage3(store:RacingStore,protocol_path:Path)->dict[str,Any]:
    protocol=load_protocol(protocol_path);digest=protocol_hash(protocol);books=_books(store,digest);results={};seed=int(protocol["resampling"]["seed"])
    for offset,(name,strength) in enumerate(VARIANTS.items()):
        scored,paired=_evaluate(books,strength,protocol);periods={period:_period(scored,paired,period,protocol,seed+offset) for period in ("validation","historical_holdout")}
        validation=periods["validation"];holdout=periods["historical_holdout"];reasons=[]
        if validation["delta_vs_identity"]>=0: reasons.append("validation did not improve over identity-only time baseline")
        if validation["paired_interval_vs_identity"]["upper"]>=0: reasons.append("validation interval includes no improvement")
        if holdout["delta_vs_identity"]>=0: reasons.append("holdout direction did not agree")
        if validation["delta_vs_official"]>=0: reasons.append("validation did not beat the accepted official baseline")
        if holdout["delta_vs_official"]>=0: reasons.append("holdout did not beat the accepted official baseline")
        if validation["race_brier_delta_vs_identity"]>0 or holdout["race_brier_delta_vs_identity"]>0: reasons.append("race Brier worsened")
        results[name]={"strength":strength,"model":f"{FULL_MARGIN_MODEL}+blend-{strength:.2f}","periods":periods,
            "decision":"EVIDENCE_PASS" if not reasons else "FREEZE_OR_REVISE","reasons":reasons}
    return {"report_name":"stage-3-time-and-margin-isolation","protocol_hash":digest,"official_baseline":OFFICIAL_MODEL,"isolation_baseline":IDENTITY_MODEL,
        "full_margin_model":FULL_MARGIN_MODEL,"common_races":len(books),"candidates":results,
        "decision_policy":"margin must add to identity-only time model and beat the accepted official baseline; negative deltas favour candidate",
        "promotion_eligible":False,"promotion_blocker":"margin formula and historical holdout were previously inspected; prospective confirmation required",
        "next_branch_if_no_pass":"freeze margin and move to pace/sectional research","generated_at":utc_now()}


def render_markdown(report:dict[str,Any])->str:
    lines=["# Stage 3 — time and margin isolation","",f"Isolation baseline: `{report['isolation_baseline']}`","",
        "| Candidate | Validation Δ vs identity | Holdout Δ | Validation Brier Δ | Holdout Brier Δ | Validation interval | Decision |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |"]
    for name,item in report["candidates"].items():
        v=item["periods"]["validation"];h=item["periods"]["historical_holdout"];i=v["paired_interval_vs_identity"]
        lines.append(f"| {name} | {v['delta_vs_identity']:.6f} | {h['delta_vs_identity']:.6f} | {v['race_brier_delta_vs_identity']:.6f} | {h['race_brier_delta_vs_identity']:.6f} | [{i['lower']:.6f}, {i['upper']:.6f}] | {item['decision']} |")
    lines += ["","Negative differences favour the margin candidate.","",f"Promotion eligible: `{report['promotion_eligible']}` — {report['promotion_blocker']}",""]
    return "\n".join(lines)


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite");parser.add_argument("--protocol",type=Path,default=ROOT/"config"/"evaluation_protocol_v1.json");parser.add_argument("--output",type=Path)
    args=parser.parse_args();store=RacingStore(args.database)
    try:report=run_stage3(store,args.protocol)
    finally:store.close()
    rendered=json.dumps(report,indent=2,sort_keys=True)+"\n"
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(rendered);args.output.with_suffix(".md").write_text(render_markdown(report))
    else:print(rendered,end="")

if __name__=="__main__":main()
