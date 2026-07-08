"""
_clv_weekend.py  -  CLV for R13 NRL + R12 AFL.
CLV% = (odds_taken / close_odds - 1) * 100 for every market type.
For handicap/total: uses closing ODDS for that market (not line points).
"""
import sys, csv, sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import nrl_weekly_clv_report as nrl_clv
import afl_weekly_ml_clv_report as afl_ml

ROOT     = Path(__file__).resolve().parent.parent
BETS     = ROOT / "data" / "bets" / "actual_bets_2026.csv"
NRL_XLSX = ROOT / "outputs" / "nrl_weekly_review" / "historical" / "latest.xlsx"
AFL_XLSX = ROOT / "outputs" / "afl_weekly_review" / "historical" / "latest.xlsx"
NRL_PRICING = ROOT / "results" / "r13_pricing_2026.csv"
AFL_PRICING = ROOT / "results" / "r13_afl_2026.csv"
OUT_NRL  = ROOT / "data" / "clv" / "nrl"
OUT_AFL  = ROOT / "data" / "clv" / "afl"
OUT_NRL.mkdir(parents=True, exist_ok=True)
OUT_AFL.mkdir(parents=True, exist_ok=True)
TODAY = "2026-06-03"

ALIASES = {
    "cronulla sutherland sharks":    "cronulla-sutherland sharks",
    "st george illawarra dragons":   "st. george illawarra dragons",
    "manly warringah sea eagles":    "manly-warringah sea eagles",
    "canterbury bankstown bulldogs": "canterbury-bankstown bulldogs",
}

def norm(s):
    s = (s or "").lower().replace("-"," ").replace(".","").strip()
    return ALIASES.get(s, s)

def short(n): return (n or "").split()[-1]

def fmt(v, d=2):
    try:    return round(float(v), d)
    except: return None

def pct(v):
    return f"{v:+.2f}%" if v is not None else "n/a"

def find_game(xlsx_rows, home, away):
    hn, an = norm(home), norm(away)
    for (d, h, a), v in xlsx_rows.items():
        if norm(h) == hn and norm(a) == an: return v
        if norm(h) == an and norm(a) == hn: return v
    hl, al = hn.split()[-1], an.split()[-1]
    for (d, h, a), v in xlsx_rows.items():
        if norm(h).split()[-1] == hl and norm(a).split()[-1] == al: return v
    return None

# ── load xlsx ──────────────────────────────────────────────────────────────────
print("Loading xlsx files...")
nrl_rows = nrl_clv.load_workbook_rows(NRL_XLSX, 2026)
r13 = {k: v for k, v in nrl_rows.items()
       if hasattr(k[0], "month") and k[0].month == 5 and k[0].day in {29,30,31}}

afl_rows = afl_ml.load_workbook_rows(AFL_XLSX, 2026)
r12_afl = {k: v for k, v in afl_rows.items()
           if hasattr(k[0], "month") and k[0].month == 5 and k[0].day in {28,29,30,31}}

print(f"  NRL R13: {len(r13)} games  |  AFL R12: {len(r12_afl)} games")

# ── load bets ──────────────────────────────────────────────────────────────────
with open(BETS, encoding="utf-8-sig") as f:
    all_bets = list(csv.DictReader(f))

bets = [b for b in all_bets
        if (b["sport"]=="NRL" and b["round"]=="13") or
           (b["sport"]=="AFL" and b["round"]=="12")]
print(f"  Bets: {len(bets)} ({sum(1 for b in bets if b['sport']=='NRL')} NRL R13, {sum(1 for b in bets if b['sport']=='AFL')} AFL R12)\n")


# ══════════════════════════════════════════════════════════════════════════════
#  REPORT 1: ACTUAL BETS CLV
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 72)
print("  REPORT 1: BETS CLV  (CLV% = odds taken / closing odds - 1)")
print("=" * 72)

all_clvs = []
bet_out  = []

