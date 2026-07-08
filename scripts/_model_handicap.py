import openpyxl, csv, glob, os
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

# Known margins NRL R16 + AFL R15
KNOWN = {
    ("2026-06-19","knights","dragons"):+2,
    ("2026-06-20","tigers","dolphins"):-14,
    ("2026-06-20","titans","panthers"):+1,
    ("2026-06-20","bulldogs","sea eagles"):+1,
    ("2026-06-21","warriors","cowboys"):+18,
    ("2026-06-21","storm","raiders"):+22,
    ("2026-06-21","roosters","sharks"):+19,
    ("2026-06-18","fremantle","geelong"):+9,
    ("2026-06-19","gold coast","hawthorn"):-16,
    ("2026-06-20","adelaide","melbourne"):+17,
    ("2026-06-20","gws","carlton"):-23,
    ("2026-06-20","collingwood","port adelaide"):+26,
    ("2026-06-21","richmond","north melbourne"):-25,
    ("2026-06-21","st kilda","western bulldogs"):-22,
}

def load_margins(path, sport, hr=2):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    res = {}
    for row in ws.iter_rows(min_row=hr, values_only=True):
        if not row or not row[0]: continue
        d = row[0]
        if isinstance(d, datetime): d = d.date()
        h=str(row[2]).strip(); a=str(row[3]).strip()
        hs=row[5]; as_=row[6]
        if hs is None or as_ is None: continue
        try: hs,as_=int(hs),int(as_)
        except: continue
        res[(str(d),canon(h,sport),canon(a,sport))] = hs-as_
    wb.close()
    return res

nrl_margins = load_margins(r"C:\Users\ElliotBladen\Apps\data\nrl\historical\latest.xlsx","NRL",2)
afl_margins = load_margins(r"C:\Users\ElliotBladen\Apps\BettingEngine\outputs\afl_weekly_review\historical\latest.xlsx","AFL",3)

# Load model pricing — NRL: fair_hcap_line (neg=home fav), AFL: rules_margin (pos=home wins)
# Model home margin: NRL = -fair_hcap_line, AFL = rules_margin
model_lines = {}  # (sport, home_canon, away_canon) -> model_home_margin

RESULTS_DIR = r"C:\Users\ElliotBladen\Apps\BettingEngine\results"

