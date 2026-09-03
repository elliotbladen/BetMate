import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]; JOIN=ROOT/"data/ucl/clv/ucl_free_market_join.csv"; REPORT=ROOT/"ml/football/reports/step2_ucl_market_eval.json"
def run():
 d=pd.read_csv(JOIN); probs=d[["p_home","p_draw","p_away"]].to_numpy(); market=d[["market_home_prob","market_draw_prob","market_away_prob"]].to_numpy(); actual=np.where(d.home_goals>d.away_goals,0,np.where(d.home_goals==d.away_goals,1,2)); edge=probs-market; best=edge.max(1); pick=edge.argmax(1); odds=d[["home_odds","draw_odds","away_odds"]].to_numpy(); returns=odds[np.arange(len(d)),pick]-1; win=(pick==actual); d["max_edge"]=best; d["value_pick"]=pick; d["value_win"]=win; d["flat_return"]=np.where(win,returns,-1)
 buckets=[]
 for low,high in [(0,.02),(.02,.05),(.05,.10),(.10,1)]:
  x=d[(d.max_edge>=low)&(d.max_edge<high)]
  buckets.append({"edge_band":f"{low:.2f}-{high:.2f}","bets":len(x),"win_rate":float(x.value_win.mean()) if len(x) else None,"roi":float(x.flat_return.sum()/len(x)) if len(x) else None})
 result={"status":"ucl_step2_market_evaluation_complete","matches":len(d),"closing_status":"archived_closing","model_accuracy":float((probs.argmax(1)==actual).mean()),"market_accuracy":float((market.argmax(1)==actual).mean()),"mean_max_edge":float(best.mean()),"edge_buckets":buckets,"provisional_flat_stake_roi_all":float(d.flat_return.mean()),"restrictions":["51 joined matches","archived closing odds without quote timestamps","not statistically conclusive","no staking promotion"]}
 d.to_csv(JOIN,index=False); REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8"); return result
if __name__=="__main__": print(json.dumps(run(),indent=2))
