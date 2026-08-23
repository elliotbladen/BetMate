"""Immutable forward ledger for frozen V2.3 sectional coefficients."""
from __future__ import annotations
import argparse,hashlib,json,math,sqlite3,statistics
from collections import defaultdict
from pathlib import Path
from .energy_sectionals import VERSION as ENERGY_VERSION,RICH_VERSION
from .v2_ratings import MODEL_VERSION

ROOT=Path(__file__).resolve().parents[1]
FREEZE_VERSION="energy-sectionals-v2.3-frozen-2026-08-23"
TRAINING_CUTOFF="2026-08-15"
FROZEN_AT="2026-08-23"
TEMPERATURE=15.0
COEFFICIENTS={
 "NSW":{"sprint":{"achievement":.1,"compensation":.1},"middle":{"achievement":0.,"compensation":0.}},
 "VIC":{"sprint":{"achievement":0.,"compensation":.4},"middle":{"achievement":0.,"compensation":.8}},
}
RICH_COEFFICIENTS={
 "NSW":{"sprint":{"achievement":.1,"compensation":.1},"middle":{"achievement":0.,"compensation":0.},"staying":{"achievement":0.,"compensation":0.}},
 "VIC":{"sprint":{"achievement":0.,"compensation":.3},"middle":{"achievement":0.,"compensation":.5},"staying":{"achievement":.1,"compensation":.4}},
}

def _clip(v,a,b):return max(a,min(b,v))
def _softmax(values):
 m=max(values);weights=[math.exp(v-m) for v in values];total=sum(weights);return [v/total for v in weights]
def _adjust(row,coefficients=COEFFICIENTS):
 c=coefficients.get(row["jurisdiction"],{}).get(row["distance_band"])
 if c is None:return None
 return _clip(c["achievement"]*float(row["achievement_signal"])+c["compensation"]*float(row["compensation_signal"]),-3,3)
def _schema(connection):
 connection.executescript("""CREATE TABLE IF NOT EXISTS v2_sectional_forward_ledger(
 freeze_version TEXT NOT NULL,coefficient_hash TEXT NOT NULL,frozen_at TEXT NOT NULL,training_cutoff TEXT NOT NULL,
 race_date TEXT NOT NULL,race_id TEXT NOT NULL,runner_number INTEGER NOT NULL,horse_key TEXT NOT NULL,
 jurisdiction TEXT NOT NULL,distance_band TEXT NOT NULL,base_prediction REAL,adjusted_prediction REAL,
 frozen_adjustment REAL NOT NULL,finish_position INTEGER,source_energy_version TEXT NOT NULL,status TEXT NOT NULL,
 evidence_json TEXT NOT NULL,scored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(freeze_version,race_id,runner_number));""")

