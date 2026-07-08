import openpyxl, os, glob, csv
from datetime import datetime, date, timedelta

NRL_CANON = {
    "broncos":"broncos","raiders":"raiders","bulldogs":"bulldogs",
    "sharks":"sharks","dolphins":"dolphins","titans":"titans",
    "eagles":"sea eagles","sea eagles":"sea eagles","storm":"storm",
    "warriors":"warriors","knights":"knights","cowboys":"cowboys",
    "eels":"eels","panthers":"panthers","rabbitohs":"rabbitohs",
    "dragons":"dragons","roosters":"roosters","tigers":"tigers",
}
AFL_CANON = {
    "adelaide":"adelaide","crows":"adelaide","brisbane":"brisbane","lions":"brisbane",
    "carlton":"carlton","blues":"carlton","collingwood":"collingwood","magpies":"collingwood",
    "essendon":"essendon","bombers":"essendon","fremantle":"fremantle","dockers":"fremantle",
    "geelong":"geelong","cats":"geelong","gold coast":"gold coast","suns":"gold coast",
    "gws":"gws","giants":"gws","hawthorn":"hawthorn","hawks":"hawthorn",
    "melbourne":"melbourne","demons":"melbourne","north melbourne":"north melbourne","kangaroos":"north melbourne",
    "port adelaide":"port adelaide","power":"port adelaide","richmond":"richmond","tigers":"richmond",
    "st kilda":"st kilda","saints":"st kilda","sydney":"sydney","swans":"sydney",
    "west coast":"west coast","eagles":"west coast","western bulldogs":"western bulldogs",
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
    return n

# Known actual margins (home_score - away_score)
KNOWN_MARGIN = {
    ("2026-06-19","knights","dragons"): +2,
    ("2026-06-20","tigers","dolphins"): -14,
    ("2026-06-20","titans","panthers"): +1,
    ("2026-06-20","bulldogs","sea eagles"): +1,
    ("2026-06-21","warriors","cowboys"): +18,
    ("2026-06-21","storm","raiders"): +22,
    ("2026-06-21","roosters","sharks"): +19,
    ("2026-06-18","fremantle","geelong"): +9,
    ("2026-06-19","gold coast","hawthorn"): -16,
    ("2026-06-20","adelaide","melbourne"): +17,
    ("2026-06-20","gws","carlton"): -23,
    ("2026-06-20","collingwood","port adelaide"): +26,
    ("2026-06-21","richmond","north melbourne"): -25,
    ("2026-06-21","st kilda","western bulldogs"): -22,
}

def load_margins(path, sport, header_row=2):
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
        results[(str(d),canon(home,sport),canon(away,sport))] = hs - as_
    wb.close()
    return results

nrl_margins = load_margins(r"C:\Users\ElliotBladen\Apps\data\nrl\historical\latest.xlsx","NRL",2)
afl_margins = load_margins(r"C:\Users\ElliotBladen\Apps\BettingEngine\outputs\afl_weekly_review\historical\latest.xlsx","AFL",3)

# Load spreads data from snapshots
SNAP_DIR = r"C:\Users\ElliotBladen\Apps\data\odds_snapshots\2026"
game_spreads = {}
for fpath in sorted(glob.glob(os.path.join(SNAP_DIR,"*.csv"))):
    with open(fpath,encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("market")!="spreads" or row.get("bookmaker")!="tab": continue
            sport=row.get("sport","")
            if sport not in ("NRL","AFL"): continue
            gid=row["game_id"]
            if gid not in game_spreads:
                game_spreads[gid]={"sport":sport,"home":row["home_team"],"away":row["away_team"],
                                   "commence":row["commence_time"][:10],
                                   "home_point":None,"home_price":None,"away_point":None,"away_price":None}
            pt = float(row["point"]) if row["point"] else None
            pr = float(row["price"]) if row["price"] else None
            if row["outcome"]==row["home_team"] and game_spreads[gid]["home_point"] is None:
                game_spreads[gid]["home_point"]=pt
                game_spreads[gid]["home_price"]=pr
            elif row["outcome"]==row["away_team"] and game_spreads[gid]["away_point"] is None:
                game_spreads[gid]["away_point"]=pt
                game_spreads[gid]["away_price"]=pr

def get_round(sport, date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    if sport=="NRL":
        if d<date(2026,5,12): return "R10"
        if d<date(2026,5,19): return "R11"
        if d<date(2026,5,26): return "R12"
        if d<date(2026,6,2): return "R13"
        if d<date(2026,6,9): return "R14"
        if d<date(2026,6,16): return "R15"
        return "R16"
    else:
        if d<date(2026,5,12): return "R9"
        if d<date(2026,5,19): return "R10"
        if d<date(2026,5,26): return "R11"
        if d<date(2026,6,2): return "R12"
        if d<date(2026,6,9): return "R13"
        if d<date(2026,6,16): return "R14"
        return "R15"

rows=[]
for gid,g in sorted(game_spreads.items(),key=lambda x:x[1]["commence"]):
    c=g["commence"]; cd=datetime.strptime(c,"%Y-%m-%d").date()
    if cd>date(2026,6,21) or cd<date(2026,5,7): continue
    hp,hpr,ap,apr = g["home_point"],g["home_price"],g["away_point"],g["away_price"]
    if hp is None or ap is None: continue
    sport=g["sport"]
    hc=canon(g["home"],sport); ac=canon(g["away"],sport)

    # Handicap fav = team with negative point
    if hp < 0:
        fav_side="home"; fav_team=g["home"]; fav_point=hp; fav_odds=hpr or 1.90
    else:
        fav_side="away"; fav_team=g["away"]; fav_point=ap; fav_odds=apr or 1.90

    # Get actual margin
    margin = KNOWN_MARGIN.get((c,hc,ac))
    if margin is None:
        margs = nrl_margins if sport=="NRL" else afl_margins
        margin = margs.get((c,hc,ac))
        if margin is None:
            for d in [1,-1,2,-2]:
                margin = margs.get((str(cd+timedelta(days=d)),hc,ac))
                if margin is not None: break

    if margin is not None:
        # adjusted = home_margin + home_point (if >0, home covered their spread)
        adjusted = margin + hp
        if fav_side=="home":
            covered = adjusted > 0
        else:
            covered = adjusted < 0
        pnl = round(fav_odds-1,4) if covered else -1.0
        result = "W" if covered else "L"
    else:
        pnl = None; result = "?"

    rows.append({"sport":sport,"date":c,"home":g["home"],"away":g["away"],
                 "fav_team":fav_team,"fav_point":fav_point,"fav_odds":fav_odds,
                 "result":result,"pnl":pnl})

# Print results
for sport,label in [("NRL","R10-R16"),("AFL","R9-R15")]:
    rnds = ["R10","R11","R12","R13","R14","R15","R16"] if sport=="NRL" else ["R9","R10","R11","R12","R13","R14","R15"]
    print(f"\n{sport} {label} | Back Handicap Favourite $1")
    print("="*55)
    print(f"{'Round':<8} {'G':>3} {'W':>3} {'L':>3} {'P&L':>8} {'ROI':>7}")
    print("-"*40)
    tot_g=0; tot_w=0; tot_p=0
    for rnd in rnds:
        rrows=[r for r in rows if r["sport"]==sport and get_round(sport,r["date"])==rnd and r["pnl"] is not None]
        if not rrows: continue
        w=sum(1 for r in rrows if r["result"]=="W")
        p=sum(r["pnl"] for r in rrows)
        print(f"{rnd:<8} {len(rrows):>3} {w:>3} {len(rrows)-w:>3} {p:>+8.2f} {p/len(rrows)*100:>+6.1f}%")
        tot_g+=len(rrows); tot_w+=w; tot_p+=p
    if tot_g:
        print(f"{'TOTAL':<8} {tot_g:>3} {tot_w:>3} {tot_g-tot_w:>3} {tot_p:>+8.2f} {tot_p/tot_g*100:>+6.1f}%")

nrl_rows=[r for r in rows if r["sport"]=="NRL" and r["pnl"] is not None]
afl_rows=[r for r in rows if r["sport"]=="AFL" and r["pnl"] is not None]
all_rows=nrl_rows+afl_rows
npl=sum(r["pnl"] for r in nrl_rows); apl=sum(r["pnl"] for r in afl_rows)
print(f"\nCOMBINED: {len(all_rows)} bets | {sum(1 for r in all_rows if r['result']=='W')}W {sum(1 for r in all_rows if r['result']=='L')}L | P&L: {npl+apl:+.2f} | ROI: {(npl+apl)/len(all_rows)*100:+.1f}%")

unk=[r for r in rows if r["pnl"] is None and datetime.strptime(r["date"],"%Y-%m-%d").date()<=date(2026,6,21)]
if unk: print(f"\n({len(unk)} unmatched excluded)"); [print(f"  {r['sport']} {r['date']} {r['home']} vs {r['away']}") for r in unk]
