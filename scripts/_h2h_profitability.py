import openpyxl, os, glob, csv
from datetime import datetime, date, timedelta
from collections import defaultdict

NRL_CANON = {
    "broncos":"broncos","raiders":"raiders","bulldogs":"bulldogs",
    "sharks":"sharks","dolphins":"dolphins","titans":"titans",
    "eagles":"sea eagles","sea eagles":"sea eagles","storm":"storm",
    "warriors":"warriors","knights":"knights","cowboys":"cowboys",
    "eels":"eels","panthers":"panthers","rabbitohs":"rabbitohs",
    "dragons":"dragons","roosters":"roosters","tigers":"tigers",
}
AFL_CANON = {
    "adelaide":"adelaide","crows":"adelaide",
    "brisbane":"brisbane","lions":"brisbane",
    "carlton":"carlton","blues":"carlton",
    "collingwood":"collingwood","magpies":"collingwood",
    "essendon":"essendon","bombers":"essendon",
    "fremantle":"fremantle","dockers":"fremantle",
    "geelong":"geelong","cats":"geelong",
    "gold coast":"gold coast","suns":"gold coast",
    "gws":"gws","giants":"gws",
    "hawthorn":"hawthorn","hawks":"hawthorn",
    "melbourne":"melbourne","demons":"melbourne",
    "north melbourne":"north melbourne","kangaroos":"north melbourne",
    "port adelaide":"port adelaide","power":"port adelaide",
    "richmond":"richmond","tigers":"richmond",
    "st kilda":"st kilda","saints":"st kilda",
    "sydney":"sydney","swans":"sydney",
    "west coast":"west coast","eagles":"west coast",
    "western bulldogs":"western bulldogs",
}

def canon(name, sport):
    n = name.lower().strip()
    m = NRL_CANON if sport=="NRL" else AFL_CANON
    if n in m: return m[n]
    last = n.split()[-1]
    if last in m: return m[last]
    if len(n.split())>=2:
        last2=" ".join(n.split()[-2:])
        if last2 in m: return m[last2]
    first = n.split()[0]
    if first in m: return m[first]
    return n

KNOWN = {
    # AFL R15
    ("2026-06-18","fremantle","geelong"):"home",
    ("2026-06-19","gold coast","hawthorn"):"away",
    ("2026-06-20","adelaide","melbourne"):"home",
    ("2026-06-20","gws","carlton"):"away",
    ("2026-06-20","collingwood","port adelaide"):"home",
    ("2026-06-21","richmond","north melbourne"):"away",
    ("2026-06-21","st kilda","western bulldogs"):"away",
    # NRL R16
    ("2026-06-19","knights","dragons"):"home",
    ("2026-06-20","tigers","dolphins"):"away",
    ("2026-06-20","titans","panthers"):"home",
    ("2026-06-20","bulldogs","sea eagles"):"home",
    ("2026-06-21","warriors","cowboys"):"home",
    ("2026-06-21","storm","raiders"):"home",
    ("2026-06-21","roosters","sharks"):"home",
}

def load_results(path, sport, header_row=2):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    results = {}
    for row in ws.iter_rows(min_row=header_row, values_only=True):
        if not row or not row[0]: continue
        d = row[0]
        if isinstance(d, datetime): d = d.date()
        home=str(row[2]).strip(); away=str(row[3]).strip()
        hs=row[5]; as_=row[6]
        if hs is None or as_ is None: continue
        try: hs,as_=int(hs),int(as_)
        except: continue
        results[(str(d),canon(home,sport),canon(away,sport))] = "home" if hs>as_ else "away"
    wb.close()
    return results

nrl_res = load_results(r"C:\Users\ElliotBladen\Apps\data\nrl\historical\latest.xlsx","NRL",2)
afl_res = load_results(r"C:\Users\ElliotBladen\Apps\BettingEngine\outputs\afl_weekly_review\historical\latest.xlsx","AFL",3)

