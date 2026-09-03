"""Out-of-sample Step 2 calibration audit for UCL match markets."""
from pathlib import Path
import json, math
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

ROOT=Path(__file__).resolve().parents[2]
PRED=ROOT/"data/ucl/clv/ucl_shared_walk_forward_predictions.csv"
REPORT=ROOT/"ml/football/reports/step2_ucl_market_calibration.json"

def brier(p,y): return float(np.mean((np.asarray(p)-np.asarray(y))**2))
def cal_error(p,y):
    p=np.asarray(p); y=np.asarray(y); bins=[]
    for lo,hi in zip(np.linspace(0,1,6)[:-1],np.linspace(0,1,6)[1:]):
        z=(p>=lo)&((p<hi) if hi<1 else (p<=hi))
        if z.any(): bins.append(abs(float(p[z].mean())-float(y[z].mean())))
    return float(np.mean(bins)) if bins else None
def run():
    d=pd.read_csv(PRED); d=d[d.season.astype(str).isin(["2024-25","2025-26"])].copy()
    d["actual_home"]=(d.home_goals>d.away_goals).astype(int); d["actual_draw"]=(d.home_goals==d.away_goals).astype(int); d["actual_away"]=(d.home_goals<d.away_goals).astype(int); d["actual_over25"]=(d.home_goals+d.away_goals>2).astype(int)
    out={"games":len(d),"seasons":{},"markets":{}}
    for s in ["2024-25","2025-26","combined"]:
        x=d if s=="combined" else d[d.season.astype(str)==s]; out["seasons"][s]={"games":len(x)}
        for name,p,y in [("1x2_home",x.p_home,x.actual_home),("1x2_draw",x.p_draw,x.actual_draw),("1x2_away",x.p_away,x.actual_away),("over25",x.p_over25,x.actual_over25)]:
            out["seasons"][s][name]={"brier":brier(p,y),"calibration_error":cal_error(p,y),"mean_probability":float(p.mean()),"actual_rate":float(y.mean())}
    # Aggregate market summaries: multiclass Brier/log loss and AH -0.5 equivalent to home win.
    p=d[["p_home","p_draw","p_away"]].to_numpy(); actual=np.where(d.actual_home,"H",np.where(d.actual_draw,"D","A")); idx=np.array([{"H":0,"D":1,"A":2}[v] for v in actual]); out["markets"]["1x2"]={"brier":float(np.mean(((p-np.eye(3)[idx])**2).sum(axis=1))),"log_loss":float(-np.mean(np.log(np.clip(p[np.arange(len(p)),idx],1e-15,1)))),"accuracy":float((p.argmax(1)==idx).mean())}
    out["markets"]["over25"]={"brier":brier(d.p_over25,d.actual_over25),"log_loss":float(log_loss(d.actual_over25,d.p_over25,labels=[0,1])),"calibration_error":cal_error(d.p_over25,d.actual_over25)}
    out["markets"]["asian_handicap_home_minus_0_5"]={"brier":brier(d.p_ah_home,d.actual_home),"calibration_error":cal_error(d.p_ah_home,d.actual_home)}
    out["promotion_decision"]="paper_only_pending_closing_line_calibration_and_stability"; REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8"); return out
if __name__=="__main__": print(json.dumps(run(),indent=2))