for fname in glob.glob(os.path.join(RESULTS_DIR, "r*_pricing_2026.csv")):
    rnd_str = os.path.basename(fname).split("r")[1].split("_")[0]; rnd = int(rnd_str)
    with open(fname, encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            h = row.get("home_team","").strip()
            a = row.get("away_team","").strip()
            hcap = row.get("fair_hcap_line","")
            if not h or not a or not hcap: continue
            hc = canon(h,"NRL"); ac = canon(a,"NRL")
            # fair_hcap_line: negative = home giving pts = home fav
            # model home margin = -fair_hcap_line? No.
            # fair_hcap_line = -6.2 means home wins by 6.2
            # so model_home_margin = -hcap? -> -(-6.2) = 6.2 ✅
            # fair_hcap_line = +0.5 means away wins by 0.5
            # so model_home_margin = -(0.5) = -0.5 ✅
            model_lines[("NRL", hc, ac)] = -float(hcap)

for fname in glob.glob(os.path.join(RESULTS_DIR, "r*_afl_2026.csv")):
    with open(fname, encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            h = row.get("home_team","").strip()
            a = row.get("away_team","").strip()
            margin = row.get("rules_margin","")
            if not h or not a or not margin: continue
            hc = canon(h,"AFL"); ac = canon(a,"AFL")
            model_lines[("AFL", hc, ac)] = float(margin)

# Load snapshot spreads
SNAP_DIR = r"C:\Users\ElliotBladen\Apps\data\odds_snapshots\2026"
game_spreads = {}
for fpath in sorted(glob.glob(os.path.join(SNAP_DIR,"*.csv"))):
    with open(fpath, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("market")!="spreads" or row.get("bookmaker")!="tab": continue
            sport=row.get("sport","")
            if sport not in ("NRL","AFL"): continue
            gid=row["game_id"]
            if gid not in game_spreads:
                game_spreads[gid]={"sport":sport,"home":row["home_team"],"away":row["away_team"],
                                   "commence":row["commence_time"][:10],
                                   "home_point":None,"home_price":None,"away_point":None,"away_price":None}
            pt=float(row["point"]) if row["point"] else None
            pr=float(row["price"]) if row["price"] else None
            if row["outcome"]==row["home_team"] and game_spreads[gid]["home_point"] is None:
                game_spreads[gid]["home_point"]=pt; game_spreads[gid]["home_price"]=pr
            elif row["outcome"]==row["away_team"] and game_spreads[gid]["away_point"] is None:
                game_spreads[gid]["away_point"]=pt; game_spreads[gid]["away_price"]=pr

def get_round(sport, ds):
    d=datetime.strptime(ds,"%Y-%m-%d").date()
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
no_model=[]
for gid,g in sorted(game_spreads.items(),key=lambda x:x[1]["commence"]):
    c=g["commence"]; cd=datetime.strptime(c,"%Y-%m-%d").date()
    if cd>date(2026,6,21) or cd<date(2026,5,14): continue  # R11+ only (have model)
    hp,hpr,ap,apr = g["home_point"],g["home_price"],g["away_point"],g["away_price"]
    if hp is None or ap is None: continue
    sport=g["sport"]
    hc=canon(g["home"],sport); ac=canon(g["away"],sport)

    # Get model
    model_hm = model_lines.get((sport,hc,ac))
    if model_hm is None:
        no_model.append(f"{sport} {c} {g['home']} vs {g['away']}")
        continue

    # Market implied home margin = -home_point (home_point neg = home giving pts = home fav)
    mkt_hm = -hp

    # Model bet direction:
    # model_hm > mkt_hm: model rates home better than mkt → home is better value → back HOME
    # model_hm < mkt_hm: model rates away better → back AWAY
    if model_hm > mkt_hm:
        bet_side="home"; bet_odds=hpr or 1.90
    else:
        bet_side="away"; bet_odds=apr or 1.90

    # Get actual margin
    margin = KNOWN.get((c,hc,ac))
    if margin is None:
        margs = nrl_margins if sport=="NRL" else afl_margins
        margin = margs.get((c,hc,ac))
        if margin is None:
            for delta in [1,-1,2,-2]:
                margin = margs.get((str(cd+timedelta(days=delta)),hc,ac))
                if margin is not None: break

    if margin is not None:
        # adjusted = actual home margin + home_point
        # if >0: home covered; if <0: away covered
        adjusted = margin + hp
        home_covered = adjusted > 0
        covered = home_covered if bet_side=="home" else not home_covered
        pnl = round(bet_odds-1,4) if covered else -1.0
        result = "W" if covered else "L"
    else:
        pnl=None; result="?"

    rows.append({"sport":sport,"date":c,"home":g["home"],"away":g["away"],
                 "model_hm":model_hm,"mkt_hm":mkt_hm,"edge":model_hm-mkt_hm,
                 "bet":bet_side,"bet_odds":bet_odds,"result":result,"pnl":pnl})

# Print
for sport,rnds in [("NRL",["R11","R12","R13","R14","R15","R16"]),
                   ("AFL",["R11","R12","R13","R14","R15"])]:
    print(f"\n{sport} | Model-Directed Handicap $1")
    print("="*55)
    print(f"{'Round':<8} {'G':>3} {'W':>3} {'L':>3} {'P&L':>8} {'ROI':>7}")
    print("-"*40)
    tot_g=tot_w=0; tot_p=0.0
    for rnd in rnds:
        rrows=[r for r in rows if r["sport"]==sport and get_round(sport,r["date"])==rnd and r["pnl"] is not None]
        if not rrows: continue
        w=sum(1 for r in rrows if r["result"]=="W")
        p=sum(r["pnl"] for r in rrows)
        print(f"{rnd:<8} {len(rrows):>3} {w:>3} {len(rrows)-w:>3} {p:>+8.2f} {p/len(rrows)*100:>+6.1f}%")
        tot_g+=len(rrows); tot_w+=w; tot_p+=p
    if tot_g:
        print(f"{'TOTAL':<8} {tot_g:>3} {tot_w:>3} {tot_g-tot_w:>3} {tot_p:>+8.2f} {tot_p/tot_g*100:>+6.1f}%")

nr=[r for r in rows if r["sport"]=="NRL" and r["pnl"] is not None]
ar=[r for r in rows if r["sport"]=="AFL" and r["pnl"] is not None]
al=nr+ar
np_=sum(r["pnl"] for r in nr); ap_=sum(r["pnl"] for r in ar)
print(f"\nCOMBINED: {len(al)} bets | {sum(1 for r in al if r['result']=='W')}W {sum(1 for r in al if r['result']=='L')}L | P&L: {np_+ap_:+.2f} | ROI: {(np_+ap_)/len(al)*100:+.1f}%")
if no_model: print(f"\n({len(no_model)} games skipped - no model data)")


