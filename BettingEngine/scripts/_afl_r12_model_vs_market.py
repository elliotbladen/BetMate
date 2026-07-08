"""AFL R12 model vs market — rules + ML shadow vs closing line."""
import sys, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import nrl_weekly_clv_report as nrl_clv
import afl_weekly_ml_clv_report as afl_ml

ROOT     = Path(__file__).resolve().parent.parent
AFL_XLSX = ROOT / "outputs" / "afl_weekly_review" / "historical" / "latest.xlsx"
AFL_R12  = ROOT / "results" / "r12_afl_2026.csv"
OUT      = ROOT / "data" / "clv" / "afl" / "AFL_R12_MODEL_VS_MARKET_2026-06-03.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

ALIASES = {
    "gws giants": "greater western sydney giants",
    "greater western sydney": "greater western sydney giants",
}
def norm(s):
    s = (s or "").lower().replace("-", " ").replace(".", "").strip()
    return ALIASES.get(s, s)
def short(n): return (n or "").split()[-1]
def fmt(v):
    try:    return round(float(v), 2)
    except: return None
def gs(v, fmt_str="+.1f"):
    return format(v, fmt_str) if v is not None else "—"

afl_rows = afl_ml.load_workbook_rows(AFL_XLSX, 2026)
r12 = {k: v for k, v in afl_rows.items()
       if hasattr(k[0], "month") and k[0].month == 5 and k[0].day in {28,29,30,31}}
print(f"AFL R12 games in xlsx: {len(r12)}")

def find(home, away):
    hn, an = norm(home), norm(away)
    for (d, h, a), v in r12.items():
        if norm(h) == hn and norm(a) == an: return v
        if norm(h) == an and norm(a) == hn: return v
    hl, al = hn.split()[-1], an.split()[-1]
    for (d, h, a), v in r12.items():
        if norm(h).split()[-1] == hl and norm(a).split()[-1] == al: return v
    return None

def direction_ok(model_val, close_val, actual_val):
    if any(x is None for x in [model_val, close_val, actual_val]): return "?"
    m = "home" if model_val > close_val else ("away" if model_val < close_val else "flat")
    a = "home" if actual_val > close_val else ("away" if actual_val < close_val else "push")
    return "MODEL" if m == a else ("FLAT" if m == "flat" else "MARKET")

rows_out = []
print()
print("=" * 80)
print("  AFL R12 — MODEL vs MARKET")
print("  Rules model + ML shadow vs closing line/odds.  actual = final result.")
print("=" * 80)

with open(AFL_R12, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        home = row["home_team"]
        away = row["away_team"]
        g = find(home, away)
        hs, as_ = short(home), short(away)

        rl_mg  = fmt(row.get("rules_margin"))
        rl_tot = fmt(row.get("rules_total"))
        rl_h   = fmt(row.get("rules_home_odds"))
        rl_a   = fmt(row.get("rules_away_odds"))
        ml_mg  = fmt(row.get("ml_margin"))
        ml_tot = fmt(row.get("ml_total"))
        act_mg  = fmt(row.get("actual_margin"))
        act_tot = fmt(row.get("actual_total"))

        if g:
            op_l = fmt(g.get("Home Line Open"))
            oc_l = fmt(g.get("Home Line Close"))
            op_t = fmt(g.get("Total Score Open"))
            oc_t = fmt(g.get("Total Score Close"))
            op_h = fmt(g.get("Home Odds Open"))
            oc_h = fmt(g.get("Home Odds Close"))
            oc_a = fmt(g.get("Away Odds Close"))
            h_sc = fmt(g.get("Home Score"))
            a_sc = fmt(g.get("Away Score"))
            if h_sc is not None and a_sc is not None:
                if act_mg  is None: act_mg  = round(h_sc - a_sc, 1)
                if act_tot is None: act_tot = round(h_sc + a_sc, 1)
        else:
            op_l = oc_l = op_t = oc_t = op_h = oc_h = oc_a = None
            print(f"  ⚠ {hs} vs {as_} not in xlsx")

        rl_hcap_gap = round(rl_mg - oc_l, 1)  if rl_mg  is not None and oc_l  is not None else None
        ml_hcap_gap = round(ml_mg - oc_l, 1)  if ml_mg  is not None and oc_l  is not None else None
        rl_tot_gap  = round(rl_tot - oc_t, 1) if rl_tot is not None and oc_t  is not None else None
        ml_tot_gap  = round(ml_tot - oc_t, 1) if ml_tot is not None and oc_t  is not None else None

        rl_hcap_w = direction_ok(rl_mg,  oc_l, act_mg)
        ml_hcap_w = direction_ok(ml_mg,  oc_l, act_mg)
        rl_tot_w  = direction_ok(rl_tot, oc_t, act_tot)
        ml_tot_w  = direction_ok(ml_tot, oc_t, act_tot)

        print(f"\n  {hs} vs {as_}")
        print(f"    HANDICAP  open:{op_l}  close:{oc_l}  actual:{gs(act_mg)}")
        print(f"              rules:{gs(rl_mg)} (gap {gs(rl_hcap_gap)}) [{rl_hcap_w}]   ML:{gs(ml_mg)} (gap {gs(ml_hcap_gap)}) [{ml_hcap_w}]")
        print(f"    TOTAL     open:{op_t}  close:{oc_t}  actual:{act_tot}")
        print(f"              rules:{rl_tot} (gap {gs(rl_tot_gap)}) [{rl_tot_w}]   ML:{ml_tot} (gap {gs(ml_tot_gap)}) [{ml_tot_w}]")
        print(f"    H2H       rules:{rl_h}/{rl_a}   open:{op_h}  close:{oc_h}/{oc_a}")

        rows_out.append({
            "home": home, "away": away,
            "rules_margin": rl_mg, "ml_margin": ml_mg,
            "open_line": op_l, "close_line": oc_l, "actual_margin": act_mg,
            "rules_hcap_gap": rl_hcap_gap, "ml_hcap_gap": ml_hcap_gap,
            "hcap_rules_winner": rl_hcap_w, "hcap_ml_winner": ml_hcap_w,
            "rules_total": rl_tot, "ml_total": ml_tot,
            "open_total": op_t, "close_total": oc_t, "actual_total": act_tot,
            "rules_total_gap": rl_tot_gap, "ml_total_gap": ml_tot_gap,
            "total_rules_winner": rl_tot_w, "total_ml_winner": ml_tot_w,
            "rules_home_odds": rl_h, "rules_away_odds": rl_a,
            "open_h2h_home": op_h, "close_h2h_home": oc_h, "close_h2h_away": oc_a,
        })

print()
print("=" * 80)
print("  SCORECARD")
print("=" * 80)
rl_hcap_wins = sum(1 for r in rows_out if r["hcap_rules_winner"] == "MODEL")
ml_hcap_wins = sum(1 for r in rows_out if r["hcap_ml_winner"]   == "MODEL")
rl_tot_wins  = sum(1 for r in rows_out if r["total_rules_winner"]== "MODEL")
ml_tot_wins  = sum(1 for r in rows_out if r["total_ml_winner"]   == "MODEL")
n = len(rows_out)
print(f"  Handicap  Rules: {rl_hcap_wins}/{n} correct   ML: {ml_hcap_wins}/{n} correct")
print(f"  Totals    Rules: {rl_tot_wins}/{n} correct    ML: {ml_tot_wins}/{n} correct")

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
    w.writeheader()
    w.writerows(rows_out)
print(f"\nSaved: {OUT}")
