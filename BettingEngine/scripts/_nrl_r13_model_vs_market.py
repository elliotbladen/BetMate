"""NRL R13 — Rules model + ML shadow vs closing line/odds."""
import sys, csv, sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import nrl_weekly_clv_report as nrl_clv

ROOT     = Path(__file__).resolve().parent.parent
NRL_XLSX = ROOT / "outputs" / "nrl_weekly_review" / "historical" / "latest.xlsx"
NRL_R13  = ROOT / "results" / "r13_pricing_2026.csv"
OUT      = ROOT / "data" / "clv" / "nrl" / "NRL_R13_MODEL_VS_MARKET_2026-06-03.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

ALIASES = {
    "cronulla sutherland sharks":    "cronulla-sutherland sharks",
    "st george illawarra dragons":   "st. george illawarra dragons",
    "manly warringah sea eagles":    "manly-warringah sea eagles",
    "canterbury bankstown bulldogs": "canterbury-bankstown bulldogs",
}
def norm(s):
    s = (s or "").lower().replace("-", " ").replace(".", "").strip()
    return ALIASES.get(s, s)
def short(n): return (n or "").split()[-1]
def fmt(v):
    try:    return round(float(v), 2)
    except: return None
def gs(v, f="+.1f"): return format(v, f) if v is not None else "—"

def direction_ok(model_val, close_val, actual_val):
    if any(x is None for x in [model_val, close_val, actual_val]): return "?"
    m = "home" if model_val > close_val else ("away" if model_val < close_val else "flat")
    a = "home" if actual_val > close_val else ("away" if actual_val < close_val else "push")
    return "MODEL" if m == a else ("FLAT" if m == "flat" else "MARKET")

# ── xlsx ───────────────────────────────────────────────────────────────────────
nrl_rows = nrl_clv.load_workbook_rows(NRL_XLSX, 2026)
r13 = {k: v for k, v in nrl_rows.items()
       if hasattr(k[0], "month") and k[0].month == 5 and k[0].day in {29, 30, 31}}
print(f"NRL R13 games in xlsx: {len(r13)}")

def find_xlsx(home, away):
    hn, an = norm(home), norm(away)
    for (d, h, a), v in r13.items():
        if norm(h) == hn and norm(a) == an: return v
        if norm(h) == an and norm(a) == hn: return v
    hl, al = hn.split()[-1], an.split()[-1]
    for (d, h, a), v in r13.items():
        if norm(h).split()[-1] == hl and norm(a).split()[-1] == al: return v
    return None

# ── ML shadow from DB ──────────────────────────────────────────────────────────
db = sqlite3.connect(str(ROOT / "data" / "model.db"))
db.row_factory = sqlite3.Row
shadow_rows = db.execute(
    "SELECT s.*, ht.team_name AS home_team, at2.team_name AS away_team "
    "FROM ml_shadow_predictions s "
    "JOIN matches m ON s.match_id = m.match_id "
    "JOIN teams ht ON m.home_team_id = ht.team_id "
    "JOIN teams at2 ON m.away_team_id = at2.team_id "
    "WHERE s.season=2026 AND s.round_number=13"
).fetchall()
db.close()

shadow_by_teams = {}
for s in shadow_rows:
    sd = dict(s)
    key = (norm(sd["home_team"]), norm(sd["away_team"]))
    shadow_by_teams[key] = sd
print(f"ML shadow rows for R13: {len(shadow_by_teams)}")

def find_shadow(home, away):
    hn, an = norm(home), norm(away)
    if (hn, an) in shadow_by_teams: return shadow_by_teams[(hn, an)]
    if (an, hn) in shadow_by_teams: return shadow_by_teams[(an, hn)]
    hl, al = hn.split()[-1], an.split()[-1]
    for (h, a), v in shadow_by_teams.items():
        if h.split()[-1] == hl and a.split()[-1] == al: return v
    return None

# ── main ───────────────────────────────────────────────────────────────────────
rows_out = []
print()
print("=" * 80)
print("  NRL R13 — RULES MODEL + ML SHADOW vs MARKET")
print("  rules = T1-T8 engine  |  ML = XGBoost + T2-T8 overlays")
print("=" * 80)

