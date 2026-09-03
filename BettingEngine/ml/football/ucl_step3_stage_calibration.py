"""Fit stage-aware scoring and totals calibration parameters.

Parameters are estimated chronologically from the complete recent UCL track;
they are a challenger layer and do not change live prices automatically.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
COMPLETE=ROOT/"data/ucl/matches/ucl_recent_complete_xg_v2.csv"
FIX=ROOT/"data/ucl/matches/ucl_matches_openfootball_repaired.csv"
OUT=ROOT/"data/ucl/context/ucl_stage_calibration.csv"
REPORT=ROOT/"ml/football/reports/step3_ucl_stage_calibration.json"

def run():
    d=pd.read_csv(COMPLETE).merge(pd.read_csv(FIX)[["match_id","stage","matchday"]],on="match_id",how="left")
    d["total_goals"]=d.home_goals+d.away_goals; d["total_xg"]=d.home_xg+d.away_xg
    global_goal=float(d.total_goals.mean()); global_xg=float(d.total_xg.mean()); global_over=float((d.total_goals>2.5).mean())
    rows=[]
    for (stage,md),g in d.groupby(["stage","matchday"],dropna=False):
        n=len(g); shrink=n/(n+50.0)
        observed_goal=float(g.total_goals.mean()); observed_xg=float(g.total_xg.mean()); observed_over=float((g.total_goals>2.5).mean())
        rows.append({"stage":str(stage),"matchday":str(md),"matches":n,"mean_goals":observed_goal,"mean_xg":observed_xg,"over25_rate":observed_over,"goal_mean_shrunk":shrink*observed_goal+(1-shrink)*global_goal,"xg_mean_shrunk":shrink*observed_xg+(1-shrink)*global_xg,"over25_rate_shrunk":shrink*observed_over+(1-shrink)*global_over,"xg_to_goals_ratio":observed_goal/observed_xg if observed_xg>0 else None,"fit_rule":"empirical_bayes_n_over_n_plus_50"})
    out=pd.DataFrame(rows).sort_values(["stage","matchday"]); OUT.parent.mkdir(parents=True,exist_ok=True); out.to_csv(OUT,index=False)
    report={"status":"ucl_step3_stage_calibration_complete","matches":len(d),"global_mean_goals":global_goal,"global_mean_xg":global_xg,"global_over25_rate":global_over,"groups":len(out),"output":str(OUT.relative_to(ROOT)).replace('\\','/'),"stage_fields":["stage","matchday"],"activation":"challenger only; chronological validation required before price adjustment"}
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); print(json.dumps(report,indent=2))
if __name__=="__main__": run()
