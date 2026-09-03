"""Out-of-sample U/O 2.5 calibration using the free historical UCL archive."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
ROOT=Path(__file__).resolve().parents[2]; PRED=ROOT/"data/ucl/clv/ucl_shared_walk_forward_predictions.csv"; OUT=ROOT/"data/ucl/clv/ucl_totals_calibrated_predictions.csv"; REPORT=ROOT/"ml/football/reports/ucl_totals_calibration_backtest.json"
def run():
 d=pd.read_csv(PRED); d["actual_over25"]=(d.home_goals+d.away_goals>2).astype(int); train=d[d.season.astype(str)<"2024-25"]; test=d[d.season.astype(str).isin(["2024-25","2025-26"])].copy(); iso=IsotonicRegression(out_of_bounds="clip").fit(train.p_over25,train.actual_over25); test["p_over25_calibrated"]=np.clip(iso.predict(test.p_over25),.01,.99); test["p_under25_calibrated"]=1-test.p_over25_calibrated
 def score(p,y): return {"brier":float(np.mean((p-y)**2)),"mean_probability":float(np.mean(p)),"actual_rate":float(np.mean(y)),"accuracy":float(((p>=.5)==(y==1)).mean())}
 result={"training_games":len(train),"test_games":len(test),"raw":score(test.p_over25.to_numpy(),test.actual_over25.to_numpy()),"calibrated":score(test.p_over25_calibrated.to_numpy(),test.actual_over25.to_numpy()),"method":"isotonic regression fit on pre-2024/25 predictions","decision":"paper_calibrated_candidate"}; OUT.parent.mkdir(parents=True,exist_ok=True); test.to_csv(OUT,index=False); REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8"); return result
if __name__=="__main__": print(json.dumps(run(),indent=2))
