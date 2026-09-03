"""Repair modern UCL fixture dates from dated SofaScore events."""
from pathlib import Path
import json
import pandas as pd
from difflib import SequenceMatcher
from .ucl_market_backtest import team_key

ROOT=Path(__file__).resolve().parents[2]; MATCH=ROOT/"data/ucl/matches/ucl_matches_openfootball_repaired.csv"; XG=ROOT/"data/ucl/xg/ucl_sofascore_match_xg.csv"; MAPPED=ROOT/"data/ucl/xg/ucl_match_xg_mapped.csv"; OUT=ROOT/"data/ucl/matches/ucl_matches_sofascore_dates.csv"; REPORT=ROOT/"ml/football/reports/ucl_sofascore_date_repair.json"
def norm(v):
 s=team_key(v).replace("atl-tico","atletico").replace("m-nchen","munchen").replace("bayern-m-nchen","bayern-munich")
 for t in ("fc-","-fc","bsc-","club-","fk-","-cf","-osc","-kv","-1909"): s=s.replace(t,"-")
 return s.strip("-")
def run():
 m=pd.read_csv(MATCH); m=m[m.season.astype(str).isin(["2024-25","2025-26"])].copy(); m["hk"]=m.home_club_id.map(norm);m["ak"]=m.away_club_id.map(norm)
 if MAPPED.exists():
  mapped=pd.read_csv(MAPPED)[["match_id","sofascore_event_id"]]; xall=pd.read_csv(XG); xall["date"]=pd.to_datetime(pd.to_numeric(xall.kickoff_utc),unit="s",utc=True); em=xall.set_index("event_id")["date"].to_dict(); mp={r.match_id:em.get(r.sofascore_event_id) for _,r in mapped.iterrows()}; out=m.copy(); out["kickoff_utc_original"]=out.kickoff_utc; out["kickoff_utc"]=out.match_id.map(lambda k: mp.get(k).isoformat() if mp.get(k) is not None else None); out["date_repair_source"]=out.match_id.map(lambda k:"sofascore_event" if mp.get(k) is not None else "unrepaired"); out.to_csv(OUT,index=False); repaired=sum(v is not None for v in mp.values()); report={"canonical_matches":len(m),"repaired":repaired,"coverage":repaired/len(m),"unrepaired":len(m)-repaired,"ambiguous":0,"by_season":out[out.date_repair_source=="sofascore_event"].season.value_counts().to_dict()}; REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); return report
 x=pd.read_csv(XG); x["date"]=pd.to_datetime(pd.to_numeric(x.kickoff_utc),unit="s",utc=True);x["hk"]=x.home_team.map(norm);x["ak"]=x.away_team.map(norm); updates=[]; used=set(); ambiguous=0
 for season in ["2024-25","2025-26"]:
  mm=m[m.season.astype(str)==season].copy(); xx=x[x.season.astype(str)==season].copy()
  pairs=sorted(set(zip(mm.hk,mm.ak)))
  for hk,ak in pairs:
   a=mm[(mm.hk==hk)&(mm.ak==ak)].sort_values("match_id"); b=xx[(xx.hk==hk)&(xx.ak==ak)&(~xx.event_id.isin(used))].sort_values("date")
   if len(b)!=len(a):
    b=xx[~xx.event_id.isin(used)].copy(); b["score"]=[(SequenceMatcher(None,hk,z).ratio()+SequenceMatcher(None,ak,w).ratio())/2 for z,w in zip(b.hk,b.ak)]; b=b[b.score>=.82].sort_values("date").head(len(a))
   if len(b)!=len(a): ambiguous += len(a); continue
   for (_,mr),(_,xr) in zip(a.iterrows(),b.iterrows()): updates.append((mr.match_id,xr.date.isoformat(),xr.event_id));used.add(xr.event_id)
 out=m.copy(); mp={k:(d,e) for k,d,e in updates}; out["kickoff_utc_original"]=out.kickoff_utc; out["kickoff_utc"]=out.match_id.map(lambda k:mp[k][0] if k in mp else None); out["date_repair_source"]=out.match_id.map(lambda k:"sofascore_event" if k in mp else "unrepaired"); out.to_csv(OUT,index=False)
 report={"canonical_matches":len(m),"repaired":len(updates),"coverage":len(updates)/len(m),"unrepaired":len(m)-len(updates),"ambiguous":ambiguous,"by_season":out[out.date_repair_source=="sofascore_event"].season.value_counts().to_dict()}; REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); return report
if __name__=="__main__": print(json.dumps(run(),indent=2))
