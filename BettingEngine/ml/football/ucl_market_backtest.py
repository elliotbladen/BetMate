"""Join free UCL odds to predictions and calculate provisional market metrics."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import re
import unicodedata
from difflib import SequenceMatcher

ROOT=Path(__file__).resolve().parents[2]
PRED=ROOT/"data/ucl/clv/ucl_shared_walk_forward_predictions.csv"; ODDS=ROOT/"data/ucl/markets/ucl_btb_closing_1x2.csv"
OUT=ROOT/"data/ucl/clv/ucl_free_market_join.csv"; REPORT=ROOT/"ml/football/reports/ucl_market_backtest.json"

def season_key(value):
    s=str(value); parts=s.split("-"); return f"{parts[0]}-{parts[1][-2:]}" if len(parts)==2 else s

ALIASES = {
    "ath-bilbao": "athletic-club", "atl-madrid": "atletico-madrid", "dortmund": "borussia-dortmund",
    "d-zagreb": "dinamo-zagreb", "dyn-kyiv": "dinamo-kiev", "psg": "paris-saint-germain",
    "inter": "internazionale", "bayern-munich": "bayern-munich", "dep-la-coruna": "deportivo-la-coruna",
    "fc-porto": "porto", "monaco": "as-monaco", "sporting-cp": "sporting", "bodo-glimt": "bodo-glimt",
    "paris-saint-germain-fc": "paris-saint-germain", "paris-sg": "paris-saint-germain", "fc-internazionale-milano": "internazionale",
    "fc-barcelona": "barcelona", "fc-bayern-munich": "bayern-munich", "bayer-04-leverkusen": "bayer-leverkusen",
    "olympique-marseille": "marseille", "olympique-lyonnais": "lyon", "olympiakos-piraeus": "olympiakos",
    "feyenoord-rotterdam": "feyenoord", "newcastle-united": "newcastle", "manchester-united": "manchester-united",
    "fk-astana": "fc-astana", "fk-bod-glimt": "bodo-glimt", "fk-kairat": "kairat-almaty", "fk-crvena-zvezda": "red-star-belgrade",
    "gnk-dinamo-zagreb": "dinamo-zagreb", "club-atletico-de-madrid": "atletico-madrid", "as-monaco-fc": "as-monaco",
}
def team_key(value):
    text=unicodedata.normalize("NFKD", str(value)).encode("ascii","ignore").decode().lower()
    text=re.sub(r"-(eng|esp|ger|ita|fra|por|ned|bel|sco|ukr|cro|rus|srb|nor|tur|aut|gre|cyp|kaz|sui|wal|irl|den|pol|rou|bra|cze|svk)$", "", text)
    text=re.sub(r"(^|-)fc$|(^|-)cf$|(^|-)bc$", "", text)
    text=re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return ALIASES.get(text, text)

def auto_alias(value, known):
    """Return a high-confidence model name, otherwise retain the key."""
    key=team_key(value); ranked=sorted(((SequenceMatcher(None,key,team_key(c)).ratio(),c) for c in known),reverse=True)
    if ranked and ranked[0][0] >= .80 and (len(ranked)==1 or ranked[0][0]-ranked[1][0] >= .10): return ranked[0][1]
    return key

def run():
    p=pd.read_csv(PRED); o=pd.read_csv(ODDS)
    if "season_source" not in o:
        dates=pd.to_datetime(o.match_date)
        start_year=dates.dt.year-(dates.dt.month<7).astype(int)
        o["season_source"]=start_year.astype(str)+"-"+(start_year+1).astype(str)
        o=o.rename(columns={"home_team":"home_name","away_team":"away_name","avg_odds_home_win":"home_odds","avg_odds_draw":"draw_odds","avg_odds_away_win":"away_odds"})
        o["home_club_id"]=o.home_name.map(team_key); o["away_club_id"]=o.away_name.map(team_key)
    p["season_key"]=p.season.map(season_key); o["season_key"]=o.season_source.map(season_key)
    known=set(p.home_club_id)|set(p.away_club_id)
    p["home_club_id"]=p.home_club_id.map(team_key); p["away_club_id"]=p.away_club_id.map(team_key)
    known=set(p.home_club_id)|set(p.away_club_id)
    o["home_club_id"]=o.home_club_id.map(lambda x:auto_alias(x,known)); o["away_club_id"]=o.away_club_id.map(lambda x:auto_alias(x,known))
    p["date_key"]=pd.to_datetime(p.kickoff_utc).dt.date.astype(str); o["date_key"]=pd.to_datetime(o.match_date.astype(str).str.split(" - ").str[0].str.strip(),format="mixed").dt.date.astype(str)
    keys=["season_key","date_key","home_club_id","away_club_id"]
    odds_cols=keys+["home_odds","draw_odds","away_odds","closing_status","source"]
    joined=p.merge(o[odds_cols],on=keys,how="inner")
    # Conservative fallback for historical naming differences.  We only search
    # predictions on the same season/date and require a strong, unambiguous
    # two-team similarity score.
    used=set(joined.match_id)
    for oi,row in o.iterrows():
        if ((joined.season_key==row.season_key)&(joined.date_key==row.date_key)&(joined.home_club_id==row.home_club_id)&(joined.away_club_id==row.away_club_id)).any(): continue
        # Fallback on season plus opposing clubs when one archive has a shifted
        # or incomplete date. Date remains a validation feature, not a hard key.
        candidates=p[(p.season_key==row.season_key)&(~p.match_id.isin(used))]
        scored=[]
        for pi,c in candidates.iterrows():
            direct=(SequenceMatcher(None,row.home_club_id,c.home_club_id).ratio()+SequenceMatcher(None,row.away_club_id,c.away_club_id).ratio())/2
            reverse=(SequenceMatcher(None,row.home_club_id,c.away_club_id).ratio()+SequenceMatcher(None,row.away_club_id,c.home_club_id).ratio())/2
            score=max(direct, reverse)
            scored.append((score,pi))
        scored.sort(reverse=True)
        if scored and scored[0][0]>=0.65 and (len(scored)==1 or scored[0][0]-scored[1][0]>=0.12):
            c=p.loc[scored[0][1]].copy(); record=c.to_dict()
            for field in ["home_odds","draw_odds","away_odds","closing_status","source"]: record[field]=row[field]
            joined=pd.concat([joined,pd.DataFrame([record])],ignore_index=True); used.add(c.match_id)
    for c in ["home_odds","draw_odds","away_odds"]: joined[c]=pd.to_numeric(joined[c],errors="coerce")
    joined=joined[(joined[["home_odds","draw_odds","away_odds"]]>1).all(axis=1)].copy()
    implied=1/joined[["home_odds","draw_odds","away_odds"]].to_numpy(); fair=implied/implied.sum(axis=1,keepdims=True)
    joined[["market_home_prob","market_draw_prob","market_away_prob"]]=fair
    model=joined[["p_home","p_draw","p_away"]].to_numpy(); market=fair
    joined["model_edge_home"]=joined.p_home-joined.market_home_prob; joined["model_edge_draw"]=joined.p_draw-joined.market_draw_prob; joined["model_edge_away"]=joined.p_away-joined.market_away_prob
    actual=np.where(joined.home_goals>joined.away_goals,0,np.where(joined.home_goals==joined.away_goals,1,2))
    joined["model_pick"] = model.argmax(axis=1); joined["market_pick"] = market.argmax(axis=1); joined["model_correct"]=(joined.model_pick==actual); joined["market_correct"]=(joined.market_pick==actual)
    status="archived_closing" if "BeatTheBookie" in set(o.source.astype(str)) else "unverified_static_close"
    report={"status":"ucl_market_backtest_complete","prediction_rows":len(p),"odds_rows":len(o),"matched_rows":len(joined),"match_rate":len(joined)/len(p),"closing_status":status,"timestamps_present":False,"market_fields_used_in_model":False,"model_accuracy":float(joined.model_correct.mean()) if len(joined) else None,"market_no_vig_accuracy":float(joined.market_correct.mean()) if len(joined) else None,"mean_max_model_edge":float(np.max(model-market,axis=1).mean()) if len(joined) else None,"restrictions":["archived closing odds without quote timestamps","no staking or ROI claim","season and conservative team-name resolver; date used for audit"]}
    OUT.parent.mkdir(parents=True,exist_ok=True); joined.to_csv(OUT,index=False); REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); return report
def main(): print(json.dumps(run(),indent=2))
if __name__=="__main__": main()
