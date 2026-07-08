"""H2H scorecard — NRL R13 + AFL R12. Market vs model vs actual."""
import sys, csv, sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import nrl_weekly_clv_report as nrl_clv
import afl_weekly_ml_clv_report as afl_ml

ROOT     = Path(__file__).resolve().parent.parent
NRL_XLSX = ROOT / "outputs" / "nrl_weekly_review" / "historical" / "latest.xlsx"
AFL_XLSX = ROOT / "outputs" / "afl_weekly_review" / "historical" / "latest.xlsx"
NRL_R13  = ROOT / "results" / "r13_pricing_2026.csv"
AFL_R12  = ROOT / "results" / "r12_afl_2026.csv"
BETS     = ROOT / "data" / "bets" / "actual_bets_2026.csv"

ALIASES = {
    "cronulla sutherland sharks":    "cronulla-sutherland sharks",
    "st george illawarra dragons":   "st. george illawarra dragons",
    "manly warringah sea eagles":    "manly-warringah sea eagles",
    "canterbury bankstown bulldogs": "canterbury-bankstown bulldogs",
    "gws giants": "greater western sydney giants",
    "greater western sydney": "greater western sydney giants",
}
def norm(s):
    s = (s or "").lower().replace("-"," ").replace(".","").strip()
    return ALIASES.get(s, s)
def short(n): return (n or "").split()[-1]
def fmt(v):
    try:    return round(float(v), 2)
    except: return None

# ── load xlsx ──────────────────────────────────────────────────────────────────
nrl_rows = nrl_clv.load_workbook_rows(NRL_XLSX, 2026)
r13 = {k: v for k, v in nrl_rows.items()
       if hasattr(k[0],"month") and k[0].month==5 and k[0].day in {29,30,31}}

afl_rows = afl_ml.load_workbook_rows(AFL_XLSX, 2026)
r12_afl = {k: v for k, v in afl_rows.items()
           if hasattr(k[0],"month") and k[0].month==5 and k[0].day in {28,29,30,31}}

def find(xlsx_rows, home, away):
    hn, an = norm(home), norm(away)
    for (d,h,a),v in xlsx_rows.items():
        if norm(h)==hn and norm(a)==an: return v
        if norm(h)==an and norm(a)==hn: return v
    hl,al = hn.split()[-1], an.split()[-1]
    for (d,h,a),v in xlsx_rows.items():
        if norm(h).split()[-1]==hl and norm(a).split()[-1]==al: return v
    return None

# ── load user H2H bets ─────────────────────────────────────────────────────────
with open(BETS, encoding="utf-8-sig") as f:
    all_bets = list(csv.DictReader(f))

user_h2h = {}  # norm(home)+norm(away) -> selection
for b in all_bets:
    if b["market_type"] != "h2h": continue
    if not ((b["sport"]=="NRL" and b["round"]=="13") or
            (b["sport"]=="AFL" and b["round"]=="12")): continue
    key = (norm(b["home_team"]), norm(b["away_team"]))
    user_h2h.setdefault(key, []).append({
        "sel": b["selection"], "odds": fmt(b.get("odds_taken")),
        "result": b.get("result","").upper()
    })

def get_user_bet(home, away):
    key = (norm(home), norm(away))
    return user_h2h.get(key) or user_h2h.get((norm(away), norm(home)))

# ── build scorecard ────────────────────────────────────────────────────────────
games = []