for b in bets:
    sport  = b["sport"]
    home   = b["home_team"]
    away   = b["away_team"]
    mkt    = b["market_type"]
    sel    = b["selection"]
    line   = fmt(b.get("line") or "")
    odds   = fmt(b.get("odds_taken") or "")
    result = (b.get("result") or "").upper()
    bid    = b["bet_id"]

    xlsx_rows = r13 if sport == "NRL" else r12_afl
    g  = find_game(xlsx_rows, home, away)
    hs, as_ = short(home), short(away)

    row = {"bet_id": bid, "sport": sport, "home": home, "away": away,
           "market": mkt, "selection": sel, "line": line, "odds_taken": odds,
           "result": result, "open_odds": "", "close_odds": "",
           "open_line": "", "close_line": "", "clv_pct": "", "note": ""}

    print(f"\n{bid}  {sport} | {hs} vs {as_} | {mkt.upper()} | {sel}  odds:{odds}  line:{line}  [{result}]")

    if g is None:
        print("  Game not in xlsx")
        row["note"] = "no match"
        bet_out.append(row)
        continue

    h_sc = fmt(g.get("Home Score"))
    a_sc = fmt(g.get("Away Score"))
    actual_total  = (h_sc + a_sc) if h_sc is not None and a_sc is not None else None
    actual_margin = (h_sc - a_sc) if h_sc is not None and a_sc is not None else None

    is_home = norm(sel) == norm(home)

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

    clv_p   = round((odds / close_o - 1) * 100, 2) if odds and close_o else None
    verdict = "BEAT CLOSE" if clv_p and clv_p > 0 else ("MISSED" if clv_p and clv_p < 0 else "FLAT")

    if mkt in ("handicap", "total"):
        print(f"  Line   open:{open_l}  close:{close_l}  taken:{line}")
    print(f"  Odds   open:{open_o}  close:{close_o}  taken:{odds}")
    print(f"  CLV: {pct(clv_p)}  {verdict}  |  actual: {hs} {h_sc}-{a_sc} {as_}  (total {actual_total})")

    if clv_p is not None: all_clvs.append(clv_p)
    row.update({"open_odds": open_o, "close_odds": close_o,
                "open_line": open_l, "close_line": close_l,
                "clv_pct": clv_p, "note": verdict})
    bet_out.append(row)

print("\n" + "-" * 72)
pos = sum(1 for x in all_clvs if x > 0)
neg = sum(1 for x in all_clvs if x < 0)
avg = round(sum(all_clvs)/len(all_clvs), 2) if all_clvs else 0
print(f"Bets with CLV data : {len(all_clvs)}/{len(bets)}")
print(f"Beat close         : {pos}  Missed: {neg}  ({100*pos//len(all_clvs) if all_clvs else 0}% positive)")
print(f"Average CLV        : {avg:+.2f}%")

p1 = OUT_NRL / f"NRL_AFL_BETS_CLV_R13_R12_{TODAY}.csv"
with open(p1, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(bet_out[0].keys()))
    w.writeheader(); w.writerows(bet_out)
print(f"Saved: {p1.name}")


# ══════════════════════════════════════════════════════════════════════════════
#  REPORT 2: MODEL vs MARKET — all games
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("  REPORT 2: MODEL vs MARKET — NRL R13 + AFL R12 (all games)")
print("=" * 72)

model_out = []

def model_vs_market_game(sport, rnd, home, away, model_margin, model_total,
                          model_h_h2h, model_a_h2h, xlsx_g):
    if not xlsx_g: return None
    h_sc = fmt(xlsx_g.get("Home Score"))
    a_sc = fmt(xlsx_g.get("Away Score"))
    oc_h   = fmt(xlsx_g.get("Home Odds Close"))
    oc_a   = fmt(xlsx_g.get("Away Odds Close"))
    oc_l   = fmt(xlsx_g.get("Home Line Close"))
    oc_t   = fmt(xlsx_g.get("Total Score Close"))
    act_mg = (h_sc - a_sc) if h_sc is not None and a_sc is not None else None
    act_t  = (h_sc + a_sc) if h_sc is not None and a_sc is not None else None

    mg_gap = round(model_margin - oc_l, 1) if model_margin and oc_l else None
    t_gap  = round(model_total - oc_t, 1)  if model_total and oc_t  else None

    hs, as_ = short(home), short(away)
    mg_verdict = "MODEL" if mg_gap and mg_gap > 0 else ("MARKET" if mg_gap and mg_gap < 0 else "FLAT")
    t_verdict  = "MODEL" if t_gap  and t_gap  > 0 else ("MARKET" if t_gap  and t_gap  < 0 else "FLAT")

    print(f"\n  {sport} | {hs} vs {as_}")
    print(f"    Hcap  model:{model_margin:+.1f}  close:{oc_l}  gap:{mg_gap:+.1f}  actual:{act_mg:+.0f}  -> {mg_verdict}")
    print(f"    Total model:{model_total}  close:{oc_t}  gap:{t_gap:+.1f}  actual:{act_t}  -> {t_verdict}")
    print(f"    H2H   model:{model_h_h2h}/{model_a_h2h}  close:{oc_h}/{oc_a}")

    return {"sport": sport, "round": rnd, "home": home, "away": away,
            "model_margin": model_margin, "model_total": model_total,
            "model_h2h_home": model_h_h2h, "model_h2h_away": model_a_h2h,
            "close_line": oc_l, "close_total": oc_t, "close_h2h_home": oc_h, "close_h2h_away": oc_a,
            "hcap_gap": mg_gap, "total_gap": t_gap,
            "actual_margin": act_mg, "actual_total": act_t,
            "hcap_winner": mg_verdict, "total_winner": t_verdict}

