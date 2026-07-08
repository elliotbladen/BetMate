"""CLV for NRL R12 bets. CLV% = odds_taken / close_odds - 1."""
import sys, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import nrl_weekly_clv_report as nrl_clv

ROOT     = Path(__file__).resolve().parent.parent
NRL_XLSX = ROOT / "outputs" / "nrl_weekly_review" / "historical" / "latest.xlsx"
BETS     = ROOT / "data" / "bets" / "actual_bets_2026.csv"
MASTER   = ROOT / "data" / "clv" / "running" / "actual_bets_clv_2026.csv"

R12_DAYS = {21, 22, 23, 24, 25}  # May

ALIASES = {
    "cronulla sutherland sharks":    "cronulla-sutherland sharks",
    "st george illawarra dragons":   "st. george illawarra dragons",
    "manly warringah sea eagles":    "manly-warringah sea eagles",
    "manly sea eagles":              "manly-warringah sea eagles",
    "canterbury bankstown bulldogs": "canterbury-bankstown bulldogs",
    "canterbury bulldogs":           "canterbury-bankstown bulldogs",
}
def norm(s):
    s = (s or "").lower().replace("-"," ").replace(".","").strip()
    return ALIASES.get(s, s)
def short(n): return (n or "").split()[-1]
def fmt(v):
    try:    return round(float(v), 2)
    except: return None
def pct(v): return f"{v:+.2f}%" if v is not None else "n/a"

# ── xlsx ───────────────────────────────────────────────────────────────────────
print("Loading NRL xlsx...")
nrl_rows = nrl_clv.load_workbook_rows(NRL_XLSX, 2026)
r12 = {k: v for k, v in nrl_rows.items()
       if hasattr(k[0],"month") and k[0].month==5 and k[0].day in R12_DAYS}
print(f"  R12 games in xlsx: {len(r12)}")

def find(home, away):
    hn, an = norm(home), norm(away)
    for (d,h,a),v in r12.items():
        if norm(h)==hn and norm(a)==an: return v
        if norm(h)==an and norm(a)==hn: return v
    hl,al = hn.split()[-1], an.split()[-1]
    for (d,h,a),v in r12.items():
        if norm(h).split()[-1]==hl and norm(a).split()[-1]==al: return v
    return None

# ── bets ───────────────────────────────────────────────────────────────────────
with open(BETS, encoding="utf-8-sig") as f:
    bets = [b for b in csv.DictReader(f) if b["sport"]=="NRL" and b["round"]=="12"]
print(f"  R12 NRL bets: {len(bets)}\n")

# ── master ─────────────────────────────────────────────────────────────────────
with open(MASTER, encoding="utf-8-sig") as f:
    master_rows = list(csv.DictReader(f))
    master_fields = list(master_rows[0].keys())
    master_ids = {r["bet_id"] for r in master_rows}

# ── CLV ────────────────────────────────────────────────────────────────────────
all_clvs = []
new_rows = []

print("=" * 72)
print("  NRL R12 — BETS CLV")
print("=" * 72)

