"""Populate a dated, shrinkage-ready provisional UCL strength table.

External UEFA/ClubElo priors are deliberately not fabricated.  This table is
the observed UCL prior used for diagnostics until those official snapshots are
available.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
MATCH=ROOT/"data/ucl/matches/ucl_matches_openfootball_repaired.csv"
OUT=ROOT/"data/ucl/context/ucl_provisional_strength_priors.csv"
REPORT=ROOT/"ml/football/reports/step2_ucl_strength_population.json"

def run():
    m=pd.read_csv(MATCH)
    m["Date"]=pd.to_datetime(m["kickoff_utc"],utc=True,errors="coerce")
    rows=[]
    for club in sorted(set(m.home_club_id)|set(m.away_club_id)):
        h=m[m.home_club_id.eq(club)]; a=m[m.away_club_id.eq(club)]
        gf=float(h.home_goals.sum()+a.away_goals.sum()); ga=float(h.away_goals.sum()+a.home_goals.sum()); n=len(h)+len(a)
        # Add-one/two smoothing prevents extreme estimates for small samples.
        attack=float(np.log((gf+1.0)/(n+2.0)/1.35))
        defence=float(np.log((ga+1.0)/(n+2.0)/1.35))
        ppg=float((3*(h.home_goals>h.away_goals).sum()+3*(a.away_goals>a.home_goals).sum()+((h.home_goals==h.away_goals).sum())+((a.away_goals==a.home_goals).sum()))/max(n,1))
        rows.append({"club_id":club,"season":"all-history","as_of_utc":"2026-09-03T00:00:00Z","attack":attack,"defence":defence,"league_adjustment":0.0,"uefa_prior":ppg,"matches":n,"source":"ucl_observed_provisional","source_published_at_utc":"2026-09-03T00:00:00Z","external_uefa_prior_available":False,"external_domestic_strength_available":False})
    out=pd.DataFrame(rows).sort_values("club_id"); OUT.parent.mkdir(parents=True,exist_ok=True); out.to_csv(OUT,index=False)
    report={"status":"provisional_complete_external_prior_pending","clubs":len(out),"matches":len(m),"output":str(OUT.relative_to(ROOT)).replace('\\','/'),"external_uefa_prior_available":False,"external_domestic_strength_available":False,"fabricated_external_rows":0,"activation":"diagnostic only; do not replace ClubElo/UEFA prior until dated external snapshots are imported"}
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); print(json.dumps(report,indent=2))
if __name__=="__main__": run()
