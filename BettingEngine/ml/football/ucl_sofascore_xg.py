"""Download match-level UCL xG from the public SofaScore event endpoints."""
from pathlib import Path
import json, ssl, urllib.request, time
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/"data/ucl/xg/ucl_sofascore_match_xg.csv"; CACHE=ROOT/"data/ucl/xg/sofascore_cache"; CTX=ssl._create_unverified_context()
SEASONS={"2024-25":61644,"2025-26":76953}
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"BetMate research client"})
    return json.loads(urllib.request.urlopen(req,context=CTX,timeout=30).read())
def run():
    rows=[]; CACHE.mkdir(parents=True,exist_ok=True)
    for season,sid in SEASONS.items():
        events=[]
        for page in range(12):
            try: d=get(f"https://www.sofascore.com/api/v1/unique-tournament/7/season/{sid}/events/last/{page}")
            except Exception: break
            batch=d.get("events",[]); events += batch
            if not d.get("hasNextPage") or not batch: break
        seen=set()
        for e in events:
            eid=e.get("id");
            if not eid or eid in seen: continue
            seen.add(eid); hp=e.get("homeScore",{}); ap=e.get("awayScore",{}); x=None
            try:
                sm=get(f"https://www.sofascore.com/api/v1/event/{eid}/shotmap"); shots=sm.get("shotmap",[]); hx=sum(float(s.get("xg",0) or 0) for s in shots if s.get("isHome")); ax=sum(float(s.get("xg",0) or 0) for s in shots if not s.get("isHome")); x=(hx,ax)
            except Exception: continue
            rows.append({"event_id":eid,"season":season,"kickoff_utc":e.get("startTimestamp"),"home_team":e.get("homeTeam",{}).get("name"),"away_team":e.get("awayTeam",{}).get("name"),"home_goals":hp.get("current"),"away_goals":ap.get("current"),"home_xg":x[0],"away_xg":x[1],"xg_source":"sofascore_shotmap"})
            time.sleep(.05)
    out=pd.DataFrame(rows).drop_duplicates("event_id"); OUT.parent.mkdir(parents=True,exist_ok=True); out.to_csv(OUT,index=False); return {"rows":len(out),"seasons":out.season.value_counts().to_dict() if len(out) else {},"output":str(OUT.relative_to(ROOT)).replace("\\","/")}
if __name__=="__main__": print(json.dumps(run(),indent=2))
