import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]; JOIN=ROOT/"data/ucl/clv/ucl_free_market_join.csv"; REPORT=ROOT/"ml/football/reports/step3_ucl_robustness.json"
def group(d):
 out=[]
 for key,g in d.groupby("group"):
  out.append({"group":str(key),"matches":len(g),"model_accuracy":float(g.model_correct.mean()),"market_accuracy":float(g.market_correct.mean()),"mean_edge":float(g.max_edge.mean()),"roi":float(g.flat_return.mean())})
 return out
def run():
 d=pd.read_csv(JOIN); d["group"]=d["season"].astype(str); seasonal=group(d); d["group"]=d["stage"].astype(str); stages=group(d)
 report={"status":"ucl_step3_robustness_complete","matches":len(d),"by_season":seasonal,"by_stage":stages,"minimum_group_warning":"groups under 30 matches are descriptive only","tier_status":{"T0":"active","T1":"results-only baseline","T2":"player shadow data pending","T3_plus":"shadow/diagnostic"},"restrictions":["51 joined matches","archived closing odds","no significance claims","no staking promotion"]}
 REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); return report
if __name__=="__main__": print(json.dumps(run(),indent=2))