if NRL_PRICING.exists():
    with open(NRL_PRICING, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            g = find_game(r13, row["home_team"], row["away_team"])
            r = model_vs_market_game(
                "NRL", 13,
                row["home_team"], row["away_team"],
                fmt(row.get("final_margin")),
                fmt(row.get("final_total") or row.get("pred_total")),
                fmt(row.get("fair_home_odds") or row.get("h2h_home_105")),
                fmt(row.get("fair_away_odds") or row.get("h2h_away_105")),
                g)
            if r: model_out.append(r)

if AFL_PRICING.exists():
    with open(AFL_PRICING, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            g = find_game(r12_afl, row["home_team"], row["away_team"])
            r = model_vs_market_game(
                "AFL", 12,
                row["home_team"], row["away_team"],
                fmt(row.get("rules_margin")),
                fmt(row.get("rules_total")),
                fmt(row.get("rules_home_odds")),
                fmt(row.get("rules_away_odds")),
                g)
            if r: model_out.append(r)

p2 = OUT_NRL / f"MODEL_VS_MARKET_NRL_R13_AFL_R12_{TODAY}.csv"
with open(p2, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(model_out[0].keys()))
    w.writeheader(); w.writerows(model_out)
print(f"\nSaved: {p2.name}")

# Model score
nrl_model_hcap = sum(1 for r in model_out if r["sport"]=="NRL" and r["hcap_winner"]=="MODEL")
nrl_mkt_hcap   = sum(1 for r in model_out if r["sport"]=="NRL" and r["hcap_winner"]=="MARKET")
afl_model_hcap = sum(1 for r in model_out if r["sport"]=="AFL" and r["hcap_winner"]=="MODEL")
afl_mkt_hcap   = sum(1 for r in model_out if r["sport"]=="AFL" and r["hcap_winner"]=="MARKET")
print(f"  NRL hcap: model {nrl_model_hcap} market {nrl_mkt_hcap} | AFL hcap: model {afl_model_hcap} market {afl_mkt_hcap}")


# ══════════════════════════════════════════════════════════════════════════════
#  REPORT 3: ML SHADOW vs MARKET — AFL R12 (from DB)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("  REPORT 3: ML SHADOW vs MARKET — AFL R12")
print("  (NRL shadow not in DB for R13 — AFL only)")
print("=" * 72)

db = sqlite3.connect(str(ROOT / "data" / "model.db"))
db.row_factory = sqlite3.Row
shadow_rows = db.execute(
    "SELECT * FROM afl_shadow_predictions WHERE season=2026 AND round_number=12 ORDER BY game_date, home_team"
).fetchall()
db.close()
print(f"  AFL R12 shadow records: {len(shadow_rows)}")

shadow_out = []
ml_wins = mkt_wins = ties = 0

for s in shadow_rows:
    sd = dict(s)
    g  = find_game(r12_afl, sd.get("home_team",""), sd.get("away_team",""))
    hs, as_ = short(sd.get("home_team","")), short(sd.get("away_team",""))

    ml_mg  = fmt(sd.get("ml_margin")   or sd.get("rules_margin"))
    ml_tot = fmt(sd.get("ml_total")    or sd.get("rules_total"))
    ml_h   = fmt(sd.get("ml_home_odds")or sd.get("rules_home_odds"))
    ml_a   = fmt(sd.get("ml_away_odds")or sd.get("rules_away_odds"))
    rl_mg  = fmt(sd.get("rules_margin"))

    oc_l   = fmt(g.get("Home Line Close"))   if g else None
    oc_t   = fmt(g.get("Total Score Close")) if g else None
    oc_h   = fmt(g.get("Home Odds Close"))   if g else None
    h_sc   = fmt(g.get("Home Score"))        if g else None
    a_sc   = fmt(g.get("Away Score"))        if g else None
    act_mg = (h_sc - a_sc) if h_sc is not None and a_sc is not None else None
    act_t  = (h_sc + a_sc) if h_sc is not None and a_sc is not None else None

    ml_gap_l = round(ml_mg  - oc_l, 1) if ml_mg  and oc_l else None
    ml_gap_t = round(ml_tot - oc_t, 1) if ml_tot and oc_t else None
    div_mg   = round(abs(ml_mg - rl_mg), 1) if ml_mg and rl_mg else None

    # Was ML right direction on handicap?
    if ml_gap_l and act_mg is not None:
        if (ml_gap_l > 0 and act_mg > oc_l) or (ml_gap_l < 0 and act_mg < oc_l):
            ml_hcap_ok = "ML correct"
            ml_wins += 1
        elif (ml_gap_l > 0 and act_mg < oc_l) or (ml_gap_l < 0 and act_mg > oc_l):
            ml_hcap_ok = "Market correct"
            mkt_wins += 1
        else:
            ml_hcap_ok = "Push"
            ties += 1
    else:
        ml_hcap_ok = "?"

    print(f"\n  {hs} vs {as_}")
    ml_gap_l_s = f"{ml_gap_l:+.1f}" if ml_gap_l is not None else "n/a"
    ml_gap_t_s = f"{ml_gap_t:+.1f}" if ml_gap_t is not None else "n/a"
    print(f"    ML margin: {ml_mg:+.1f}  Rules: {rl_mg:+.1f}  Div: {div_mg}  Close line: {oc_l}  ML gap: {ml_gap_l_s}")
    print(f"    ML total:  {ml_tot}  Close total: {oc_t}  ML gap: {ml_gap_t_s}")
    print(f"    ML H2H:    {ml_h}/{ml_a}  Close H2H: {oc_h}")
    act_mg_s = f"{act_mg:+.0f}" if act_mg is not None else "?"
    print(f"    Actual:    {hs} {h_sc}-{a_sc} {as_}  (margin {act_mg_s}, total {act_t})  -> {ml_hcap_ok}")

    sr = {k: sd[k] for k in sd}
    sr.update({"close_line": oc_l, "close_total": oc_t, "close_h2h_home": oc_h,
               "ml_gap_line": ml_gap_l, "ml_gap_total": ml_gap_t,
               "actual_margin": act_mg, "actual_total": act_t, "hcap_verdict": ml_hcap_ok})
    shadow_out.append(sr)

print(f"\n  ML shadow hcap: {ml_wins} correct / {mkt_wins} market / {ties} push")

p3 = OUT_AFL / f"AFL_R12_ML_SHADOW_VS_MARKET_{TODAY}.csv"
with open(p3, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(shadow_out[0].keys()))
    w.writeheader(); w.writerows(shadow_out)
print(f"Saved: {p3.name}")


# ══════════════════════════════════════════════════════════════════════════════
#  RUNNING TOTAL
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("  RUNNING TOTAL — all bets with CLV data to date")
print("=" * 72)

clv_bets = [b for b in bet_out if b.get("clv_pct") != ""]
by_round = {}
for b in all_bets:
    key = f"{b['sport']} R{b['round']}"
    if key not in by_round: by_round[key] = []
    by_round[key].append(b)

# Summarise from bet_out for this weekend
this_wknd_clvs = [b["clv_pct"] for b in bet_out if b.get("clv_pct") != "" and b["clv_pct"] is not None]
avg_wknd = round(sum(this_wknd_clvs)/len(this_wknd_clvs), 2) if this_wknd_clvs else 0
pos_wknd = sum(1 for x in this_wknd_clvs if x > 0)

print(f"\n  This weekend (NRL R13 + AFL R12):")
print(f"    Bets with CLV : {len(this_wknd_clvs)}")
print(f"    Beat close    : {pos_wknd}/{len(this_wknd_clvs)}")
print(f"    Avg CLV       : {avg_wknd:+.2f}%")

print("\n" + "=" * 72)
print("  ALL DONE")
print("=" * 72)
