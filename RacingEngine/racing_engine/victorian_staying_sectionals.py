"""Source-honest two-phase fallback for Victorian staying sectionals."""
from __future__ import annotations
import argparse,json,math,statistics
from collections import defaultdict
from pathlib import Path
from .storage import RacingStore,utc_now
from .v2_ratings import MODEL_VERSION

ROOT=Path(__file__).resolve().parents[1];VERSION="vic-staying-two-phase-v1.0-shadow"
def _mean(v):return statistics.mean(v) if v else None
def _median(v):return statistics.median(v) if v else None
def _clip(v,a,b):return max(a,min(b,v))
def _softmax(v):
 m=max(v);w=[math.exp(x-m) for x in v];s=sum(w);return[x/s for x in w]
def _fit(pairs):
 if len(pairs)<50:return {"coefficient":0.0,"pairs":len(pairs),"status":"insufficient_sample_frozen_zero"}
 best=min(((_mean([abs(target-c*signal) for signal,target in pairs])+.002*c,c) for c in [x/10 for x in range(16)]))
 return {"coefficient":best[1],"pairs":len(pairs),"status":"fitted"}
def _paired_ci(values):
 if len(values)<2:return {"mean":_mean(values),"lower_95":None,"upper_95":None,"n":len(values)}
 mean=_mean(values);se=statistics.stdev(values)/math.sqrt(len(values))
 return {"mean":mean,"lower_95":mean-1.96*se,"upper_95":mean+1.96*se,"n":len(values)}

def schema(store):
 store.connection.executescript("""CREATE TABLE IF NOT EXISTS v2_vic_staying_two_phase(
 version TEXT NOT NULL,race_id TEXT NOT NULL,runner_number INTEGER NOT NULL,horse_key TEXT NOT NULL,
 opening_speed_mps REAL NOT NULL,final400_speed_mps REAL NOT NULL,opening_ratio REAL NOT NULL,final_ratio REAL NOT NULL,
 optimal_opening_ratio REAL NOT NULL,optimal_final_ratio REAL NOT NULL,front_exposure REAL NOT NULL,
 compensation_signal REAL NOT NULL,confidence REAL NOT NULL,detail_json TEXT NOT NULL,created_at TEXT NOT NULL,
 PRIMARY KEY(version,race_id,runner_number));""")

