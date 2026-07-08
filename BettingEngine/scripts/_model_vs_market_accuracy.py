"""
NRL Model vs Market Accuracy — R9 through R13
Compares model (T1-T8 rules engine) vs market closing line on:
  H2H  : did each pick the correct winner?
  Hcap : MAE + direction accuracy vs closing line
  Total: MAE + direction accuracy vs closing line
"""
import sys, csv, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import nrl_weekly_clv_report as nrl_clv

ROOT     = Path(__file__).resolve().parent.parent
NRL_XLSX = ROOT / "outputs" / "nrl_weekly_review" / "historical" / "latest.xlsx"
RESULTS  = ROOT / "results"

# Pricing files: round -> file, and the date range for the xlsx lookup
ROUNDS = {
    9:  {"file": RESULTS / "r9_pricing_2026.csv",  "month": 4, "days": set(range(24, 30))},
    10: {"file": RESULTS / "r10_pricing_2026.csv", "month": 5, "days": set(range(1,  8))},
    11: {"file": RESULTS / "r11_pricing_2026.csv", "month": 5, "days": set(range(8,  18))},
    12: {"file": RESULTS / "r12_pricing_2026.csv", "month": 5, "days": set(range(18, 26))},
    13: {"file": RESULTS / "r13_pricing_2026.csv", "month": 5, "days": set(range(28, 32))},
}

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
def fmt(v):
    try:    return round(float(v), 2)
    except: return None

# ── load full xlsx ─────────────────────────────────────────────────────────────
print("Loading NRL xlsx...")
all_xlsx = nrl_clv.load_workbook_rows(NRL_XLSX, 2026)
print(f"  {len(all_xlsx)} total game rows\n")

def get_xlsx_game(home, away, month, days):
    hn, an = norm(home), norm(away)
    for (d, h, a), v in all_xlsx.items():
        if not (hasattr(d,"month") and d.month==month and d.day in days): continue
        if norm(h)==hn and norm(a)==an: return v
        if norm(h)==an and norm(a)==hn: return v
    # fuzzy
    hl, al = hn.split()[-1], an.split()[-1]
    for (d, h, a), v in all_xlsx.items():
        if not (hasattr(d,"month") and d.month==month and d.day in days): continue
        if norm(h).split()[-1]==hl and norm(a).split()[-1]==al: return v
    return None

# ── accumulators ───────────────────────────────────────────────────────────────
h2h_model_correct = h2h_mkt_correct = h2h_total = 0
hcap_model_dir = hcap_mkt_dir = hcap_total = 0
hcap_model_mae_sum = hcap_mkt_mae_sum = 0.0
tot_model_dir = tot_mkt_dir = tot_total = 0
tot_model_mae_sum = tot_mkt_mae_sum = 0.0

all_games = []

