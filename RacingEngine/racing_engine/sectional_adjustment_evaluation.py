"""Frozen multi-gate evaluation for Step 2 sectional adjustment V2.2."""
from __future__ import annotations
import argparse,json,math,statistics
from collections import defaultdict
from pathlib import Path
from typing import Any
from .sectional_adjustment import VERSION
from .storage import RacingStore
from .v2_ratings import MODEL_VERSION

ROOT=Path(__file__).resolve().parents[1]
VARIANTS={"base":(),"achievement_only":("achievement",),"trip_only":("trip",),
          "steward_only":("steward",),"combined":("achievement","trip","steward")}

def _softmax(v):
    m=max(v); w=[math.exp(x-m) for x in v]; s=sum(w); return [x/s for x in w]
def _mean(v): return statistics.mean(v) if v else None
def _features(row): return {"achievement":float(row["achievement_signal"]),"trip":float(row["trip_signal"]),"steward":float(row["steward_signal"])}

def _fit(train,features):
    if not features:return {name:0.0 for name in ("achievement","trip","steward")}
    grids={name:[x/10 for x in range(16)] for name in features}
    if "steward" in features: grids["steward"]=[0,.25,.5,.75,1.0]
    candidates=[{}]
    for name in features:candidates=[{**old,name:value} for old in candidates for value in grids[name]]
    best=None
    for coef in candidates:
        errors=[abs(target-sum(coef.get(name,0)*row[name] for name in features)) for row,target in train]
        objective=_mean(errors)+.002*sum(coef.values())
        value=(objective,tuple(coef.get(name,0) for name in ("achievement","trip","steward")),coef)
        if best is None or value<best:best=value
    return {name:best[2].get(name,0.0) for name in ("achievement","trip","steward")}

def _adjust(row,coef):return max(-3,min(3,sum(coef[name]*row[name] for name in coef)))

def evaluate(store:RacingStore)->dict[str,Any]:
    raw=store.connection.execute("""SELECT r.race_date,r.race_id,c.runner_number,c.horse_key,c.horse_name,c.finish_position,
      x.jurisdiction,x.achievement_signal,x.trip_signal,x.steward_signal,p.performance_rating
      FROM v2_runner_sectional_components x JOIN v2_clean_races r USING(race_id)
      JOIN v2_clean_runner_results c USING(race_id,runner_number)
      JOIN v2_run_performances p USING(race_id,runner_number)
      WHERE x.version=? AND p.model_version=? ORDER BY r.race_date,r.race_id,c.runner_number""",(VERSION,MODEL_VERSION)).fetchall()
    rows=[{**dict(r),**_features(r),"performance":float(r["performance_rating"])} for r in raw]
    horses=defaultdict(list)
    for row in rows:horses[row["horse_key"]].append(row)
    pairs=[]
    for runs in horses.values():
      for current,nxt in zip(runs,runs[1:]):pairs.append((current,nxt["performance"]-current["performance"],nxt))
    coefficients={}
    for variant,features in VARIANTS.items():
      coefficients[variant]={}
      for jurisdiction in ("NSW","VIC"):
        train=[(row,target) for row,target,_ in pairs if row["jurisdiction"]==jurisdiction and row["race_date"]<"2025-01-01"]
        coefficients[variant][jurisdiction]=_fit(train,features)

    next_start={}
    for variant in VARIANTS:
      sample=[]
      for row,target,nxt in pairs:
        if row["race_date"]<"2025-01-01":continue
        adjustment=_adjust(row,coefficients[variant][row["jurisdiction"]]); sample.append((row["jurisdiction"],abs(target-adjustment),target,adjustment))
      next_start[variant]={"overall":{"pairs":len(sample),"mae":_mean([x[1] for x in sample])},
        "jurisdiction":{j:{"pairs":sum(x[0]==j for x in sample),"mae":_mean([x[1] for x in sample if x[0]==j])} for j in ("NSW","VIC")}}

    by_race=defaultdict(list)
    for row in rows:by_race[row["race_id"]].append(row)
    history={variant:defaultdict(list) for variant in VARIANTS}; examples=[]
    for race_id,runners in by_race.items():
      if len(runners)>=4 and sum(r["finish_position"]==1 for r in runners)==1:
        coverage=sum(bool(history["base"][r["horse_key"]]) for r in runners)/len(runners)
        if coverage>=.60:
          example={"date":runners[0]["race_date"],"jurisdiction":runners[0]["jurisdiction"],
                   "winner":next(i for i,r in enumerate(runners) if r["finish_position"]==1)}
          for variant in VARIANTS:example[variant]=[statistics.median(history[variant][r["horse_key"]][-3:]) if history[variant][r["horse_key"]] else 100 for r in runners]
          examples.append(example)
      for r in runners:
        for variant in VARIANTS:
          value=r["performance"]+_adjust(r,coefficients[variant][r["jurisdiction"]]);history[variant][r["horse_key"]].append(value)
    train=[x for x in examples if x["date"]<"2025-01-01"];test=[x for x in examples if x["date"]>="2025-01-01"]
    temps={}
    for variant in VARIANTS:
      def loss(t):return _mean([-math.log(max(_softmax([v/t for v in x[variant]])[x["winner"]],1e-12)) for x in train])
      temps[variant]=min((3,5,8,10,12,15),key=loss)
    def metrics(sample,variant):
      scored=[]
      for x in sample:
        probs=_softmax([v/temps[variant] for v in x[variant]]);w=x["winner"]
        scored.append((-math.log(max(probs[w],1e-12)),sum((p-(i==w))**2 for i,p in enumerate(probs)),int(max(range(len(probs)),key=probs.__getitem__)==w)))
      return {"races":len(scored),"log_loss":_mean([x[0] for x in scored]),"brier":_mean([x[1] for x in scored]),"strike":_mean([x[2] for x in scored])}
    ranking={variant:{"temperature":temps[variant],"overall":metrics(test,variant),
      "jurisdiction":{j:metrics([x for x in test if x["jurisdiction"]==j],variant) for j in ("NSW","VIC")}} for variant in VARIANTS}
    base=ranking["base"]; decisions={}
    for variant in VARIANTS:
      if variant=="base":continue
      overall=ranking[variant]["overall"]["log_loss"]<base["overall"]["log_loss"]
      rank_jurisdictions=all(ranking[variant]["jurisdiction"][j]["log_loss"]<base["jurisdiction"][j]["log_loss"] for j in ("NSW","VIC"))
      mae=next_start[variant]["overall"]["mae"]<next_start["base"]["overall"]["mae"]
      mae_jurisdictions=all(next_start[variant]["jurisdiction"][j]["mae"]<next_start["base"]["jurisdiction"][j]["mae"] for j in ("NSW","VIC"))
      decisions[variant]={"overall_log_loss_improved":overall,"both_jurisdictions_log_loss_improved":rank_jurisdictions,
        "next_start_mae_improved":mae,"both_jurisdictions_next_start_mae_improved":mae_jurisdictions,
        "promote":overall and rank_jurisdictions and mae and mae_jurisdictions}
    return {"version":VERSION,"fit_window":"before 2025-01-01","test_window":"2025 onward","coefficients":coefficients,
      "next_start":next_start,"ranking":ranking,"promotion_decisions":decisions,"accepted_rating_changed":False}

def main():
 p=argparse.ArgumentParser();p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite");p.add_argument("--output",type=Path);a=p.parse_args();s=RacingStore(a.database)
 try:r=evaluate(s)
 finally:s.close()
 rendered=json.dumps(r,indent=2,sort_keys=True)+"\n"
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered)
 else:print(rendered,end="")
if __name__=="__main__":main()
