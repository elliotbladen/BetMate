"""Season-forward UCL predictions using the shared Dixon-Coles engine."""
import json
from pathlib import Path
import pandas as pd
import numpy as np
from .ucl_shared_engine import load_matches, fit_before, build_elo_before, price
from .ucl_backtest import multiclass_metrics
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/"data/ucl/clv/ucl_shared_walk_forward_predictions.csv"; REPORT=ROOT/"ml/football/reports/ucl_shared_walk_forward.json"
def run():
 d=load_matches(); rows=[]; seasons=sorted(d.season.unique())
 for season in seasons:
  current=d[d.season==season]; prior=d[d.Date<current.Date.min()]
  cutoff=current.Date.min(); ratings=fit_before(d,cutoff) if len(prior)>=50 else {}
  elo=build_elo_before(d,cutoff) if len(prior)>=10 else None
  for _,r in current.iterrows():
   if not ratings: continue
   try:
    q=price(r.home_team,r.away_team,ratings,elo=elo,matches=d,as_of=r.Date); row=r.to_dict(); row.update({"p_home":q["p_home"],"p_draw":q["p_draw"],"p_away":q["p_away"],"p_over25":q["p_over25"],"p_under25":q["p_under25"],"p_ah_home":q["p_ah_home"],"p_ah_away":q["p_ah_away"],"lambda_home":q["lambda_home"],"lambda_away":q["lambda_away"],"elo_weight":q["elo_weight"],"engine":q["engine"]}); rows.append(row)
   except KeyError: continue
 out=pd.DataFrame(rows); report={"status":"ucl_shared_stack_walk_forward_complete","games":len(out),"seasons":sorted(out.season.unique().tolist()),"engine":"ucl_shared_dixon_coles_elo_tier_stack","market_fields_used":False,"metrics":multiclass_metrics(out),"stack":{"dixon_coles":0.70,"club_elo":0.30,"tiers":"form/rest active; PPDA/injury/referee/set-piece/manager shadow until historical coverage"},"restrictions":["season-forward fits","goals fallback for missing xG","no future leakage in Elo, form or rest"]}; OUT.parent.mkdir(parents=True,exist_ok=True); REPORT.parent.mkdir(parents=True,exist_ok=True); out.to_csv(OUT,index=False); REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); return report
if __name__=="__main__": print(json.dumps(run(),indent=2))
