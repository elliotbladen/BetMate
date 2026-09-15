#!/usr/bin/env python3
"""Build an APPEARANCE-FILTERED T5 absence list for Championship GW8.

The documented lesson (GW7): 62 of ~110 published Championship absentees had made ZERO
appearances that season, so their absence is already priced into the Dixon-Coles rating
and feeding them to T5 subtracts them twice.

The rating cannot see a FRESH injury though — a player who featured in the games that
built the rating and is now out. So T5 should carry exactly those, and nothing else.

Filter, applied to every published absentee:
  1. featured (any minutes) in at least one of their club's last TWO completed matches
  2. started >= 60% of the club's matches they appeared in
Anything failing either test is already in the ratings and is EXCLUDED.
"""
import json, sys, unicodedata, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STATS = ROOT/"ml/football/data/championship/player_layer/player_match_stats_espn_2026.csv"
OUT = ROOT/"outputs/football/championship/2026-27/gw08/_supporting/gw08_t5_audit.json"

# sportsgambler.com/injuries/football/england-championship, retrieved 2026-09-15
PUBLISHED = {
 "Birmingham":[("Marc Leonard","CM","ankle")],
 "Blackburn":[("Augustus Kargbo","FW","calf"),("Lewis Miller","CM","ankle (ret 15 Nov)")],
 "Bristol City":[("Luke McNally","CB","lower leg")],
 "Charlton":[("Joshua Edwards","CB","ankle")],
 "Derby":[("Patrick Agyemang","ST","ankle")],
 "Millwall":[("Benicio Baker-Boaitey","FW","undisclosed")],
 "Norwich":[("Mirko Topic","CM","cruciate"),("Gabriel Forsyth","CM","knee")],
 "Portsmouth":[("Franco Umeh-Chibueze","FW","hamstring"),("Mark Kosznovszky","CM","knee")],
 "QPR":[("Karamoko Dembele","AM","knee")],
 "Southampton":[("Mads Roerslev","RB","knee")],
 "Swansea":[("Zeidane Inoussa","FW","undisclosed")],
 "West Ham":[("Tomas Soucek","CM","ankle")],
}
NO_ABSENCES = ["Bolton","Burnley","Cardiff","Lincoln","Middlesbrough","Preston",
               "Sheffield United","Stoke","Watford","West Brom","Wolves","Wrexham"]

def norm(s):
    s=unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode()
    return re.sub(r"[^a-z ]","",s.lower()).strip()

d=pd.read_csv(STATS)
d["ko"]=pd.to_datetime(d.kickoff,errors="coerce",utc=True)
d["pn"]=d.player_name.map(norm)
print(f"appearance data: {d.event_id.nunique()} fixtures to {d.ko.max().date()}\n")

audit=[]; keep={}
for club, players in PUBLISHED.items():
    cd=d[d.team==club]
    if cd.empty:
        # club label mismatch — try a contains match
        cand=[t for t in d.team.unique() if norm(club) in norm(t) or norm(t) in norm(club)]
        if cand: cd=d[d.team==cand[0]]
    last2=sorted(cd.ko.unique())[-2:]
    for name,pos,reason in players:
        # Full-name match within the club ONLY. A surname-contains fallback was tried
        # and removed: it matched Millwall's Leonard to Birmingham's Marc Leonard, QPR's
        # Edwards to Charlton's Joshua Edwards, and Derby's Forsyth to Norwich's Gabriel
        # Forsyth — three false positives out of three hits.
        pr=cd[cd.pn==norm(name)]
        apps=len(pr); starts=int(pr.starter.sum()) if apps else 0
        recent=bool(apps and pr[pr.ko.isin(last2)].shape[0]>0)
        start_rate=(starts/apps) if apps else 0.0
        inc = recent and start_rate>=0.60
        audit.append(dict(club=club,player=name,pos=pos,reason=reason,apps=apps,
                          starts=starts,start_rate=round(start_rate,2),
                          featured_last2=recent,included=inc))
        if inc: keep.setdefault(club,[]).append((name,pos))

print(f"{'club':16s} {'player':26s} {'pos':4s} {'apps':>4s} {'starts':>6s} {'start%':>7s} {'last2':>6s}  verdict")
for a in audit:
    print(f"{a['club']:16s} {a['player'][:25]:26s} {a['pos']:4s} {a['apps']:>4d} {a['starts']:>6d} "
          f"{a['start_rate']*100:>6.0f}% {str(a['featured_last2']):>6s}  "
          f"{'T5 ✓ fresh' if a['included'] else 'excluded — already in the ratings'}")
inc=sum(1 for a in audit if a['included'])
print(f"\n  published {len(audit)} · INCLUDED {inc} · excluded {len(audit)-inc}")
print(f"  clubs with no published absence: {len(NO_ABSENCES)}")
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps({"generated":"2026-09-15","source":"sportsgambler 15 Sep 2026",
    "filter":"featured in one of last 2 completed matches AND started >=60% of appearances",
    "audit":audit,"t5_absences":{k:[list(x) for x in v] for k,v in keep.items()},
    "clubs_no_published_absence":NO_ABSENCES},indent=2),encoding="utf-8")
print(f"  wrote {OUT}")
