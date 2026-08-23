"""Evaluate the V2 pace candidate without changing accepted ratings."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from .pace_shape import VERSION
from .storage import RacingStore, utc_now
from .v2_ratings import MODEL_VERSION

ROOT = Path(__file__).resolve().parents[1]


def _softmax(values: list[float]) -> list[float]:
    maximum=max(values); weights=[math.exp(value-maximum) for value in values]; total=sum(weights)
    return [value/total for value in weights]


def _mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def _metrics(examples: list[dict[str, Any]], field: str, temperature: float) -> dict[str, Any]:
    scored=[]
    for row in examples:
        probs=_softmax([value/temperature for value in row[field]])
        scored.append((-math.log(max(probs[row["winner"]],1e-12)),
                       sum((prob-(index==row["winner"]))**2 for index,prob in enumerate(probs)),
                       int(max(range(len(probs)),key=probs.__getitem__)==row["winner"])))
    return {"races":len(scored),"log_loss":_mean([row[0] for row in scored]),
            "race_brier":_mean([row[1] for row in scored]),"top_pick_strike_rate":_mean([row[2] for row in scored])}


def register_data_gaps(store: RacingStore) -> list[dict[str, Any]]:
    store.connection.executescript("""
    CREATE TABLE IF NOT EXISTS v2_sectional_data_gaps (
      race_id TEXT NOT NULL, runner_number INTEGER, subject TEXT NOT NULL,
      status TEXT NOT NULL, reason TEXT NOT NULL, checked_at TEXT NOT NULL,
      evidence_json TEXT NOT NULL, PRIMARY KEY(race_id,runner_number,subject)
    );""")
    checks=[
      ("2025-10-18|randwick|7",None,"2025 Everest","permanent_source_gap",
       "No matched official runner sectional rows exist in the stored Racing NSW/Racing.com source snapshot."),
      ("2026-04-04|randwick|8",15,"Sheza Alibi — 2026 Doncaster","permanent_runner_gap",
       "Winner is runner 15 in official results, but runner 15 is absent from the stored official sectional PDF."),
    ]
    output=[]
    for race_id,number,subject,status,reason in checks:
        count=store.connection.execute("""SELECT count(*) FROM runner_sectionals s JOIN v2_clean_races r
          ON r.source=s.source AND r.race_date=s.race_date AND r.track_slug=s.track_slug AND r.race_number=s.race_number
          WHERE r.race_id=? AND (? IS NULL OR s.runner_number=?)""",(race_id,number,number)).fetchone()[0]
        evidence={"stored_rows":count,"no_imputation":True,"recheck_required_if_source_archive_changes":True}
        store.connection.execute("INSERT OR REPLACE INTO v2_sectional_data_gaps VALUES (?,?,?,?,?,?,?)",
            (race_id,number,subject,status,reason,utc_now(),json.dumps(evidence,sort_keys=True)))
        output.append({"race_id":race_id,"runner_number":number,"subject":subject,"status":status,"stored_rows":count})
    return output


def evaluate(store: RacingStore, *, pace_version: str=VERSION) -> dict[str, Any]:
    rows=store.connection.execute("""SELECT r.race_date,
      CASE WHEN r.source LIKE '%nsw%' THEN 'NSW' ELSE 'VIC' END jurisdiction,r.track_slug,r.race_number,
      p.race_id,p.runner_number,p.horse_key,p.horse_name,p.performance_rating,c.finish_position,
      COALESCE(q.shadow_rating_adjustment,0) adjustment,q.pace_advantage,q.confidence,s.pace_label
      FROM v2_run_performances p JOIN v2_clean_races r USING(race_id)
      JOIN v2_clean_runner_results c USING(race_id,runner_number)
      LEFT JOIN v2_runner_pace_ratings q ON q.race_id=p.race_id AND q.runner_number=p.runner_number AND q.version=?
      LEFT JOIN v2_race_pace_shapes s ON s.race_id=p.race_id AND s.version=?
      WHERE p.model_version=? AND c.result_status='finished' AND c.finish_position IS NOT NULL
      ORDER BY r.race_date,p.race_id,p.runner_number""",(pace_version,pace_version,MODEL_VERSION)).fetchall()
    histories:dict[str,list[Any]]=defaultdict(list); next_pairs=[]
    for row in rows: histories[row["horse_key"]].append(row)
    for runs in histories.values():
        for current,nxt in zip(runs,runs[1:]):
            if current["pace_label"] is None: continue
            next_pairs.append({"jurisdiction":current["jurisdiction"],"label":current["pace_label"],
                "adjustment":float(current["adjustment"]),"base_error":abs(float(current["performance_rating"])-float(nxt["performance_rating"])),
                "adjusted_error":abs(float(current["performance_rating"])+float(current["adjustment"])-float(nxt["performance_rating"])),
                "next_change":float(nxt["performance_rating"])-float(current["performance_rating"]),
                "next_suitable":nxt["pace_advantage"] is None or float(nxt["pace_advantage"])>=-.25})
    def pair_summary(sample):
        return {"pairs":len(sample),"base_mae":_mean([x["base_error"] for x in sample]),
                "adjusted_mae":_mean([x["adjusted_error"] for x in sample]),
                "mae_change_adjusted_minus_base":(_mean([x["adjusted_error"] for x in sample])-_mean([x["base_error"] for x in sample])) if sample else None}
    disadvantaged=[x for x in next_pairs if x["adjustment"]>=.75 and x["next_suitable"]]
    neutral=[x for x in next_pairs if abs(x["adjustment"])<.25 and x["next_suitable"]]

    by_race:dict[str,list[Any]]=defaultdict(list)
    for row in rows: by_race[row["race_id"]].append(row)
    history_base:dict[str,list[float]]=defaultdict(list); history_adjusted:dict[str,list[float]]=defaultdict(list); examples=[]
    for race_id,runners in by_race.items():
        day=runners[0]["race_date"]
        eligible=[r for r in runners if history_base[r["horse_key"]]]
        if len(runners)>=4 and len(eligible)/len(runners)>=.60 and sum(r["finish_position"]==1 for r in runners)==1:
            base=[statistics.median(history_base[r["horse_key"]][-3:]) if history_base[r["horse_key"]] else 100.0 for r in runners]
            adjusted=[statistics.median(history_adjusted[r["horse_key"]][-3:]) if history_adjusted[r["horse_key"]] else 100.0 for r in runners]
            examples.append({"date":day,"jurisdiction":runners[0]["jurisdiction"],"winner":next(i for i,r in enumerate(runners) if r["finish_position"]==1),"base":base,"adjusted":adjusted})
        for r in runners:
            history_base[r["horse_key"]].append(float(r["performance_rating"]))
            history_adjusted[r["horse_key"]].append(float(r["performance_rating"])+float(r["adjustment"]))
    train=[x for x in examples if x["date"]<"2025-01-01"]
    test=[x for x in examples if x["date"]>="2025-01-01"]
    temps=(3.,5.,8.,10.,12.,15.)
    def fit(field):
        return min(temps,key=lambda t:_metrics(train,field,t)["log_loss"]) if train else 10.
    fitted={field:fit(field) for field in ("base","adjusted")}
    prediction={"training_races":len(train),"test_races":len(test),"temperatures":fitted,
                "overall":{field:_metrics(test,field,fitted[field]) for field in fitted},"jurisdiction":{}}
    for jurisdiction in ("NSW","VIC"):
        sample=[x for x in test if x["jurisdiction"]==jurisdiction]
        prediction["jurisdiction"][jurisdiction]={field:_metrics(sample,field,fitted[field]) for field in fitted}
    movements=sorted(({"horse":r["horse_name"],"race_id":r["race_id"],"adjustment":float(r["adjustment"]),"label":r["pace_label"]}
                      for r in rows if r["pace_label"] is not None),key=lambda x:abs(x["adjustment"]),reverse=True)[:30]
    gaps=register_data_gaps(store); store.connection.commit()
    return {"pace_version":pace_version,"status":"shadow_not_promoted","next_start":pair_summary(next_pairs),
      "next_start_by_jurisdiction":{j:pair_summary([x for x in next_pairs if x["jurisdiction"]==j]) for j in ("NSW","VIC")},
      "disadvantaged_response":{"definition":"adjustment >= 0.75 and next run not pace-disadvantaged",
        "sample":len(disadvantaged),"mean_next_rating_change":_mean([x["next_change"] for x in disadvantaged]),
        "neutral_control_sample":len(neutral),"neutral_mean_next_rating_change":_mean([x["next_change"] for x in neutral])},
      "chronological_prediction_ablation":prediction,"largest_shadow_movements":movements,"named_data_gaps":gaps}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite"); parser.add_argument("--output",type=Path)
    args=parser.parse_args(); store=RacingStore(args.database)
    try: report=evaluate(store)
    finally: store.close()
    rendered=json.dumps(report,indent=2,sort_keys=True)+"\n"
    if args.output: args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(rendered)
    else: print(rendered,end="")


if __name__=="__main__": main()