for b in bets:
    bid    = b["bet_id"]
    home   = b["home_team"]
    away   = b["away_team"]
    mkt    = b["market_type"]
    sel    = b["selection"]
    line   = fmt(b.get("line") or "")
    odds   = fmt(b.get("odds_taken") or "")
    result = (b.get("result") or "").upper()

    g = find(home, away)
    hs, as_ = short(home), short(away)

    print(f"\n{bid}  NRL R12 | {hs} vs {as_} | {mkt.upper()} | {sel}  odds:{odds}  line:{line}  [{result}]")

    if g is None:
        print("  ⚠ Not found in xlsx")
        new_rows.append({"bet_id":bid,"sport":"NRL","round":"12",
            "match":f"{hs} v {as_}","market":mkt,"selection":sel,
            "line":line,"odds_taken":odds,"open_line":"","close_line":"",
            "line_move":"","close_odds":"","clv_pct":"","clv_line":"",
            "pnl":b.get("pnl",""),"result":result})
        continue

    h_sc = fmt(g.get("Home Score"))
    a_sc = fmt(g.get("Away Score"))
    act_mg  = round(h_sc-a_sc,1) if h_sc is not None and a_sc is not None else None
    act_tot = round(h_sc+a_sc,1) if h_sc is not None and a_sc is not None else None
    is_home = norm(sel)==norm(home)

    if mkt == "h2h":
        open_o  = fmt(g.get("Home Odds Open"  if is_home else "Away Odds Open"))
        close_o = fmt(g.get("Home Odds Close" if is_home else "Away Odds Close"))
        open_l = close_l = ""
    elif mkt == "handicap":
        open_o  = fmt(g.get("Home Line Odds Open"  if is_home else "Away Line Odds Open"))
        close_o = fmt(g.get("Home Line Odds Close" if is_home else "Away Line Odds Close"))
        open_l  = fmt(g.get("Home Line Open"  if is_home else "Away Line Open"))
        close_l = fmt(g.get("Home Line Close" if is_home else "Away Line Close"))
    elif mkt == "total":
        is_over = sel == "over"
        open_o  = fmt(g.get("Total Score Over Open"  if is_over else "Total Score Under Open"))
        close_o = fmt(g.get("Total Score Over Close" if is_over else "Total Score Under Close"))
        open_l  = fmt(g.get("Total Score Open"))
        close_l = fmt(g.get("Total Score Close"))
    else:
        open_o = close_o = open_l = close_l = None

    clv_p = round((odds/close_o-1)*100, 2) if odds and close_o else None
    verdict = "BEAT CLOSE" if clv_p and clv_p>0 else ("MISSED" if clv_p and clv_p<0 else "FLAT")

    if mkt in ("handicap","total"):
        print(f"  Line   open:{open_l}  close:{close_l}  taken:{line}")
    print(f"  Odds   open:{open_o}  close:{close_o}  taken:{odds}")
    print(f"  CLV: {pct(clv_p)}  {verdict}  |  actual: {hs} {h_sc}-{a_sc} {as_} (margin {act_mg:+.0f}, total {act_tot})")

    if clv_p is not None: all_clvs.append(clv_p)

    pnl = b.get("pnl","") or ""
    if not pnl:
        try:
            stake = float(b.get("stake","25") or 25)
            if result=="WIN":  pnl = str(round(stake*odds-stake,2))
            elif result=="LOSS": pnl = str(round(-stake,2))
        except: pass

    lm = ""
    try:
        lm = str(round(float(close_l)-float(open_l),1)) if open_l and close_l else ""
    except: pass

    new_rows.append({"bet_id":bid,"sport":"NRL","round":"12",
        "match":f"{hs} v {as_}","market":mkt,"selection":sel,
        "line":line,"odds_taken":odds,"open_line":open_l,"close_line":close_l,
        "line_move":lm,"close_odds":close_o,"clv_pct":clv_p,"clv_line":"",
        "pnl":pnl,"result":result})

print("\n" + "-"*72)
pos = sum(1 for x in all_clvs if x>0)
avg = round(sum(all_clvs)/len(all_clvs),2) if all_clvs else 0
print(f"Bets with CLV : {len(all_clvs)}/{len(bets)}")
print(f"Beat close    : {pos}/{len(all_clvs)}")
print(f"Avg CLV       : {avg:+.2f}%")

# ── append to master ───────────────────────────────────────────────────────────
added = 0
for r in new_rows:
    if r["bet_id"] not in master_ids:
        master_rows.append(r); master_ids.add(r["bet_id"]); added += 1

with open(MASTER, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=master_fields, extrasaction="ignore")
    w.writeheader(); w.writerows(master_rows)
print(f"\nMaster: {added} rows added ({len(master_rows)} total)")
