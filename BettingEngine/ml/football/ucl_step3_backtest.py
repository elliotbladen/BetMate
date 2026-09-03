"""Chronological out-of-sample backtest for the Step 3 stage calibration."""
from pathlib import Path
import json
import math
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
COMPLETE=ROOT/"data/ucl/matches/ucl_recent_complete_xg_v2.csv"
FIX=ROOT/"data/ucl/matches/ucl_matches_openfootball_repaired.csv"
REPORT=ROOT/"ml/football/reports/step3_ucl_stage_backtest.json"

def over_prob(mu):
    return 1.0-math.exp(-mu)*(1.0+mu+mu*mu/2.0)
def brier(p,y): return sum((a-b)**2 for a,b in zip(p,y))/len(p)
def logloss(p,y):
    eps=1e-12; return -sum(b*math.log(max(a,eps))+(1-b)*math.log(max(1-a,eps)) for a,b in zip(p,y))/len(p)
def run():
    d=pd.read_csv(COMPLETE).merge(pd.read_csv(FIX)[["match_id","stage","matchday"]],on="match_id",how="left")
    d["total_xg"]=d.home_xg+d.away_xg; d["y"]=(d.home_goals+d.away_goals>2.5).astype(int)
    d=d.sort_values(["season","match_id"]).reset_index(drop=True)
    train=d[d.season.eq("2024-25")]
    global_ratio=train[["home_goals","away_goals"]].sum().sum()/train.total_xg.sum()
    ratios=train.assign(total_goals=train.home_goals+train.away_goals).groupby(["stage","matchday"]).apply(lambda g:(g.total_goals.sum()+50*train.assign(total_goals=train.home_goals+train.away_goals).total_goals.mean())/(g.total_xg.sum()+50*train.total_xg.mean()),include_groups=False).to_dict()
    hist={}
    pre=[]
    for _,r in d.iterrows():
        def avg(team,key,default):
            v=hist.get(team,{}).get(key,[])[-5:]
            return sum(v)/len(v) if v else default
        all_home=train.home_xg.mean(); all_away=train.away_xg.mean()
        ha=avg(r.home_club_id,"gf",all_home); hd=avg(r.home_club_id,"ga",all_away)
        aa=avg(r.away_club_id,"gf",all_away); ad=avg(r.away_club_id,"ga",all_home)
        pre.append(max(.15,(ha+ad)/2)+max(.10,(aa+hd)/2))
        hist.setdefault(r.home_club_id,{"gf":[],"ga":[]}); hist.setdefault(r.away_club_id,{"gf":[],"ga":[]})
        hist[r.home_club_id]["gf"].append(float(r.home_xg)); hist[r.home_club_id]["ga"].append(float(r.away_xg))
        hist[r.away_club_id]["gf"].append(float(r.away_xg)); hist[r.away_club_id]["ga"].append(float(r.home_xg))
    d["prematch_total_xg"]=pre
    test=d[d.season.eq("2025-26")]
    base=[]; adj=[]; y=[]
    for _,r in test.iterrows():
        mu=float(r.prematch_total_xg)*global_ratio; mu2=float(r.prematch_total_xg)*float(ratios.get((r.stage,r.matchday),global_ratio))
        base.append(over_prob(mu)); adj.append(over_prob(mu2)); y.append(int(r.y))
    report={"status":"ucl_step3_stage_backtest_complete","train_season":"2024-25","test_season":"2025-26","test_matches":len(test),"feature_timing":"pre-match rolling xG from prior matches only; no same-match xG","baseline":{"brier":brier(base,y),"log_loss":logloss(base,y),"mean_over_probability":sum(base)/len(base)},"stage_adjusted":{"brier":brier(adj,y),"log_loss":logloss(adj,y),"mean_over_probability":sum(adj)/len(adj)},"actual_over25_rate":sum(y)/len(y),"brier_change_stage_minus_baseline":brier(adj,y)-brier(base,y),"log_loss_change_stage_minus_baseline":logloss(adj,y)-logloss(base,y),"activation":"paper challenger only"}
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); print(json.dumps(report,indent=2))
if __name__=="__main__": run()
