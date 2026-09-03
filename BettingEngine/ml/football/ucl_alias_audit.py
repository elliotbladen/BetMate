"""Create auditable free-odds to model club-name alias suggestions."""
from pathlib import Path
import json
from difflib import SequenceMatcher
import pandas as pd
from .ucl_market_backtest import team_key

ROOT=Path(__file__).resolve().parents[2]
ODDS=ROOT/"data/ucl/markets/ucl_free_unverified_1x2.csv"; PRED=ROOT/"data/ucl/clv/ucl_walk_forward_predictions.csv"
OUT=ROOT/"data/ucl/context/ucl_club_alias_audit.csv"; REPORT=ROOT/"ml/football/reports/ucl_alias_audit.json"

def run():
    o=pd.read_csv(ODDS); p=pd.read_csv(PRED)
    odds_names=sorted(set(o.home_club_id)|set(o.away_club_id)); model_names=sorted(set(p.home_club_id)|set(p.away_club_id))
    rows=[]
    for name in odds_names:
        scores=sorted(((SequenceMatcher(None,team_key(name),team_key(candidate)).ratio(),candidate) for candidate in model_names),reverse=True)
        for rank,(score,candidate) in enumerate(scores[:3],1): rows.append({"odds_club_id":name,"candidate_rank":rank,"model_club_id":candidate,"similarity":round(score,4),"manual_decision":""})
    out=pd.DataFrame(rows); OUT.parent.mkdir(parents=True,exist_ok=True); out.to_csv(OUT,index=False)
    result={"status":"ucl_alias_audit_candidates_created","odds_clubs":len(odds_names),"model_clubs":len(model_names),"candidates":len(out),"manual_review_required":True,"output":str(OUT.relative_to(ROOT))}
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8"); return result
if __name__=="__main__": print(json.dumps(run(),indent=2))
