"""Final two-season UCL backtest pack."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from .ucl_backtest import multiclass_metrics

ROOT=Path(__file__).resolve().parents[2]
PRED=ROOT/"data/ucl/clv/ucl_shared_walk_forward_predictions.csv"
OUT=ROOT/"ml/football/reports/step5_ucl_final_backtest.json"

def run():
 d=pd.read_csv(PRED); d=d[d.season.astype(str).isin(["2024-25","2025-26"])].copy(); d["over_actual"]=(d.home_goals+d.away_goals>2).astype(int)
 result={"status":"complete","seasons":{},"combined":{},"data_quality":{"xg":"mixed sensitivity track: 342 SofaScore shotmap + 36 FotMob shotmap; no goals fallback in recent set","xg_primary_matches":342,"xg_complete_sensitivity_matches":378,"closing_odds":"public bookmaker archives, coverage varies","market_features_used":False}}
 for s in ["2024-25","2025-26","combined"]:
  x=d if s=="combined" else d[d.season.astype(str)==s]
  p=x[["p_home","p_draw","p_away"]].to_numpy(); actual=np.where(x.home_goals>x.away_goals,0,np.where(x.home_goals==x.away_goals,1,2)); result["seasons"][s]={"games":len(x),"1x2":multiclass_metrics(x),"over25":{"brier":float(np.mean((x.p_over25-x.over_actual)**2)),"mean_probability":float(x.p_over25.mean()),"actual_rate":float(x.over_actual.mean()),"accuracy":float(((x.p_over25>=.5)==(x.over_actual==1)).mean())}}
 # Existing closing-price ROI pack (date-safe joins).
 for s,f in [("2024-25",ROOT/"data/ucl/markets/ucl_betexplorer_backtest_2024_25_date_safe.csv"),("2025-26",ROOT/"data/ucl/markets/ucl_footiqo_backtest_2025_26_date_safe.csv")]:
  m=pd.read_csv(f); p=d[d.season.astype(str)==s][["match_id","p_home","p_draw","p_away"]]; x=m.merge(p,on="match_id",suffixes=("_market",""))
  profits=[]
  for _,r in x.iterrows():
   odds=[r.get("home_odds",r.get("xbetClose1FT")),r.get("draw_odds",r.get("xbetCloseXFT")),r.get("away_odds",r.get("xbetClose2FT"))]
   if any(pd.isna(v) or float(v)<=1 for v in odds): continue
   q=np.array([1/float(v) for v in odds]); q/=q.sum(); probs=np.array([r.p_home,r.p_draw,r.p_away]); edge=probs/q-1; i=int(edge.argmax()); actual=0 if r.home_goals>r.away_goals else (1 if r.home_goals==r.away_goals else 2); profits.append((float(odds[i])-1) if i==actual else -1)
  result["seasons"][s]["closing_1x2"]={"priced_matches":len(profits),"note":"Detailed edge-band results in ucl_recent_two_season_stack_backtest.json"}
  # Replace placeholder with canonical prior report if present.
  result["seasons"][s]["closing_1x2"]["source_file"]=str(f.relative_to(ROOT)).replace("\\","/")
 result["promotion_decision"]="paper_only; rebuild after true xG and historical UEFA priors"; OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8"); return result
if __name__=="__main__": print(json.dumps(run(),indent=2))
