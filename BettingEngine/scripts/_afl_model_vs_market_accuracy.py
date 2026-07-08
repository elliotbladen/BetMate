"""
AFL Model vs Market Accuracy — R8, R9, R11, R12
Rules engine + ML shadow vs market closing line on H2H, handicap, totals.
"""
import sys, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import afl_weekly_ml_clv_report as afl_ml

ROOT     = Path(__file__).resolve().parent.parent
AFL_XLSX = ROOT / "outputs" / "afl_weekly_review" / "historical" / "latest.xlsx"
PRICING  = ROOT / "data" / "pricing" / "afl"
RESULTS  = ROOT / "results"

# Two formats: older pricing CSVs (no actuals) vs results CSVs (has actuals + ML)
ROUNDS = {
    8:  {"file": PRICING / "AFL_PRICING_R08_2026-05-05.csv",  "fmt": "old", "month": 4, "days": {30}   | set(range(1,4))},
    9:  {"file": PRICING / "AFL_PRICING_R09_2026-05-12.csv",  "fmt": "old", "month": 5, "days": set(range(7,11))},
    11: {"file": RESULTS  / "r11_afl_2026.csv",               "fmt": "new", "month": 5, "days": set(range(21,25))},
    12: {"file": RESULTS  / "r12_afl_2026.csv",               "fmt": "new", "month": 5, "days": set(range(28,32))},
}