# NRL R13
with open(NRL_R13, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        home, away = row["home_team"], row["away_team"]
        g = find(r13, home, away)
        if not g: continue

        h_sc = fmt(g.get("Home Score"))
        a_sc = fmt(g.get("Away Score"))
        oc_h = fmt(g.get("Home Odds Close"))
        oc_a = fmt(g.get("Away Odds Close"))
        model_h = fmt(row.get("fair_home_odds") or row.get("h2h_home_105"))
        model_a = fmt(row.get("fair_away_odds") or row.get("h2h_away_105"))

        actual_winner = home if h_sc and a_sc and h_sc > a_sc else (away if a_sc and h_sc and a_sc > h_sc else "DRAW")
        market_pick   = home if oc_h and oc_a and oc_h < oc_a else away
        model_pick    = home if model_h and model_a and model_h < model_a else away

        games.append({
            "sport":"NRL","home":home,"away":away,
            "close_h":oc_h,"close_a":oc_a,
            "model_h":model_h,"model_a":model_a,
            "actual":actual_winner,"market_pick":market_pick,"model_pick":model_pick,
            "user_bets": get_user_bet(home, away)
        })

# AFL R12
with open(AFL_R12, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        home, away = row["home_team"], row["away_team"]
        g = find(r12_afl, home, away)
        if not g: continue

        h_sc = fmt(g.get("Home Score"))
        a_sc = fmt(g.get("Away Score"))
        oc_h = fmt(g.get("Home Odds Close"))
        oc_a = fmt(g.get("Away Odds Close"))
        model_h = fmt(row.get("rules_home_odds"))
        model_a = fmt(row.get("rules_away_odds"))

        actual_winner = home if h_sc and a_sc and h_sc > a_sc else (away if a_sc and h_sc and a_sc > h_sc else "DRAW")
        market_pick   = home if oc_h and oc_a and oc_h < oc_a else away
        model_pick    = home if model_h and model_a and model_h < model_a else away

        games.append({
            "sport":"AFL","home":home,"away":away,
            "close_h":oc_h,"close_a":oc_a,
            "model_h":model_h,"model_a":model_a,
            "actual":actual_winner,"market_pick":market_pick,"model_pick":model_pick,
            "user_bets": get_user_bet(home, away)
        })

# ── print ──────────────────────────────────────────────────────────────────────
print()
print("=" * 90)
print("  H2H SCORECARD — NRL R13 + AFL R12")
print("  Market fav (close) vs Model fav (rules) vs Actual winner")
print("=" * 90)
print(f"  {'Game':<38} {'Mkt':<20} {'Model':<20} {'Actual':<20} {'Mkt':>5} {'Mdl':>5} {'You':>5}")
print("  " + "-" * 86)

mkt_correct = mdl_correct = user_correct = user_total = 0

for g in games:
    hs, as_ = short(g["home"]), short(g["away"])
    actual_s = short(g["actual"])
    mkt_s    = short(g["market_pick"])
    mdl_s    = short(g["model_pick"])

    mkt_ok = "✓" if g["market_pick"] == g["actual"] else "✗"
    mdl_ok = "✓" if g["model_pick"]  == g["actual"] else "✗"
    if g["market_pick"] == g["actual"]: mkt_correct += 1
    if g["model_pick"]  == g["actual"]: mdl_correct += 1

    # user bet
    ub = g["user_bets"]
    user_s = ""
    if ub:
        for bet in ub:
            sel_s  = short(bet["sel"])
            res    = bet["result"]
            odds   = bet["odds"]
            user_s += f"{sel_s}@{odds}({res}) "
            user_total += 1
            if res == "WIN": user_correct += 1

    game_str = f"{hs} vs {as_}"
    mkt_line  = f"{mkt_s} ({g['close_h']}/{g['close_a']})"
    mdl_line  = f"{mdl_s} ({g['model_h']}/{g['model_a']})"

    print(f"  [{g['sport']}] {game_str:<34} {mkt_line:<20} {mdl_line:<20} {actual_s:<20} {mkt_ok:>5} {mdl_ok:>5}  {user_s}")

n = len(games)
print("  " + "-" * 86)
print(f"  {'TOTAL':<38} {'':20} {'':20} {'':20} {mkt_correct}/{n}  {mdl_correct}/{n}  {user_correct}/{user_total}")
print()
print(f"  Market correct : {mkt_correct}/{n} ({100*mkt_correct//n}%)")
print(f"  Model correct  : {mdl_correct}/{n} ({100*mdl_correct//n}%)")
if user_total:
    print(f"  Your H2H bets  : {user_correct}/{user_total} ({100*user_correct//user_total}%)")
print()
