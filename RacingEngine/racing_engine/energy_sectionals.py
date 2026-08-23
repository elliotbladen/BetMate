"""V2.3 distance-specific velocity/energy sectional experiment (shadow only)."""
from __future__ import annotations
import argparse,json,math,statistics
from collections import defaultdict
from pathlib import Path
from typing import Any
from .pace_shape import SOURCES
from .storage import RacingStore,utc_now
from .v2_ratings import MODEL_VERSION

ROOT=Path(__file__).resolve().parents[1]; VERSION="energy-sectionals-v2.3-shadow"
RICH_VERSION="energy-sectionals-v2.4-vic-200m-shadow"
HIER_VERSION="energy-sectionals-v2.5-hierarchical-shadow"
PHASES=("early","middle","late")
def _mean(v):return statistics.mean(v) if v else None
def _median(v):return statistics.median(v) if v else None
def _clip(v,a,b):return max(a,min(b,v))
def _band(d):return "sprint" if d<=1400 else "middle" if d<=2000 else "staying"
def _condition(v):
 v=(v or "unknown").lower();return "heavy" if "heavy" in v else "soft" if "soft" in v else "good" if "good" in v else "firm" if "firm" in v else "other"

def schema(store):
 store.connection.executescript("""CREATE TABLE IF NOT EXISTS v2_runner_energy_sectionals(
 version TEXT NOT NULL,race_id TEXT NOT NULL,runner_number INTEGER NOT NULL,horse_key TEXT NOT NULL,
 jurisdiction TEXT NOT NULL,distance_band TEXT NOT NULL,resolution TEXT NOT NULL,segments INTEGER NOT NULL,
 early_speed_mps REAL,middle_speed_mps REAL,late_speed_mps REAL,overall_speed_mps REAL,
 optimal_early_ratio REAL,optimal_middle_ratio REAL,optimal_late_ratio REAL,
 efficiency_cost REAL NOT NULL,early_energy_cost REAL NOT NULL,late_deceleration_cost REAL NOT NULL,
 late_burst_ability REAL NOT NULL,front_exposure REAL NOT NULL,compensation_signal REAL NOT NULL,
 achievement_signal REAL NOT NULL,confidence REAL NOT NULL,detail_json TEXT NOT NULL,created_at TEXT NOT NULL,
 PRIMARY KEY(version,race_id,runner_number));""")

def _segments(source,distance,rows):
 values=[]
 for row in rows:
  marker=int(row["marker_metres"]);seconds=row["section_seconds"]
  if not seconds or seconds<=0:continue
  if "nsw" in source: metres=200
  elif marker==800:metres=distance-800
  else:metres=400
  if metres<=0:continue
  # Progress is measured at the segment midpoint from the start.
  progress=(distance-marker-metres/2)/distance
  values.append((progress,metres/float(seconds),marker,row["position_at_marker"]))
 return sorted(values)
def _rich_segments(distance,rows):
 values=[];previous=distance
 for row in sorted(rows,key=lambda x:int(x["marker_metres"]),reverse=True):
  marker=int(row["marker_metres"]);metres=previous-marker;seconds=row["section_seconds"]
  if metres<=0 or not seconds or seconds<=0:continue
  progress=(distance-marker-metres/2)/distance
  values.append((progress,metres/float(seconds),marker,row["position_at_marker"]));previous=marker
 return values

def _phase_speeds(segments):
 buckets={p:[] for p in PHASES}
 for progress,speed,_,_ in segments:buckets["early" if progress<1/3 else "middle" if progress<2/3 else "late"].append(speed)
 return {p:_mean(buckets[p]) for p in PHASES}

