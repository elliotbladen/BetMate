"""Pair historical UCL knockout legs and compute aggregate outcomes."""
from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]; MATCHES=ROOT/"data/ucl/matches/ucl_matches_openfootball.csv"; OUT=ROOT/"data/ucl/clv/ucl_knockout_ties.csv"; REPORT=ROOT/"ml/football/reports/ucl_tie_pairing.json"
def run():
 d=pd.read_csv(MATCHES); d=d[d.season.isin(["2024-25","2025-26"])&d.stage.str.contains("knockout")].copy(); d["round"]=d.matchday
 rows=[]; paired=0
 for (season, rnd, pair_key), g in d.assign(pair_key=d.apply(lambda r: "|".join(sorted([r.home_club_id,r.away_club_id])),axis=1)).groupby(["season","round","pair_key"]):
  a,b=pair_key.split("|",1)
  g=g.sort_values(["kickoff_utc","match_id"]); legs=len(g); first=g.iloc[0]; second=g.iloc[1] if legs>1 else None
  if second is not None:
   agg_a=(int(first.home_goals) if first.home_club_id==a else int(first.away_goals))+(int(second.home_goals) if second.home_club_id==a else int(second.away_goals)); agg_b=(int(first.home_goals) if first.home_club_id==b else int(first.away_goals))+(int(second.home_goals) if second.home_club_id==b else int(second.away_goals)); winner=a if agg_a>agg_b else b if agg_b>agg_a else "tied_source_needs_et_penalties"; paired+=1
  else: agg_a=agg_b=None; winner="single_match"
  rows.append({"season":season,"round":rnd,"club_a":a,"club_b":b,"legs":legs,"aggregate_a":agg_a,"aggregate_b":agg_b,"winner_status":winner})
 out=pd.DataFrame(rows); result={"status":"ucl_knockout_tie_pairing_complete","seasons":sorted(out.season.unique().tolist()),"ties":len(out),"two_leg_ties":int((out.legs==2).sum()),"single_matches":int((out.legs==1).sum()),"aggregate_ties_requiring_resolution":int((out.winner_status=="tied_source_needs_et_penalties").sum()),"source_scores_used":True,"output":str(OUT.relative_to(ROOT))}; OUT.parent.mkdir(parents=True,exist_ok=True); out.to_csv(OUT,index=False); REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8"); return result
if __name__=="__main__": print(json.dumps(run(),indent=2))