# ── process each round ─────────────────────────────────────────────────────────
for rnd, cfg in ROUNDS.items():
    if not cfg["file"].exists():
        print(f"  R{rnd}: file not found — skipping")
        continue

    with open(cfg["file"], encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.DictReader(f))

    rnd_games = 0
    for row in rows:
        home = row["home_team"]
        away = row["away_team"]
        g    = get_xlsx_game(home, away, cfg["month"], cfg["days"])

        model_margin = fmt(row.get("final_margin"))
        model_total  = fmt(row.get("fair_total_line") or row.get("pred_total"))
        model_h_odds = fmt(row.get("fair_home_odds"))
        model_a_odds = fmt(row.get("fair_away_odds"))

        # actuals from pricing CSV (populated after results)
        act_home = fmt(row.get("actual_home") or row.get("pred_home_score"))
        act_away = fmt(row.get("actual_away") or row.get("pred_away_score"))
        act_total_csv = fmt(row.get("actual_total"))

        if g:
            # prefer xlsx actuals (more reliable)
            h_sc = fmt(g.get("Home Score"))
            a_sc = fmt(g.get("Away Score"))
            if h_sc is not None and a_sc is not None:
                act_margin = round(h_sc - a_sc, 1)
                act_total  = round(h_sc + a_sc, 1)
            elif act_home and act_away:
                act_margin = round(act_home - act_away, 1)
                act_total  = round(act_home + act_away, 1)
            else:
                continue

            close_line  = fmt(g.get("Home Line Close"))
            close_total = fmt(g.get("Total Score Close"))
            close_h_odds= fmt(g.get("Home Odds Close"))
            close_a_odds= fmt(g.get("Away Odds Close"))
        elif act_home and act_away:
            act_margin = round(act_home - act_away, 1)
            act_total  = act_total_csv
            close_line  = None
            close_total = None
            close_h_odds= None
            close_a_odds= None
        else:
            continue

        hs, as_ = short(home), short(away)
        actual_winner = "home" if act_margin > 0 else ("away" if act_margin < 0 else "draw")

        game_rec = {
            "round": rnd, "home": home, "away": away,
            "model_margin": model_margin, "model_total": model_total,
            "model_h_odds": model_h_odds, "model_a_odds": model_a_odds,
            "close_line": close_line, "close_total": close_total,
            "close_h_odds": close_h_odds, "close_a_odds": close_a_odds,
            "act_margin": act_margin, "act_total": act_total,
            "actual_winner": actual_winner,
        }

        # ── H2H ───────────────────────────────────────────────────────────────
        if model_h_odds and model_a_odds and close_h_odds and close_a_odds:
            model_pick = "home" if model_h_odds < model_a_odds else "away"
            mkt_pick   = "home" if close_h_odds  < close_a_odds  else "away"
            model_ok   = model_pick == actual_winner
            mkt_ok     = mkt_pick   == actual_winner
            game_rec.update({"h2h_model_pick": model_pick, "h2h_mkt_pick": mkt_pick,
                             "h2h_model_ok": model_ok, "h2h_mkt_ok": mkt_ok})
            if model_ok: h2h_model_correct += 1
            if mkt_ok:   h2h_mkt_correct   += 1
            h2h_total += 1

        # ── Handicap ──────────────────────────────────────────────────────────
        if model_margin is not None and close_line is not None and act_margin is not None:
            # direction: which side of the close does each predict?
            model_dir = "home" if model_margin > close_line else "away"
            actual_dir = "home" if act_margin > close_line else ("away" if act_margin < close_line else "push")
            mkt_dir = "neutral"  # market is the reference, so neither side

            model_dir_ok = model_dir == actual_dir
            # market "direction" = random coin flip at close line (by definition 50%)
            # We compare model MAE vs close MAE
            model_hcap_mae = abs(model_margin - act_margin)
            mkt_hcap_mae   = abs(close_line   - act_margin)

            game_rec.update({"hcap_model_dir": model_dir, "hcap_actual_dir": actual_dir,
                             "hcap_model_dir_ok": model_dir_ok,
                             "hcap_model_mae": model_hcap_mae, "hcap_mkt_mae": mkt_hcap_mae})

            if model_dir_ok:   hcap_model_dir += 1
            hcap_model_mae_sum += model_hcap_mae
            hcap_mkt_mae_sum   += mkt_hcap_mae
            hcap_total += 1

        # ── Totals ────────────────────────────────────────────────────────────
        if model_total is not None and close_total is not None and act_total is not None:
            model_tot_dir = "over" if model_total > close_total else "under"
            actual_tot_dir = "over" if act_total > close_total else ("under" if act_total < close_total else "push")
            tot_dir_ok    = model_tot_dir == actual_tot_dir

            model_tot_mae = abs(model_total - act_total)
            mkt_tot_mae   = abs(close_total - act_total)

            game_rec.update({"tot_model_dir": model_tot_dir, "tot_actual_dir": actual_tot_dir,
                             "tot_model_dir_ok": tot_dir_ok,
                             "tot_model_mae": model_tot_mae, "tot_mkt_mae": mkt_tot_mae})

            if tot_dir_ok:  tot_model_dir += 1
            tot_model_mae_sum += model_tot_mae
            tot_mkt_mae_sum   += mkt_tot_mae
            tot_total += 1

        all_games.append(game_rec)
        rnd_games += 1

    print(f"  R{rnd}: {rnd_games} games processed")

# ── print results ──────────────────────────────────────────────────────────────
n = len(all_games)
print(f"\nTotal games: {n}  (R9–R13)")

print()
print("=" * 70)
print("  H2H — WHO PICKS THE CORRECT WINNER?")
print("=" * 70)
print(f"  Model  : {h2h_model_correct}/{h2h_total}  ({100*h2h_model_correct/h2h_total:.1f}%)")
print(f"  Market : {h2h_mkt_correct}/{h2h_total}  ({100*h2h_mkt_correct/h2h_total:.1f}%)")
h2h_edge = (h2h_model_correct - h2h_mkt_correct) / h2h_total * 100 if h2h_total else 0
print(f"  Edge   : model {h2h_edge:+.1f}% vs market")