def _fit(train,features):
 if len(train)<50:return {features[0]:0,features[1]:0,"training_pairs":len(train),"status":"insufficient_sample_frozen_zero"}
 grid=[x/10 for x in range(16)];best=None
 for a in grid:
  for c in grid:
   errors=[abs(target-(a*row[features[0]]+c*row[features[1]])) for row,target in train]
   candidate=(_mean(errors)+.002*(a+c),a,c)
   if best is None or candidate<best:best=candidate
 return {features[0]:best[1],features[1]:best[2],"training_pairs":len(train),"status":"fitted"}

def build(store:RacingStore,version:str=VERSION,prefer_vic_200m:bool=False,hierarchical:bool=False)->dict[str,Any]:
 schema(store);store.connection.execute("DELETE FROM v2_runner_energy_sectionals WHERE version=?",(version,));now=utc_now()
 races=store.connection.execute("""SELECT r.*,rr.track_condition FROM v2_clean_races r LEFT JOIN race_results rr
 ON rr.source=r.source AND rr.race_date=r.race_date AND rr.track_slug=r.track_slug AND rr.race_number=r.race_number
 WHERE r.source IN (?,?) ORDER BY r.race_date,r.track_slug,r.race_number""",tuple(sorted(SOURCES))).fetchall()
 # Optimal distributions are learned only from earlier winners, separately by
 # source, distance band and going. Sparse groups shrink to source/band history.
 exact=defaultdict(list);broad=defaultdict(list);built=[];skipped=defaultdict(int)
 for race in races:
  distance=int(race["distance_metres"] or 0);band=_band(distance);going=_condition(race["track_condition"]);jur="NSW" if "nsw" in race["source"] else "VIC"
  runners=store.connection.execute("""SELECT * FROM v2_clean_runner_results WHERE race_id=? AND result_status='finished' AND finish_position IS NOT NULL""",(race["race_id"],)).fetchall();race_rows=[]
  for runner in runners:
   rich=prefer_vic_200m and jur=="VIC"
   if rich:
    raw=store.connection.execute("""SELECT marker_metres,section_seconds,position_at_marker FROM v2_vic_200m_sectionals
     WHERE version='racing-com-vic-200m-v1' AND race_id=? AND runner_number=? ORDER BY marker_metres DESC""",(race["race_id"],runner["runner_number"])).fetchall()
    segments=_rich_segments(distance,raw)
   else:
    raw=store.connection.execute("""SELECT marker_metres,section_seconds,position_at_marker FROM runner_sectionals
     WHERE source=? AND race_date=? AND track_slug=? AND race_number=? AND runner_number=? ORDER BY marker_metres DESC""",
     (race["source"],race["race_date"],race["track_slug"],race["race_number"],runner["runner_number"])).fetchall()
    segments=_segments(race["source"],distance,raw)
   phases=_phase_speeds(segments)
   if any(phases[p] is None for p in PHASES):skipped["incomplete_curve"]+=1;continue
   overall=sum(x[1] for x in segments)/len(segments);ratios={p:phases[p]/overall for p in PHASES}
   race_rows.append({"runner":runner,"segments":segments,"phases":phases,"overall":overall,"ratios":ratios})
  key=((race["source"],race["track_slug"],distance,going) if hierarchical else (race["source"],band,going));fallback=(race["source"],band);minimum=5 if band=="staying" else 10
  sample=exact[key] if len(exact[key])>=minimum else broad[fallback]
  if len(sample)>=minimum:
   optimal={p:_median([x[p] for x in sample[-100:]]) for p in PHASES}
   for item in race_rows:
    ratios=item["ratios"];positions=[x[3] for x in item["segments"] if x[3] is not None and x[0]<.55]
    field_mid=(len(runners)+1)/2;mean_position=_mean([float(x) for x in positions]) or field_mid
    front=_clip((field_mid-mean_position)/max(1,field_mid-1),0,1)
    early_cost=max(0,ratios["early"]-optimal["early"])
    decel=max(0,optimal["late"]-ratios["late"])
    burst=max(0,ratios["late"]-optimal["late"])
    efficiency=sum(abs(ratios[p]-optimal[p]) for p in PHASES)
    # Front exposure magnifies excess early energy; late deceleration provides
    # evidence that the expenditure was paid for rather than merely tactical.
    compensation=100*(early_cost*(.5+front)+decel*.5)
    achievement=100*burst*(1-max(0,optimal["early"]-ratios["early"]))
    confidence=min(.95,.35+.05*min(10,len(sample))+.02*min(5,len(item["segments"])))
    detail={"profile_is_strictly_prior":True,"profile_sample":len(sample),"going_bucket":going,
      "phase_ratios":ratios,"minimum_profile_sample":minimum,"sparse_staying_profile":"five prior winners with lower confidence" if band=="staying" else None,
      "source_resolution":"200m intervals" if jur=="NSW" or rich else "three variable-length phases","profile_level":"track_distance_going_with_source_band_fallback" if hierarchical else "source_band_going",
      "drafting_status":"front exposure proxy only; cover not directly observed"}
    values=(version,race["race_id"],item["runner"]["runner_number"],item["runner"]["horse_key"],jur,band,
      "200m" if jur=="NSW" or rich else "three_phase",len(item["segments"]),item["phases"]["early"],item["phases"]["middle"],item["phases"]["late"],item["overall"],
      optimal["early"],optimal["middle"],optimal["late"],efficiency,early_cost*100,decel*100,achievement,front,compensation,achievement,confidence,json.dumps(detail,sort_keys=True),now)
    store.connection.execute("INSERT INTO v2_runner_energy_sectionals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",values);built.append(values)
  winner=next((x for x in race_rows if x["runner"]["finish_position"]==1),None)
  if winner:exact[key].append(winner["ratios"]);broad[fallback].append(winner["ratios"])
 store.connection.commit();return {"version":version,"runners":len(built),"races":len(set(x[1] for x in built)),"skipped":dict(skipped),"accepted_rating_changed":False}

