"""Import BeatTheBookie historical Champions League closing odds."""
import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"data/ucl/markets/ucl_btb_closing_1x2.csv"; REPORT=ROOT/"ml/football/reports/ucl_btb_import.json"
def run(source:Path):
 d=pd.read_csv(source,compression="gzip"); d=d[d.league.eq("Europe: Champions League")].copy(); d["source"]="BeatTheBookie"; d["closing_status"]="confirmed_archive_closing"; d["timestamps_present"]=False
 keep=["match_id","league","match_date","home_team","home_score","away_team","away_score","avg_odds_home_win","avg_odds_draw","avg_odds_away_win","n_odds_home_win","n_odds_draw","n_odds_away_win","source","closing_status","timestamps_present"]
 OUT.parent.mkdir(parents=True,exist_ok=True); d[keep].to_csv(OUT,index=False); r={"status":"ucl_btb_closing_odds_imported","rows":len(d),"date_min":str(d.match_date.min()),"date_max":str(d.match_date.max()),"source":"BeatTheBookie","stable_match_ids":True,"timestamps_present":False,"output":str(OUT.relative_to(ROOT))}; REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8"); return r
if __name__=="__main__":
 import sys; print(json.dumps(run(Path(sys.argv[1])),indent=2))