SNAP_DIR = r"C:\Users\ElliotBladen\Apps\data\odds_snapshots\2026"
game_odds = {}
for fpath in sorted(glob.glob(os.path.join(SNAP_DIR,"*.csv"))):
    snap_date = os.path.basename(fpath).replace(".csv","")
    with open(fpath,encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("market")!="h2h" or row.get("bookmaker")!="tab": continue
            sport=row.get("sport","")
            if sport not in ("NRL","AFL"): continue
            gid=row["game_id"]
            if gid not in game_odds:
                game_odds[gid]={"sport":sport,"home":row["home_team"],"away":row["away_team"],
                                "commence":row["commence_time"][:10],"home_odds":None,"away_odds":None}
            price=float(row["price"]) if row["price"] else None
            if row["outcome"]==row["home_team"] and game_odds[gid]["home_odds"] is None:
                game_odds[gid]["home_odds"]=price
            elif row["outcome"]==row["away_team"] and game_odds[gid]["away_odds"] is None:
                game_odds[gid]["away_odds"]=price

rows=[]
for gid,g in sorted(game_odds.items(),key=lambda x:x[1]["commence"]):
    c=g["commence"]; cd=datetime.strptime(c,"%Y-%m-%d").date()
    if cd>date(2026,6,21) or cd<date(2026,5,7): continue
    ho,ao=g["home_odds"],g["away_odds"]
    if not ho or not ao: continue
    sport=g["sport"]
    hc=canon(g["home"],sport); ac=canon(g["away"],sport)
    fav_side="home" if ho<=ao else "away"
    fav_odds=ho if fav_side=="home" else ao
    winner=KNOWN.get((c,hc,ac))
    if not winner:
        res=nrl_res if sport=="NRL" else afl_res
        winner=res.get((c,hc,ac))
        if not winner:
            for d in [1,-1,2,-2]:
                winner=res.get((str(cd+timedelta(days=d)),hc,ac))
                if winner: break
    pnl=(round(fav_odds-1,4) if winner==fav_side else -1.0) if winner else None
    result="W" if pnl and pnl>0 else ("L" if pnl==-1.0 else "?")
    rows.append({"sport":sport,"date":c,"home":g["home"],"away":g["away"],
                 "fav_side":fav_side,"fav_odds":fav_odds,"result":result,"pnl":pnl})

# Assign round numbers
def get_round(sport, date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    if sport == "NRL":
        if d < date(2026, 5, 12): return "R10"
        if d < date(2026, 5, 19): return "R11"
        if d < date(2026, 5, 26): return "R12"
        if d < date(2026, 6, 2): return "R13"
        if d < date(2026, 6, 9): return "R14"
        if d < date(2026, 6, 16): return "R15"
        return "R16"
    else:  # AFL
        if d < date(2026, 5, 12): return "R9"
        if d < date(2026, 5, 19): return "R10"
        if d < date(2026, 5, 26): return "R11"
        if d < date(2026, 6, 2): return "R12"
        if d < date(2026, 6, 9): return "R13"
        if d < date(2026, 6, 16): return "R14"
        return "R15"

print("\nNRL R10-R16 | Back Favourite $1 Each Game")
print("="*55)
print(f"{'Round':<8} {'G':>3} {'W':>3} {'L':>3} {'P&L':>8} {'ROI':>7}")
print("-"*40)
nrl_total=0; nrl_g=0; nrl_w=0
for rnd in ["R10","R11","R12","R13","R14","R15","R16"]:
    rrows=[r for r in rows if r["sport"]=="NRL" and get_round("NRL",r["date"])==rnd and r["pnl"] is not None]
    if not rrows: continue
    w=sum(1 for r in rrows if r["result"]=="W"); l=len(rrows)-w
    p=sum(r["pnl"] for r in rrows)
    print(f"{rnd:<8} {len(rrows):>3} {w:>3} {l:>3} {p:>+8.2f} {p/len(rrows)*100:>+6.1f}%")
    nrl_total+=p; nrl_g+=len(rrows); nrl_w+=w
print(f"{'TOTAL':<8} {nrl_g:>3} {nrl_w:>3} {nrl_g-nrl_w:>3} {nrl_total:>+8.2f} {nrl_total/nrl_g*100:>+6.1f}%")

print("\nAFL R9-R15 | Back Favourite $1 Each Game")
print("="*55)
print(f"{'Round':<8} {'G':>3} {'W':>3} {'L':>3} {'P&L':>8} {'ROI':>7}")
print("-"*40)
afl_total=0; afl_g=0; afl_w=0
for rnd in ["R9","R10","R11","R12","R13","R14","R15"]:
    rrows=[r for r in rows if r["sport"]=="AFL" and get_round("AFL",r["date"])==rnd and r["pnl"] is not None]
    if not rrows: continue
    w=sum(1 for r in rrows if r["result"]=="W"); l=len(rrows)-w
    p=sum(r["pnl"] for r in rrows)
    print(f"{rnd:<8} {len(rrows):>3} {w:>3} {l:>3} {p:>+8.2f} {p/len(rrows)*100:>+6.1f}%")
    afl_total+=p; afl_g+=len(rrows); afl_w+=w
print(f"{'TOTAL':<8} {afl_g:>3} {afl_w:>3} {afl_g-afl_w:>3} {afl_total:>+8.2f} {afl_total/afl_g*100:>+6.1f}%")

all_g=nrl_g+afl_g; all_w=nrl_w+afl_w; all_p=nrl_total+afl_total
print(f"\nCOMBINED: {all_g} bets | {all_w}W {all_g-all_w}L | P&L: {all_p:+.2f} | ROI: {all_p/all_g*100:+.1f}%")

unk=[r for r in rows if r["pnl"] is None and datetime.strptime(r["date"],"%Y-%m-%d").date()<=date(2026,6,21)]
if unk:
    print(f"\n({len(unk)} unmatched — excluded):")
    for r in unk: print(f"  {r['sport']} {r['date']} {r['home']} vs {r['away']}")
