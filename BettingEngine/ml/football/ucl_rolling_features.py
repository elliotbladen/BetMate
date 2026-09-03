"""Build leakage-safe rolling UCL xG/stat features."""
from pathlib import Path
from collections import defaultdict, deque
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
MATCH=ROOT/"data/ucl/matches/ucl_matches_openfootball_repaired.csv"
XG=ROOT/"data/ucl/xg/ucl_match_xg_mapped.csv"
ST=ROOT/"data/ucl/xg/ucl_sofascore_match_stats.csv"
OUT=ROOT/"data/ucl/xg/ucl_rolling_prematch_features.csv"
def run():
 m=pd.read_csv(MATCH); m["Date"]=pd.to_datetime(m.kickoff_utc,utc=True)
 x=pd.read_csv(XG)[["match_id","home_xg","away_xg"]]; s=pd.read_csv(ST)
 d=m.merge(x,on="match_id",how="left").merge(s,on="match_id",how="left",suffixes=("","_stat")).sort_values(["Date","match_id"])
 hist=defaultdict(lambda:defaultdict(lambda:deque(maxlen=5))); rows=[]
 for _,r in d.iterrows():
  row=r.to_dict()
  for team in (r.home_club_id,r.away_club_id):
   for metric in ("xg_for","xg_against","shots_for","big_chances_for"):
    vals=[v for v in hist[team][metric] if pd.notna(v)]; row[f"{team}_{metric}_roll5"]=sum(vals)/len(vals) if vals else None
  rows.append(row)
  for team,side,opp in ((r.home_club_id,"home","away"),(r.away_club_id,"away","home")):
   hist[team]["xg_for"].append(r.get(f"{side}_xg") if pd.notna(r.get(f"{side}_xg")) else r.get(f"{side}_goals"))
   hist[team]["xg_against"].append(r.get(f"{opp}_xg") if pd.notna(r.get(f"{opp}_xg")) else r.get(f"{opp}_goals"))
   hist[team]["shots_for"].append(r.get(f"shotsOnGoal_{side}")); hist[team]["big_chances_for"].append(r.get(f"bigChanceCreated_{side}"))
 out=pd.DataFrame(rows); OUT.parent.mkdir(parents=True,exist_ok=True); out.to_csv(OUT,index=False); return {"rows":len(out),"rolling_columns":len([c for c in out if "roll5" in c]),"output":str(OUT.relative_to(ROOT)).replace("\\","/")}
if __name__=="__main__": print(run())