def _softmax(v):
 m=max(v);w=[math.exp(x-m) for x in v];s=sum(w);return[x/s for x in w]
def _paired_ci(values):
 if len(values)<2:return {"mean":_mean(values),"lower_95":None,"upper_95":None,"n":len(values)}
 mean=_mean(values);se=statistics.stdev(values)/math.sqrt(len(values))
 return {"mean":mean,"lower_95":mean-1.96*se,"upper_95":mean+1.96*se,"n":len(values)}
def evaluate(store:RacingStore,version:str=VERSION)->dict[str,Any]:
 raw=store.connection.execute("""SELECT e.*,r.race_date,c.horse_name,c.finish_position,p.performance_rating FROM v2_runner_energy_sectionals e
 JOIN v2_clean_races r USING(race_id) JOIN v2_clean_runner_results c USING(race_id,runner_number)
 JOIN v2_run_performances p USING(race_id,runner_number) WHERE e.version=? AND p.model_version=? ORDER BY r.race_date,r.race_id""",(version,MODEL_VERSION)).fetchall()
 rows=[{**dict(x),"performance":float(x["performance_rating"]),"compensation":float(x["compensation_signal"]),"achievement":float(x["achievement_signal"])} for x in raw]
 horses=defaultdict(list)
 for x in rows:horses[(x["horse_key"],x["distance_band"])].append(x)
 pairs=[]
 for runs in horses.values():
  for cur,nxt in zip(runs,runs[1:]):pairs.append((cur,nxt,float(nxt["performance"])-cur["performance"]))
 coefficients={}
 for jur in ("NSW","VIC"):
  coefficients[jur]={}
  for band in ("sprint","middle","staying"):
   train=[(x,t) for x,_,t in pairs if x["jurisdiction"]==jur and x["distance_band"]==band and x["race_date"]<"2025-01-01"]
   coefficients[jur][band]=_fit(train,("achievement","compensation"))
 def adjustment(x,mode="combined"):
  c=coefficients[x["jurisdiction"]][x["distance_band"]];v=0
  if mode in ("achievement","combined"):v+=c["achievement"]*x["achievement"]
  if mode in ("compensation","combined"):v+=c["compensation"]*x["compensation"]
  return _clip(v,-3,3)
 modes=("base","achievement","compensation","combined");next_metrics={};suitable={}
 for mode in modes:
  sample=[]
  for cur,nxt,target in pairs:
   if cur["race_date"]<"2025-01-01":continue
   adj=0 if mode=="base" else adjustment(cur,mode);sample.append((cur["jurisdiction"],cur["distance_band"],abs(target-adj)))
  next_metrics[mode]={"overall":_mean([x[2] for x in sample]),"jurisdiction":{j:_mean([x[2] for x in sample if x[0]==j]) for j in ("NSW","VIC")},
   "distance_band":{b:_mean([x[2] for x in sample if x[1]==b]) for b in ("sprint","middle","staying")},"pairs":len(sample)}
 suitable_rows=[(cur,nxt,nxt["performance"]-cur["performance"]) for cur,nxt,_ in pairs if cur["race_date"]>="2025-01-01" and cur["compensation"]>=1 and nxt["distance_band"]==cur["distance_band"] and nxt["compensation"]<cur["compensation"]]
 suitable={"pairs":len(suitable_rows),"mean_next_rating_change":_mean([x[2] for x in suitable_rows])}
 byrace=defaultdict(list)
 for x in rows:byrace[x["race_id"]].append(x)
 histories={m:defaultdict(list) for m in modes};examples=[]
 for rid,runners in byrace.items():
  if len(runners)>=4 and sum(x["finish_position"]==1 for x in runners)==1 and sum(bool(histories["base"][(x["horse_key"],x["distance_band"])]) for x in runners)/len(runners)>=.6:
   ex={"date":runners[0]["race_date"],"jur":runners[0]["jurisdiction"],"winner":next(i for i,x in enumerate(runners) if x["finish_position"]==1)}
   ex["band"]=runners[0]["distance_band"]
   for m in modes:ex[m]=[statistics.median(histories[m][(x["horse_key"],x["distance_band"])][-3:]) if histories[m][(x["horse_key"],x["distance_band"])] else 100 for x in runners]
   examples.append(ex)
  for x in runners:
   for m in modes:histories[m][(x["horse_key"],x["distance_band"])].append(x["performance"]+(0 if m=="base" else adjustment(x,m)))
 train=[x for x in examples if x["date"]<"2025-01-01"];test=[x for x in examples if x["date"]>="2025-01-01"]
 ranking={}
 for m in modes:
  def ll(sample,temp):return _mean([-math.log(max(_softmax([v/temp for v in x[m]])[x["winner"]],1e-12)) for x in sample])
  temp=min((3,5,8,10,12,15),key=lambda t:ll(train,t));ranking[m]={"overall":ll(test,temp),"temperature":temp,"races":len(test),
   "jurisdiction":{j:ll([x for x in test if x["jur"]==j],temp) for j in ("NSW","VIC")},
   "distance_band":{b:ll([x for x in test if x["band"]==b],temp) for b in ("sprint","middle","staying")}}
 uncertainty={}
 for m in modes[1:]:
  next_diffs=[]
  for cur,_,target in pairs:
   if cur["race_date"]>="2025-01-01":next_diffs.append((cur["race_date"],cur["jurisdiction"],cur["distance_band"],abs(target-adjustment(cur,m))-abs(target)))
  rank_diffs=[]
  for x in test:
   base_loss=-math.log(max(_softmax([v/ranking["base"]["temperature"] for v in x["base"]])[x["winner"]],1e-12))
   candidate_loss=-math.log(max(_softmax([v/ranking[m]["temperature"] for v in x[m]])[x["winner"]],1e-12))
   rank_diffs.append((x["date"],x["jur"],x["band"],candidate_loss-base_loss))
  grouped=lambda values,index,key:_paired_ci([x[3] for x in values if x[index]==key])
  quarters=sorted(set(x[0][:4]+"-Q"+str((int(x[0][5:7])-1)//3+1) for x in next_diffs+rank_diffs))
  byquarter={q:{"next_start_mae_difference":_paired_ci([x[3] for x in next_diffs if x[0][:4]+"-Q"+str((int(x[0][5:7])-1)//3+1)==q]),
    "race_log_loss_difference":_paired_ci([x[3] for x in rank_diffs if x[0][:4]+"-Q"+str((int(x[0][5:7])-1)//3+1)==q])} for q in quarters}
  uncertainty[m]={"next_start_mae_difference":_paired_ci([x[3] for x in next_diffs]),"race_log_loss_difference":_paired_ci([x[3] for x in rank_diffs]),
   "by_jurisdiction":{j:{"next_start_mae_difference":grouped(next_diffs,1,j),"race_log_loss_difference":grouped(rank_diffs,1,j)} for j in ("NSW","VIC")},
   "by_distance_band":{b:{"next_start_mae_difference":grouped(next_diffs,2,b),"race_log_loss_difference":grouped(rank_diffs,2,b)} for b in ("sprint","middle","staying")},
   "calendar_quarter":byquarter}
 decisions={}
 for m in modes[1:]:decisions[m]={"next_mae_both_jurisdictions":all(next_metrics[m]["jurisdiction"][j]<next_metrics["base"]["jurisdiction"][j] for j in ("NSW","VIC")),
  "ranking_both_jurisdictions":all(ranking[m]["jurisdiction"][j]<ranking["base"]["jurisdiction"][j] for j in ("NSW","VIC")),
  "all_distance_bands_next_mae":all(next_metrics[m]["distance_band"][b]<next_metrics["base"]["distance_band"][b] for b in ("sprint","middle","staying"))}
 for m in decisions:
  decisions[m]["distance_band"]={b:{"next_mae_improved":next_metrics[m]["distance_band"][b]<next_metrics["base"]["distance_band"][b],
    "ranking_improved":ranking[m]["distance_band"][b]<ranking["base"]["distance_band"][b]} for b in ("sprint","middle","staying")}
  decisions[m]["uncertainty_overall_favourable"]=uncertainty[m]["next_start_mae_difference"]["upper_95"]<0 and uncertainty[m]["race_log_loss_difference"]["upper_95"]<0
  decisions[m]["uncertainty_both_jurisdictions_favourable"]=all(uncertainty[m]["by_jurisdiction"][j][metric]["upper_95"] is not None and uncertainty[m]["by_jurisdiction"][j][metric]["upper_95"]<0 for j in ("NSW","VIC") for metric in ("next_start_mae_difference","race_log_loss_difference"))
  decisions[m]["promote"]=all(value for key,value in decisions[m].items() if key!="distance_band")
 return {"version":version,"coefficients":coefficients,"next_start":next_metrics,"suitable_pace_response":suitable,"ranking":ranking,
  "paired_uncertainty":uncertainty,"promotion":decisions,"accepted_rating_changed":False}

def main():
 p=argparse.ArgumentParser();p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite");p.add_argument("--build-output",type=Path);p.add_argument("--evaluation-output",type=Path);p.add_argument("--vic-200m",action="store_true");p.add_argument("--hierarchical",action="store_true");a=p.parse_args();s=RacingStore(a.database);version=HIER_VERSION if a.hierarchical else RICH_VERSION if a.vic_200m else VERSION
 try:b=build(s,version,a.vic_200m or a.hierarchical,a.hierarchical);e=evaluate(s,version)
 finally:s.close()
 for value,path in ((b,a.build_output),(e,a.evaluation_output)):
  rendered=json.dumps(value,indent=2,sort_keys=True)+"\n"
  if path:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(rendered)
  else:print(rendered,end="")
if __name__=="__main__":main()
