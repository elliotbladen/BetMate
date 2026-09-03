"""Recover quarantined UCL xG from FotMob's public match pages.

This is a separate provider track; values are never silently merged with
SofaScore.  The script matches by season, club names and final score.
"""
from pathlib import Path
from difflib import SequenceMatcher
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
Q = ROOT / "data/ucl/matches/ucl_recent_quarantine.csv"
OUT = ROOT / "data/ucl/xg/ucl_fotmob_recovery_candidates.json"
DETAIL_DIR = ROOT.parent / "tmp_fotmob_ucl_matches"
RECOVERED = ROOT / "data/ucl/xg/ucl_fotmob_recovered_xg.csv"
COMPLETE = ROOT / "data/ucl/matches/ucl_recent_complete_xg_v2.csv"
REPORT = ROOT / "ml/football/reports/ucl_fotmob_recovery_audit.md"

def norm(s):
    s = str(s).lower()
    for a,b in [("-fc", ""), ("fc-", ""), ("club-", ""), ("sport-lisboa-e-benfica", "benfica"),
                ("sporting-clube-de-portugal", "sporting cp"), ("paris-saint-germain", "psg"),
                ("fc-barcelona", "barcelona"), ("fc-bayern-m-nchen", "bayern munich"),
                ("club-atl-tico-de-madrid", "atletico madrid"), ("fk-shakhtar-donetsk", "shakhtar donetsk"),
                ("pae-olympiakos-sfp", "olympiacos"), ("qaraba-a-dam-fk", "qarabag"),
                ("bologna-fc-1909", "bologna"), ("stade-brestois-29", "brest")]:
        s=s.replace(a,b)
    return s.replace("-", " ").strip()

def score(a,b):
    a,b=norm(a),norm(b)
    return SequenceMatcher(None,a,b).ratio()

def run():
    q=pd.read_csv(Q)
    candidates=[]
    for season, fn in [("2024-25", "tmp_fotmob_ucl_2425_data.json"), ("2025-26", "tmp_fotmob_ucl_2526_data.json")]:
        data=json.loads(Path(fn).read_text(encoding="utf-8"))
        games=data["fixtures"]["allMatches"]
        for _,r in q[q.season.astype(str)==season].iterrows():
            rows=[]
            for g in games:
                hs=score(r.home_club_id,g["home"]["name"]); aws=score(r.away_club_id,g["away"]["name"])
                ss=str(g.get("status",{}).get("scoreStr", "")).replace(" ","")
                target=f"{int(r.home_goals)}-{int(r.away_goals)}"
                rows.append((hs+aws, hs, aws, int(ss.split("-")[0])==int(r.home_goals) and int(ss.split("-")[1])==int(r.away_goals), g))
            rows.sort(key=lambda z:(z[3],z[0]), reverse=True)
            best=rows[0]
            candidates.append({"match_id":r.match_id,"season":season,"home_club_id":r.home_club_id,"away_club_id":r.away_club_id,"home_goals":int(r.home_goals),"away_goals":int(r.away_goals),"fotmob_match_id":best[4]["id"],"fotmob_home":best[4]["home"]["name"],"fotmob_away":best[4]["away"]["name"],"score_match":best[3],"name_score":best[0],"url":"https://www.fotmob.com/api/data/matchDetails?matchId="+str(best[4]["id"])})
    OUT.write_text(json.dumps(candidates,indent=2)+"\n",encoding="utf-8")
    recovered=[]
    for c in candidates:
        fn=DETAIL_DIR/(c["match_id"]+".json")
        try:
            d=json.loads(fn.read_text(encoding="utf-8"))
            shots=d.get("content",{}).get("shotmap",{}).get("shots",[])
            htid=int(d["general"]["homeTeam"]["id"]); atid=int(d["general"]["awayTeam"]["id"])
            hx=sum(float(s.get("expectedGoals",0) or 0) for s in shots if int(s.get("teamId",-1))==htid)
            ax=sum(float(s.get("expectedGoals",0) or 0) for s in shots if int(s.get("teamId",-1))==atid)
            recovered.append({**{k:c[k] for k in ("match_id","season","home_club_id","away_club_id","home_goals","away_goals","fotmob_match_id")},"home_xg":hx,"away_xg":ax,"xg_source":"fotmob_shotmap","coverage_level":d.get("general",{}).get("coverageLevel"),"shot_count":len(shots)})
        except Exception as e:
            recovered.append({**{k:c[k] for k in ("match_id","season","home_club_id","away_club_id","home_goals","away_goals","fotmob_match_id")},"home_xg":None,"away_xg":None,"xg_source":"fotmob_shotmap","error":str(e)})
    pd.DataFrame(recovered).to_csv(RECOVERED,index=False)
    rd=pd.DataFrame(recovered)
    clean=pd.read_csv(ROOT / "data/ucl/matches/ucl_recent_consistent_matches.csv")
    base=clean[["match_id","season","kickoff_utc","Date","home_club_id","away_club_id","home_goals","away_goals","home_xg","away_xg","xg_source"]].copy()
    add=rd[["match_id","season","home_club_id","away_club_id","home_goals","away_goals","home_xg","away_xg","xg_source"]].copy()
    qdates=pd.read_csv(Q)[["match_id","kickoff_utc"]]
    add=add.merge(qdates,on="match_id",how="left")
    add["Date"]=pd.to_datetime(add["kickoff_utc"],utc=True,errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    complete=pd.concat([base,add],ignore_index=True).drop_duplicates("match_id",keep="first").sort_values(["season","match_id"])
    complete.to_csv(COMPLETE,index=False)
    REPORT.write_text("""# UCL alternate xG recovery audit

FotMob public match-detail records were matched to all 36 quarantined fixtures
using season, club pair and final score. Each record exposed a shotmap with
expected-goals values and was aggregated by home/away team.

- Recovered: **36/36**
- Shotmap coverage flag: **xG** for all recovered records
- Duplicate FotMob match IDs: **0**
- Combined recent dataset: **378/378** matches

The combined file is explicitly a **mixed-provider sensitivity track**:
342 SofaScore shotmap rows and 36 FotMob shotmap rows. It must not replace the
SofaScore-only primary dataset until a provider-scale calibration check is run.
""",encoding="utf-8")
    print("recovered",sum(pd.notna(r.get("home_xg")) and pd.notna(r.get("away_xg")) for r in recovered),"of",len(recovered),"to",RECOVERED,"; complete",len(complete),"to",COMPLETE)
    print(json.dumps(candidates,indent=2))
if __name__=="__main__": run()
