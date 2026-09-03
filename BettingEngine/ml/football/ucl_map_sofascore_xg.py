"""Map SofaScore shotmap xG onto canonical UCL fixtures."""
from pathlib import Path
import pandas as pd
from difflib import SequenceMatcher
from .ucl_market_backtest import team_key
def norm(v):
    s=team_key(v).replace("atl-tico","atletico").replace("m-nchen","munchen").replace("bayern-m-nchen","bayern-munich")
    for t in ("fc-","-fc","bsc-","club-","fk-","-cf","-osc","-kv","-1909"): s=s.replace(t,"-")
    return s.strip("-")

ROOT=Path(__file__).resolve().parents[2]; MATCH=ROOT/"data/ucl/matches/ucl_matches_openfootball_repaired.csv"; XG=ROOT/"data/ucl/xg/ucl_sofascore_match_xg.csv"; OUT=ROOT/"data/ucl/xg/ucl_match_xg_mapped.csv"; REPORT=ROOT/"ml/football/reports/ucl_recent_xg_mapping.json"
def run():
 m=pd.read_csv(MATCH); m=m[m.season.astype(str).isin(["2024-25","2025-26"])].copy(); m["date"]=pd.to_datetime(m.kickoff_utc,utc=True).dt.date; m["hk"]=m.home_club_id.map(norm); m["ak"]=m.away_club_id.map(norm)
 x=pd.read_csv(XG); x["date"]=pd.to_datetime(pd.to_numeric(x.kickoff_utc),unit="s",utc=True).dt.date; x["hk"]=x.home_team.map(norm); x["ak"]=x.away_team.map(norm); rows=[]; used=set(); ambiguous=0
 for _,r in m.iterrows():
  cand=x[(x.season.astype(str)==str(r.season)) & (~x.event_id.isin(used))].copy(); cand["daydiff"]=(pd.to_datetime(cand.date)-pd.Timestamp(r.date)).abs().dt.days; cand["score"]=[(SequenceMatcher(None,r.hk,a).ratio()+SequenceMatcher(None,r.ak,b).ratio())/2 for a,b in zip(cand.hk,cand.ak)]; cand=cand[(cand.daydiff<=2)&(cand.score>=.65)].sort_values(["score","daydiff"],ascending=[False,True])
  if not len(cand):
   # A small number of archive fixtures have season/date repairs that differ
   # by more than two days. Fall back to a high-confidence club-pair match,
   # still one-to-one and still within the same season.
   broad=x[(x.season.astype(str)==str(r.season)) & (~x.event_id.isin(used))].copy(); broad["daydiff"]=(pd.to_datetime(broad.date)-pd.Timestamp(r.date)).abs().dt.days; broad["score"]=[(SequenceMatcher(None,r.hk,a).ratio()+SequenceMatcher(None,r.ak,b).ratio())/2 for a,b in zip(broad.hk,broad.ak)]; cand=broad[broad.score>=.82].sort_values(["score","daydiff"],ascending=[False,True]).head(2)
  if len(cand) and (len(cand)==1 or (cand.iloc[0].score-cand.iloc[1].score>=.10)):
   z=cand.iloc[0]; rows.append({"match_id":r.match_id,"season":r.season,"home_club_id":r.home_club_id,"away_club_id":r.away_club_id,"kickoff_utc":r.kickoff_utc,"home_xg":z.home_xg,"away_xg":z.away_xg,"xg_source":"sofascore_shotmap","sofascore_event_id":z.event_id,"mapping_day_difference":int(z.daydiff),"mapping_score":float(z.score)}); used.add(z.event_id)
  elif len(cand): ambiguous+=1
 out=pd.DataFrame(rows); OUT.parent.mkdir(parents=True,exist_ok=True); out.to_csv(OUT,index=False); report={"canonical_matches":len(m),"mapped":len(out),"coverage":len(out)/len(m),"ambiguous":ambiguous,"unmapped":len(m)-len(out),"by_season":out.season.value_counts().to_dict() if len(out) else {},"decision":"candidate xG only; activate after one-to-one coverage and provider audit"}; REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(__import__('json').dumps(report,indent=2)+"\n",encoding="utf-8"); return report
if __name__=="__main__": print(run())