def build(store):
 schema(store);store.connection.execute("DELETE FROM v2_vic_staying_two_phase WHERE version=?",(VERSION,));now=utc_now();history=[];built=0
 races=store.connection.execute("""SELECT * FROM v2_clean_races WHERE source='racing-com-rv-authorised' AND distance_metres>2000 ORDER BY race_date,race_id""").fetchall()
 for race in races:
  runners=store.connection.execute("""SELECT * FROM v2_clean_runner_results WHERE race_id=? AND result_status='finished' AND finish_position IS NOT NULL""",(race["race_id"],)).fetchall();parsed=[]
  for runner in runners:
   rows={x["marker_metres"]:x for x in store.connection.execute("""SELECT marker_metres,section_seconds,position_at_marker FROM runner_sectionals
    WHERE source=? AND race_date=? AND track_slug=? AND race_number=? AND runner_number=?""",(race["source"],race["race_date"],race["track_slug"],race["race_number"],runner["runner_number"]))}
   if 800 not in rows or 0 not in rows:continue
   opening_metres=int(race["distance_metres"])-800;opening=opening_metres/float(rows[800]["section_seconds"]);final=400/float(rows[0]["section_seconds"])
   overall=(opening_metres+400)/(float(rows[800]["section_seconds"])+float(rows[0]["section_seconds"]));parsed.append((runner,opening/overall,final/overall,opening,final,rows[800]["position_at_marker"]))
  if len(history)>=5:
   opt_open=_median([x[0] for x in history[-50:]]);opt_final=_median([x[1] for x in history[-50:]])
   mid=(len(runners)+1)/2
   for runner,opening_ratio,final_ratio,opening,final,pos in parsed:
    exposure=_clip((mid-float(pos or mid))/max(1,mid-1),0,1);early=max(0,opening_ratio-opt_open);fade=max(0,opt_final-final_ratio)
    signal=100*(early*(.5+exposure)+fade*.5);confidence=min(.80,.30+.04*min(10,len(history)))
    detail={"source":"stored official RV aggregate phases","middle_phase_excluded":True,"richer_200m_csv_preferred":True,"strictly_prior_profile":True,"profile_sample":len(history)}
    store.connection.execute("INSERT INTO v2_vic_staying_two_phase VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(VERSION,race["race_id"],runner["runner_number"],runner["horse_key"],opening,final,opening_ratio,final_ratio,opt_open,opt_final,exposure,signal,confidence,json.dumps(detail,sort_keys=True),now));built+=1
  winner=next((x for x in parsed if x[0]["finish_position"]==1),None)
  if winner:history.append((winner[1],winner[2]))
 store.connection.commit();return {"version":VERSION,"races":len(races),"runners":built,"accepted_rating_changed":False}

def evaluate(store):
 rows=[dict(x) for x in store.connection.execute("""SELECT x.*,r.race_date,c.finish_position,p.performance_rating FROM v2_vic_staying_two_phase x
 JOIN v2_clean_races r USING(race_id) JOIN v2_clean_runner_results c USING(race_id,runner_number) JOIN v2_run_performances p USING(race_id,runner_number)
 WHERE x.version=? AND p.model_version=? ORDER BY r.race_date,r.race_id""",(VERSION,MODEL_VERSION))]
 horses=defaultdict(list)
 for x in rows:horses[x["horse_key"]].append(x)
 pairs=[]
 for runs in horses.values():
  for cur,nxt in zip(runs,runs[1:]):pairs.append((cur,float(nxt["performance_rating"])-float(cur["performance_rating"])))
 fit=_fit([(float(x["compensation_signal"]),target) for x,target in pairs if x["race_date"]<"2025-01-01"]);coef=fit["coefficient"]
 test=[(x,target) for x,target in pairs if x["race_date"]>="2025-01-01"]
 base=_mean([abs(t) for _,t in test]);adjusted=_mean([abs(t-_clip(coef*float(x["compensation_signal"]),-3,3)) for x,t in test])
 byrace=defaultdict(list)
 for x in rows:byrace[x["race_id"]].append(x)
 histories={"base":defaultdict(list),"adjusted":defaultdict(list)};examples=[]
 for _,runners in byrace.items():
  if len(runners)>=4 and sum(x["finish_position"]==1 for x in runners)==1 and sum(bool(histories["base"][x["horse_key"]]) for x in runners)/len(runners)>=.6:
   examples.append({"date":runners[0]["race_date"],"winner":next(i for i,x in enumerate(runners) if x["finish_position"]==1),
    "base":[statistics.median(histories["base"][x["horse_key"]][-3:]) if histories["base"][x["horse_key"]] else 100 for x in runners],
    "adjusted":[statistics.median(histories["adjusted"][x["horse_key"]][-3:]) if histories["adjusted"][x["horse_key"]] else 100 for x in runners]})
  for x in runners:
   histories["base"][x["horse_key"]].append(float(x["performance_rating"]));histories["adjusted"][x["horse_key"]].append(float(x["performance_rating"])+_clip(coef*float(x["compensation_signal"]),-3,3))
 train=[x for x in examples if x["date"]<"2025-01-01"];hold=[x for x in examples if x["date"]>="2025-01-01"]
 def loss(sample,name,temp):return _mean([-math.log(max(_softmax([v/temp for v in x[name]])[x["winner"]],1e-12)) for x in sample])
 temps={n:min((3,5,8,10,12,15),key=lambda t:loss(train,n,t)) for n in ("base","adjusted")}
 ranking={n:{"races":len(hold),"log_loss":loss(hold,n,temps[n]),"temperature":temps[n]} for n in temps}
 next_diffs=[abs(t-_clip(coef*float(x["compensation_signal"]),-3,3))-abs(t) for x,t in test]
 rank_diffs=[]
 for x in hold:
  base_loss=-math.log(max(_softmax([v/temps["base"] for v in x["base"]])[x["winner"]],1e-12))
  adjusted_loss=-math.log(max(_softmax([v/temps["adjusted"] for v in x["adjusted"]])[x["winner"]],1e-12))
  rank_diffs.append(adjusted_loss-base_loss)
 uncertainty={"next_start_mae_difference":_paired_ci(next_diffs),"race_log_loss_difference":_paired_ci(rank_diffs)}
 basic_pass=fit["status"]=="fitted" and adjusted<base and ranking["adjusted"]["log_loss"]<ranking["base"]["log_loss"]
 audit_pass=basic_pass and uncertainty["next_start_mae_difference"]["upper_95"]<0 and uncertainty["race_log_loss_difference"]["upper_95"]<0
 return {"version":VERSION,"fit":fit,"next_start":{"pairs":len(test),"base_mae":base,"adjusted_mae":adjusted},"ranking":ranking,
  "paired_uncertainty":uncertainty,"basic_directional_pass":basic_pass,"audit_pass":audit_pass,"promote":audit_pass,"accepted_rating_changed":False}

def main():
 p=argparse.ArgumentParser();p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite");p.add_argument("--output",type=Path);a=p.parse_args();s=RacingStore(a.database)
 try:r={"build":build(s),"evaluation":evaluate(s)}
 finally:s.close()
 out=json.dumps(r,indent=2,sort_keys=True)+"\n"
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(out)
 else:print(out,end="")
if __name__=="__main__":main()