with open(NRL_R13, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        home = row["home_team"]
        away = row["away_team"]
        g  = find_xlsx(home, away)
        sd = find_shadow(home, away)
        hs, as_ = short(home), short(away)

        rl_mg  = fmt(row.get("final_margin"))
        rl_tot = fmt(row.get("final_total") or row.get("pred_total"))
        rl_h   = fmt(row.get("fair_home_odds") or row.get("h2h_home_105"))
        rl_a   = fmt(row.get("fair_away_odds") or row.get("h2h_away_105"))

        ml_mg  = fmt(sd.get("ml_adj_margin"))   if sd else None
        ml_tot = fmt(sd.get("ml_adj_total"))    if sd else None
        ml_prob = fmt(sd.get("ml_adj_h2h_prob")) if sd else None
        ml_h   = round(1/ml_prob, 2) if ml_prob and ml_prob > 0 else None

        if g:
            op_l  = fmt(g.get("Home Line Open"))
            oc_l  = fmt(g.get("Home Line Close"))
            op_t  = fmt(g.get("Total Score Open"))
            oc_t  = fmt(g.get("Total Score Close"))
            op_h  = fmt(g.get("Home Odds Open"))
            oc_h  = fmt(g.get("Home Odds Close"))
            oc_a  = fmt(g.get("Away Odds Close"))
            h_sc  = fmt(g.get("Home Score"))
            a_sc  = fmt(g.get("Away Score"))
            act_mg  = round(h_sc - a_sc, 1) if h_sc is not None and a_sc is not None else None
            act_tot = round(h_sc + a_sc, 1) if h_sc is not None and a_sc is not None else None
        else:
            op_l=oc_l=op_t=oc_t=op_h=oc_h=oc_a=act_mg=act_tot = None

        rl_hcap_gap = round(rl_mg  - oc_l, 1) if rl_mg  is not None and oc_l is not None else None
        ml_hcap_gap = round(ml_mg  - oc_l, 1) if ml_mg  is not None and oc_l is not None else None
        rl_tot_gap  = round(rl_tot - oc_t, 1) if rl_tot is not None and oc_t is not None else None
        ml_tot_gap  = round(ml_tot - oc_t, 1) if ml_tot is not None and oc_t is not None else None

        rl_hcap_w = direction_ok(rl_mg,  oc_l, act_mg)
        ml_hcap_w = direction_ok(ml_mg,  oc_l, act_mg)
        rl_tot_w  = direction_ok(rl_tot, oc_t, act_tot)
        ml_tot_w  = direction_ok(ml_tot, oc_t, act_tot)

        print(f"\n  {hs} vs {as_}")
        print(f"    HANDICAP  open:{op_l}  close:{oc_l}  actual:{gs(act_mg)}")
        print(f"              rules:{gs(rl_mg)} (gap {gs(rl_hcap_gap)}) [{rl_hcap_w}]   ML:{gs(ml_mg)} (gap {gs(ml_hcap_gap)}) [{ml_hcap_w}]")
        print(f"    TOTAL     open:{op_t}  close:{oc_t}  actual:{act_tot}")
        print(f"              rules:{rl_tot} (gap {gs(rl_tot_gap)}) [{rl_tot_w}]   ML:{ml_tot} (gap {gs(ml_tot_gap)}) [{ml_tot_w}]")
        print(f"    H2H       rules:{rl_h}/{rl_a}   ML:{ml_h}   open:{op_h}  close:{oc_h}/{oc_a}")

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
            "rules_home_odds": rl_h, "rules_away_odds": rl_a, "ml_home_odds": ml_h,
            "open_h2h_home": op_h, "close_h2h_home": oc_h, "close_h2h_away": oc_a,
        })

print()
print("=" * 80)
print("  SCORECARD")
print("=" * 80)
n = len(rows_out)
rl_hw = sum(1 for r in rows_out if r["hcap_rules_winner"] == "MODEL")
ml_hw = sum(1 for r in rows_out if r["hcap_ml_winner"]   == "MODEL")
rl_tw = sum(1 for r in rows_out if r["total_rules_winner"]== "MODEL")
ml_tw = sum(1 for r in rows_out if r["total_ml_winner"]   == "MODEL")
print(f"  Handicap  Rules: {rl_hw}/{n}   ML: {ml_hw}/{n}")
print(f"  Totals    Rules: {rl_tw}/{n}   ML: {ml_tw}/{n}")

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
    w.writeheader(); w.writerows(rows_out)
print(f"\nSaved: {OUT}")