def score(history_path:Path,forward_path:Path,candidate:str="v23")->dict:
 history=sqlite3.connect(history_path);history.row_factory=sqlite3.Row
 forward=sqlite3.connect(forward_path);forward.row_factory=sqlite3.Row
 _schema(history)
 coefficients=RICH_COEFFICIENTS if candidate=="v24" else COEFFICIENTS
 energy_version=RICH_VERSION if candidate=="v24" else ENERGY_VERSION
 freeze_version="energy-sectionals-v2.4-vic-200m-frozen-2026-08-23" if candidate=="v24" else FREEZE_VERSION
 coefficient_json=json.dumps(coefficients,sort_keys=True,separators=(",",":"))
 coefficient_hash=hashlib.sha256(coefficient_json.encode()).hexdigest()
 histories=defaultdict(list)
 rows=history.execute("""SELECT e.*,p.performance_rating,r.race_date FROM v2_runner_energy_sectionals e
 JOIN v2_run_performances p USING(race_id,runner_number) JOIN v2_clean_races r USING(race_id)
 WHERE e.version=? AND p.model_version=? AND r.race_date<=? ORDER BY r.race_date,r.race_id""",
 (energy_version,MODEL_VERSION,TRAINING_CUTOFF)).fetchall()
 for row in rows:
  adjustment=_adjust(row,coefficients)
  if adjustment is not None:histories[(row["horse_key"],row["distance_band"])].append((float(row["performance_rating"]),adjustment))
 candidates=forward.execute("""SELECT e.*,r.race_date,c.finish_position FROM v2_runner_energy_sectionals e
 JOIN v2_clean_races r USING(race_id) JOIN v2_clean_runner_results c USING(race_id,runner_number)
 WHERE e.version=? AND r.race_date>? ORDER BY r.race_date,r.race_id,e.runner_number""",(energy_version,TRAINING_CUTOFF)).fetchall()
 race_rows=defaultdict(list);inserted=0;existing=0
 for row in candidates:
  adjustment=_adjust(row,coefficients)
  if adjustment is None:continue
  prior=histories.get((row["horse_key"],row["distance_band"]),[])
  base=statistics.median([x[0] for x in prior[-3:]]) if prior else None
  adjusted=statistics.median([x[0]+x[1] for x in prior[-3:]]) if prior else None
  evidence={"coefficients":coefficients[row["jurisdiction"]][row["distance_band"]],"coefficient_json":coefficient_json,
   "prior_runs":len(prior),"prospective_style_holdout":True,"live_post_freeze":False,
   "reason":"race was unseen by the model and occurred after the frozen training cutoff, but before candidate_frozen_at"}
  values=(freeze_version,coefficient_hash,FROZEN_AT,TRAINING_CUTOFF,row["race_date"],row["race_id"],row["runner_number"],row["horse_key"],
   row["jurisdiction"],row["distance_band"],base,adjusted,adjustment,row["finish_position"],energy_version,"scored",json.dumps(evidence,sort_keys=True))
  before=history.total_changes
  history.execute("""INSERT OR IGNORE INTO v2_sectional_forward_ledger(
   freeze_version,coefficient_hash,frozen_at,training_cutoff,race_date,race_id,runner_number,horse_key,jurisdiction,distance_band,
   base_prediction,adjusted_prediction,frozen_adjustment,finish_position,source_energy_version,status,evidence_json)
   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",values)
  if history.total_changes>before:inserted+=1
  else:existing+=1
  race_rows[row["race_id"]].append({"base":base,"adjusted":adjusted,"winner":row["finish_position"]==1,"jurisdiction":row["jurisdiction"],"band":row["distance_band"]})
 history.commit()
 losses=[];skipped=defaultdict(int)
 for rid,runners in race_rows.items():
  if sum(x["winner"] for x in runners)!=1:skipped["no_unique_winner"]+=1;continue
  available=[x for x in runners if x["base"] is not None]
  if len(available)/len(runners)<.6:skipped["prior_coverage_below_60_percent"]+=1;continue
  # Keep the comparison on the same covered field; missing histories are not manufactured.
  if not any(x["winner"] for x in available):skipped["winner_missing_prior_history"]+=1;continue
  winner=next(i for i,x in enumerate(available) if x["winner"])
  base=-math.log(max(_softmax([x["base"]/TEMPERATURE for x in available])[winner],1e-12))
  adjusted=-math.log(max(_softmax([x["adjusted"]/TEMPERATURE for x in available])[winner],1e-12))
  losses.append({"race_id":rid,"jurisdiction":available[0]["jurisdiction"],"band":available[0]["band"],"base":base,"adjusted":adjusted,"difference":adjusted-base})
 history.close();forward.close()
 by=lambda key,value:[x for x in losses if x[key]==value]
 mean=lambda values:statistics.mean(values) if values else None
 return {"freeze_version":freeze_version,"coefficient_hash":coefficient_hash,"frozen_at":FROZEN_AT,"training_cutoff":TRAINING_CUTOFF,
  "interpretation":"prospective-style unseen holdout; not live post-freeze","candidate_rows":len(candidates),"inserted":inserted,"already_present":existing,
  "race_log_loss":{"races":len(losses),"base":mean([x["base"] for x in losses]),"adjusted":mean([x["adjusted"] for x in losses]),
   "difference":mean([x["difference"] for x in losses]),"by_jurisdiction":{j:{"races":len(by("jurisdiction",j)),"difference":mean([x["difference"] for x in by("jurisdiction",j)])} for j in ("NSW","VIC")},
   "by_band":{b:{"races":len(by("band",b)),"difference":mean([x["difference"] for x in by("band",b)])} for b in ("sprint","middle")}},
  "skipped_races":dict(skipped),"next_start_mae":"pending future starts","audit_pass":False,
  "audit_reason":"One meeting per jurisdiction is too small, the combined ranking result is worse, and next-start outcomes are pending."}

def main():
 p=argparse.ArgumentParser();p.add_argument("--history-database",type=Path,default=ROOT/"data"/"racing_engine.sqlite");p.add_argument("--forward-database",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--candidate",choices=("v23","v24"),default="v23");a=p.parse_args()
 result=score(a.history_database,a.forward_database,a.candidate);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":main()
