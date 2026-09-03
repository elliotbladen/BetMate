"""Download free SofaScore match-level statistics for mapped UCL events."""
from pathlib import Path
import json, ssl, urllib.request, time
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]; MAPPED=ROOT/"data/ucl/xg/ucl_match_xg_mapped.csv"; OUT=ROOT/"data/ucl/xg/ucl_sofascore_match_stats.csv"; CTX=ssl._create_unverified_context()
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"BetMate research client"}); return json.loads(urllib.request.urlopen(req,context=CTX,timeout=30).read())
def run():
 m=pd.read_csv(MAPPED); rows=[]
 for _,r in m.iterrows():
  try: d=get(f"https://www.sofascore.com/api/v1/event/{int(r.sofascore_event_id)}/statistics")
  except Exception: continue
  vals={}
  for period in d.get("statistics",[]):
   if period.get("period")!="ALL": continue
   for group in period.get("groups",[]):
    for item in group.get("statisticsItems",[]):
     if item.get("key") in {"expectedGoals","bigChanceCreated","totalShots","shotsOnGoal","cornerKicks","ballPossession","accuratePasses","redCards","yellowCards","fouls"}:
      vals[item["key"]+"_home"]=item.get("homeValue"); vals[item["key"]+"_away"]=item.get("awayValue")
  if vals: rows.append({"match_id":r.match_id,"season":r.season,"sofascore_event_id":r.sofascore_event_id,**vals})
  time.sleep(.04)
 out=pd.DataFrame(rows); OUT.parent.mkdir(parents=True,exist_ok=True);out.to_csv(OUT,index=False); return {"rows":len(out),"fields":sorted(set(out.columns)-{"match_id","season","sofascore_event_id"}),"output":str(OUT.relative_to(ROOT)).replace("\\","/")}
if __name__=="__main__": print(json.dumps(run(),indent=2))