print()
print("=" * 70)
print("  HANDICAP — MODEL vs MARKET CLOSE")
print("=" * 70)
model_hcap_avg_mae = hcap_model_mae_sum / hcap_total if hcap_total else 0
mkt_hcap_avg_mae   = hcap_mkt_mae_sum   / hcap_total if hcap_total else 0
print(f"  Direction accuracy (did model pick right side of close?)")
print(f"    Model  : {hcap_model_dir}/{hcap_total}  ({100*hcap_model_dir/hcap_total:.1f}%)")
print(f"    Market : {hcap_total//2}/{hcap_total}  (50.0%)  ← baseline by definition")
print(f"  Mean Absolute Error vs actual margin")
print(f"    Model  : {model_hcap_avg_mae:.1f} pts")
print(f"    Market : {mkt_hcap_avg_mae:.1f} pts")
print(f"    Edge   : model {mkt_hcap_avg_mae - model_hcap_avg_mae:+.1f} pts vs market close")

print()
print("=" * 70)
print("  TOTALS — MODEL vs MARKET CLOSE")
print("=" * 70)
model_tot_avg_mae = tot_model_mae_sum / tot_total if tot_total else 0
mkt_tot_avg_mae   = tot_mkt_mae_sum   / tot_total if tot_total else 0
print(f"  Direction accuracy (did model predict over/under vs close correctly?)")
print(f"    Model  : {tot_model_dir}/{tot_total}  ({100*tot_model_dir/tot_total:.1f}%)")
print(f"    Market : {tot_total//2}/{tot_total}  (50.0%)  ← baseline by definition")
print(f"  Mean Absolute Error vs actual total")
print(f"    Model  : {model_tot_avg_mae:.1f} pts")
print(f"    Market : {mkt_tot_avg_mae:.1f} pts")
print(f"    Edge   : model {mkt_tot_avg_mae - model_tot_avg_mae:+.1f} pts vs market close")

print()
print("=" * 70)
print("  GAME BY GAME")
print("=" * 70)
print(f"  {'Rd':<4} {'Game':<34} {'H2H':^12} {'Hcap':^18} {'Total':^18}")
print(f"  {'':4} {'':34} {'Mdl  Mkt':^12} {'Mdl gap  ActDir':^18} {'Mdl gap  ActDir':^18}")
print("  " + "-" * 86)

for g in all_games:
    hs  = short(g["home"])
    as_ = short(g["away"])
    game_str = f"R{g['round']} {hs} v {as_}"

    h2h_str = ""
    if "h2h_model_ok" in g:
        m = "✓" if g["h2h_model_ok"] else "✗"
        k = "✓" if g["h2h_mkt_ok"]   else "✗"
        h2h_str = f"M:{m}  K:{k}"

    hcap_str = ""
    if "hcap_model_mae" in g:
        gap = round(g["model_margin"] - g["close_line"], 1) if g.get("model_margin") and g.get("close_line") else 0
        d   = "✓" if g["hcap_model_dir_ok"] else "✗"
        hcap_str = f"{gap:+.1f} ({d})"

    tot_str = ""
    if "tot_model_mae" in g:
        gap = round(g["model_total"] - g["close_total"], 1) if g.get("model_total") and g.get("close_total") else 0
        d   = "✓" if g["tot_model_dir_ok"] else "✗"
        tot_str = f"{gap:+.1f} ({d})"

    print(f"  {game_str:<38} {h2h_str:<12} {hcap_str:<18} {tot_str}")

# ── save ───────────────────────────────────────────────────────────────────────
OUT = ROOT / "data" / "clv" / "nrl" / "NRL_MODEL_ACCURACY_R9_R13_2026-06-03.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)
save_fields = ["round","home","away","model_margin","close_line","act_margin",
               "h2h_model_ok","h2h_mkt_ok","hcap_model_dir_ok","hcap_model_mae","hcap_mkt_mae",
               "tot_model_dir_ok","tot_model_mae","tot_mkt_mae"]
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=save_fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(all_games)
print(f"\nSaved: {OUT.name}")
