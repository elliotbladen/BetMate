"""Evaluate the free static UCL odds archive independently of model joins."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
ODDS=ROOT/"data/ucl/markets/ucl_free_unverified_1x2.csv"; REPORT=ROOT/"ml/football/reports/ucl_free_odds_benchmark.json"
def run():
 d=pd.read_csv(ODDS); odds=d[["home_odds","draw_odds","away_odds"]].astype(float); valid=(odds>1).all(axis=1)&d.home_goals.notna()&d.away_goals.notna(); d=d[valid].reset_index(drop=True); odds=d[["home_odds","draw_odds","away_odds"]].to_numpy(); imp=1/odds; p=imp/imp.sum(axis=1,keepdims=True); actual=np.where(d.home_goals>d.away_goals,0,np.where(d.home_goals==d.away_goals,1,2)); pick=p.argmax(1); onehot=np.eye(3)[actual]
 result={"status":"ucl_free_odds_standalone_benchmark_complete","matches":len(d),"seasons":sorted(d.season_source.astype(str).unique().tolist()),"market_accuracy":float((pick==actual).mean()),"market_brier":float(((p-onehot)**2).sum(1).mean()),"mean_overround":float((imp.sum(1)-1).mean()),"closing_status":"unverified_static_close","timestamps_present":False,"model_join_excluded":True,"restrictions":["benchmark only","no confirmed close timestamp","no ROI or CLV claim"]}
 REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8"); return result
if __name__=="__main__": print(json.dumps(run(),indent=2))