ALIASES = {
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
print("Loading AFL xlsx...")
all_xlsx = afl_ml.load_workbook_rows(AFL_XLSX, 2026)
print(f"  {len(all_xlsx)} total game rows\n")

def get_xlsx(home, away, month, days):
    hn, an = norm(home), norm(away)
    for (d, h, a), v in all_xlsx.items():
        if not (hasattr(d,"month") and d.month == month and d.day in days): continue
        if norm(h) == hn and norm(a) == an: return v
        if norm(h) == an and norm(a) == hn: return v
    hl, al = hn.split()[-1], an.split()[-1]
    for (d, h, a), v in all_xlsx.items():
        if not (hasattr(d,"month") and d.month == month and d.day in days): continue
        if norm(h).split()[-1] == hl and norm(a).split()[-1] == al: return v
    return None

def get_xlsx_any_month(home, away, days_map):
    """For R8 spanning April/May."""
    hn, an = norm(home), norm(away)
    for (d, h, a), v in all_xlsx.items():
        if not hasattr(d,"month"): continue
        ok = (d.month == 4 and d.day in {30}) or (d.month == 5 and d.day in {1,2,3})
        if not ok: continue
        if norm(h) == hn and norm(a) == an: return v
        if norm(h) == an and norm(a) == hn: return v
    hl, al = hn.split()[-1], an.split()[-1]
    for (d, h, a), v in all_xlsx.items():
        if not hasattr(d,"month"): continue
        ok = (d.month == 4 and d.day in {30}) or (d.month == 5 and d.day in {1,2,3})
        if not ok: continue
        if norm(h).split()[-1] == hl and norm(a).split()[-1] == al: return v
    return None

# ── accumulators ───────────────────────────────────────────────────────────────
h2h_model_correct = h2h_ml_correct = h2h_mkt_correct = h2h_total = 0
hcap_model_dir = hcap_ml_dir = hcap_total = 0
hcap_model_mae = hcap_ml_mae = hcap_mkt_mae = 0.0
tot_model_dir = tot_ml_dir = tot_total = 0
tot_model_mae = tot_ml_mae = tot_mkt_mae = 0.0

all_games = []

# ── process rounds ─────────────────────────────────────────────────────────────
for rnd, cfg in ROUNDS.items():
    if not cfg["file"].exists():
        print(f"  R{rnd}: file not found — skipping"); continue

    with open(cfg["file"], encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.DictReader(f))

    rnd_games = 0
    for row in rows:
        if cfg["fmt"] == "old":
            home         = row.get("home_team","")
            away         = row.get("away_team","")
            model_margin = fmt(row.get("final_margin"))
            model_total  = None  # older format doesn't have total
            model_h_odds = fmt(row.get("home_odds"))
            model_a_odds = fmt(row.get("away_odds"))
            ml_margin    = None
            ml_total     = None
            ml_h_odds    = None
            act_margin   = None
            act_total    = None
        else:
            home         = row.get("home_team","")
            away         = row.get("away_team","")
            model_margin = fmt(row.get("rules_margin"))
            model_total  = fmt(row.get("rules_total"))
            model_h_odds = fmt(row.get("rules_home_odds"))
            model_a_odds = fmt(row.get("rules_away_odds"))
            ml_margin    = fmt(row.get("ml_margin"))
            ml_total     = fmt(row.get("ml_total"))
            ml_h_odds    = None
            act_margin   = fmt(row.get("actual_margin"))
            act_total    = fmt(row.get("actual_total"))

        # get xlsx for closing lines + actuals
        if rnd == 8:
            g = get_xlsx_any_month(home, away, None)
        else:
            g = get_xlsx(home, away, cfg["month"], cfg["days"])

        if g:
            h_sc = fmt(g.get("Home Score"))
            a_sc = fmt(g.get("Away Score"))
            if h_sc is not None and a_sc is not None:
                act_margin = round(h_sc - a_sc, 1)
                act_total  = round(h_sc + a_sc, 1)
            close_line   = fmt(g.get("Home Line Close"))
            close_total  = fmt(g.get("Total Score Close"))
            close_h_odds = fmt(g.get("Home Odds Close"))
            close_a_odds = fmt(g.get("Away Odds Close"))
        else:
            close_line = close_total = close_h_odds = close_a_odds = None

        if act_margin is None: continue  # no result yet

        actual_winner = "home" if act_margin > 0 else ("away" if act_margin < 0 else "draw")
        hs, as_ = short(home), short(away)

        rec = {"round": rnd, "home": home, "away": away,
               "model_margin": model_margin, "ml_margin": ml_margin,
               "model_total": model_total, "ml_total": ml_total,
               "close_line": close_line, "close_total": close_total,
               "close_h_odds": close_h_odds, "close_a_odds": close_a_odds,
               "act_margin": act_margin, "act_total": act_total,
               "actual_winner": actual_winner}

        # H2H
        if model_h_odds and model_a_odds and close_h_odds and close_a_odds:
            model_pick = "home" if model_h_odds < model_a_odds else "away"
            mkt_pick   = "home" if close_h_odds  < close_a_odds  else "away"
            m_ok = model_pick == actual_winner
            k_ok = mkt_pick   == actual_winner
            rec.update({"h2h_model_ok": m_ok, "h2h_mkt_ok": k_ok,
                        "model_pick": model_pick, "mkt_pick": mkt_pick})
            if m_ok: h2h_model_correct += 1
            if k_ok: h2h_mkt_correct   += 1
            h2h_total += 1

        # Handicap
        if model_margin is not None and close_line is not None:
            m_dir   = "home" if model_margin > close_line else "away"
            act_dir = "home" if act_margin   > close_line else ("away" if act_margin < close_line else "push")
            m_ok    = m_dir == act_dir
            m_mae   = abs(model_margin - act_margin)
            k_mae   = abs(close_line   - act_margin)
            rec.update({"hcap_model_dir_ok": m_ok, "hcap_model_mae": m_mae, "hcap_mkt_mae": k_mae})
            if m_ok: hcap_model_dir += 1
            hcap_model_mae += m_mae
            hcap_mkt_mae   += k_mae
            hcap_total += 1

            if ml_margin is not None:
                ml_dir = "home" if ml_margin > close_line else "away"
                ml_ok  = ml_dir == act_dir
                ml_mae_v = abs(ml_margin - act_margin)
                rec.update({"hcap_ml_dir_ok": ml_ok, "hcap_ml_mae": ml_mae_v})
                if ml_ok: hcap_ml_dir += 1
                hcap_ml_mae += ml_mae_v

        # Totals
        if model_total is not None and close_total is not None and act_total is not None:
            m_dir   = "over" if model_total > close_total else "under"
            act_dir = "over" if act_total   > close_total else ("under" if act_total < close_total else "push")
            m_ok    = m_dir == act_dir
            m_mae   = abs(model_total - act_total)
            k_mae   = abs(close_total - act_total)
            rec.update({"tot_model_dir_ok": m_ok, "tot_model_mae": m_mae, "tot_mkt_mae": k_mae})
            if m_ok: tot_model_dir += 1
            tot_model_mae += m_mae
            tot_mkt_mae   += k_mae
            tot_total += 1

            if ml_total is not None:
                ml_dir = "over" if ml_total > close_total else "under"
                ml_ok  = ml_dir == act_dir
                ml_mae_v = abs(ml_total - act_total)
                rec.update({"tot_ml_dir_ok": ml_ok, "tot_ml_mae": ml_mae_v})
                if ml_ok: tot_ml_dir += 1
                tot_ml_mae += ml_mae_v

        all_games.append(rec)
        rnd_games += 1

    print(f"  R{rnd}: {rnd_games} games processed")

# ── results ────────────────────────────────────────────────────────────────────
n = len(all_games)
ml_hcap_n = sum(1 for g in all_games if "hcap_ml_dir_ok" in g)
ml_tot_n  = sum(1 for g in all_games if "tot_ml_dir_ok"  in g)

print(f"\nTotal games: {n}  (R8, R9, R11, R12 — R7 pre-dates xlsx, R10 no pricing file)")

print()
print("=" * 70)
print("  H2H — CORRECT WINNER")
print("=" * 70)
print(f"  Model  : {h2h_model_correct}/{h2h_total}  ({100*h2h_model_correct/h2h_total:.1f}%)" if h2h_total else "  n/a")
print(f"  Market : {h2h_mkt_correct}/{h2h_total}  ({100*h2h_mkt_correct/h2h_total:.1f}%)"    if h2h_total else "  n/a")
if h2h_total:
    print(f"  Edge   : model {(h2h_model_correct-h2h_mkt_correct)/h2h_total*100:+.1f}% vs market")

print()
print("=" * 70)
print("  HANDICAP")
print("=" * 70)
if hcap_total:
    avg_m = hcap_model_mae/hcap_total
    avg_k = hcap_mkt_mae/hcap_total
    print(f"  Direction accuracy (model right side of close?)")
    print(f"    Rules  : {hcap_model_dir}/{hcap_total}  ({100*hcap_model_dir/hcap_total:.1f}%)")
    if ml_hcap_n:
        print(f"    ML     : {hcap_ml_dir}/{ml_hcap_n}  ({100*hcap_ml_dir/ml_hcap_n:.1f}%)  [{ml_hcap_n} games with ML]")
    print(f"    Market : {hcap_total//2}/{hcap_total}  (50.0%)  ← baseline")
    print(f"  Mean Absolute Error vs actual margin")
    print(f"    Rules  : {avg_m:.1f} pts")
    if ml_hcap_n:
        print(f"    ML     : {hcap_ml_mae/ml_hcap_n:.1f} pts")
    print(f"    Market : {avg_k:.1f} pts")
    print(f"    Edge   : rules {avg_k-avg_m:+.1f} pts vs market")

print()
print("=" * 70)
print("  TOTALS")
print("=" * 70)
if tot_total:
    avg_m = tot_model_mae/tot_total
    avg_k = tot_mkt_mae/tot_total
    print(f"  Direction accuracy")
    print(f"    Rules  : {tot_model_dir}/{tot_total}  ({100*tot_model_dir/tot_total:.1f}%)")
    if ml_tot_n:
        print(f"    ML     : {tot_ml_dir}/{ml_tot_n}  ({100*tot_ml_dir/ml_tot_n:.1f}%)  [{ml_tot_n} games with ML]")
    print(f"    Market : {tot_total//2}/{tot_total}  (50.0%)  ← baseline")
    print(f"  Mean Absolute Error vs actual total")
    print(f"    Rules  : {avg_m:.1f} pts")
    if ml_tot_n:
        print(f"    ML     : {tot_ml_mae/ml_tot_n:.1f} pts")
    print(f"    Market : {avg_k:.1f} pts")
    print(f"    Edge   : rules {avg_k-avg_m:+.1f} pts vs market")

print()
print("=" * 70)
print("  GAME BY GAME")
print("=" * 70)
print(f"  {'Rd':<4} {'Game':<36} {'H2H':^12} {'Hcap (rules/ML)':^22} {'Total (rules/ML)':^22}")
print("  " + "-" * 96)

for g in all_games:
    hs, as_ = short(g["home"]), short(g["away"])
    game_str = f"R{g['round']} {hs} v {as_}"

    h2h_str = ""
    if "h2h_model_ok" in g:
        m = "✓" if g["h2h_model_ok"] else "✗"
        k = "✓" if g["h2h_mkt_ok"]   else "✗"
        h2h_str = f"M:{m} K:{k}"

    hcap_str = ""
    if "hcap_model_dir_ok" in g and g.get("model_margin") is not None and g.get("close_line") is not None:
        gap = round(g["model_margin"] - g["close_line"], 1)
        d   = "✓" if g["hcap_model_dir_ok"] else "✗"
        ml_part = ""
        if "hcap_ml_dir_ok" in g and g.get("ml_margin") is not None:
            ml_gap = round(g["ml_margin"] - g["close_line"], 1)
            ml_d   = "✓" if g["hcap_ml_dir_ok"] else "✗"
            ml_part = f"/ML{ml_gap:+.0f}({ml_d})"
        hcap_str = f"{gap:+.1f}({d}){ml_part}"

    tot_str = ""
    if "tot_model_dir_ok" in g and g.get("model_total") is not None and g.get("close_total") is not None:
        gap = round(g["model_total"] - g["close_total"], 1)
        d   = "✓" if g["tot_model_dir_ok"] else "✗"
        ml_part = ""
        if "tot_ml_dir_ok" in g and g.get("ml_total") is not None:
            ml_gap = round(g["ml_total"] - g["close_total"], 1)
            ml_d   = "✓" if g["tot_ml_dir_ok"] else "✗"
            ml_part = f"/ML{ml_gap:+.0f}({ml_d})"
        tot_str = f"{gap:+.1f}({d}){ml_part}"

    print(f"  {game_str:<40} {h2h_str:<12} {hcap_str:<24} {tot_str}")

# ── save ───────────────────────────────────────────────────────────────────────
OUT = ROOT / "data" / "clv" / "afl" / "AFL_MODEL_ACCURACY_R8_R12_2026-06-03.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)
fields = ["round","home","away","model_margin","ml_margin","close_line","act_margin",
          "h2h_model_ok","h2h_mkt_ok","hcap_model_dir_ok","hcap_ml_dir_ok",
          "hcap_model_mae","hcap_ml_mae","hcap_mkt_mae",
          "model_total","ml_total","close_total","act_total",
          "tot_model_dir_ok","tot_ml_dir_ok","tot_model_mae","tot_ml_mae","tot_mkt_mae"]
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader(); w.writerows(all_games)
print(f"\nSaved: {OUT.name}")
