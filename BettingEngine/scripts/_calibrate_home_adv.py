"""
Calibrate NRL home advantage:
1. Measure actual home win rate and margin advantage from 2009-2026 xlsx
2. Compare model H2H home predictions vs actual from CLV files
3. Compute the correct home_advantage_points setting
"""
import openpyxl, statistics, math, csv, sqlite3
from pathlib import Path
from collections import defaultdict
from datetime import date

xlsx_path = Path("C:/Users/ElliotBladen/Apps/data/nrl/historical/latest.xlsx")
BE = Path("C:/Users/ElliotBladen/Apps/BettingEngine")

# ── 1. True NRL home advantage from historical results ─────────────────────
print("=" * 70)
print("  HISTORICAL NRL HOME ADVANTAGE (xlsx, 2009-2026)")
print("=" * 70)

wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
ws = wb.active

home_wins, away_wins, draws = 0, 0, 0
home_margins = []    # margin from home perspective when home wins
away_margins = []    # margin from home perspective when away wins
all_margins  = []    # all home-perspective margins (positive = home won)

by_season_margin = defaultdict(list)
by_season_hw     = defaultdict(lambda: [0, 0])  # [wins, total]

for row in ws.iter_rows(min_row=3, values_only=True):
    match_date = row[0]
    hs = row[5]
    aws = row[6]
    if not match_date or hs is None or aws is None:
        continue
    try:
        hs, aws = int(hs), int(aws)
    except (TypeError, ValueError):
        continue
    if hs == 0 and aws == 0:
        continue

    season = match_date.year if hasattr(match_date, "year") else None
    if not season:
        continue

    margin = hs - aws  # positive = home won
    all_margins.append(margin)
    by_season_margin[season].append(margin)

    if hs > aws:
        home_wins += 1
        home_margins.append(margin)
        by_season_hw[season][0] += 1
    elif aws > hs:
        away_wins += 1
        away_margins.append(margin)
    else:
        draws += 1
    by_season_hw[season][1] += 1

wb.close()

total = home_wins + away_wins + draws
home_win_rate = home_wins / total
avg_margin_all = sum(all_margins) / len(all_margins)  # true home advantage in pts
avg_margin_when_home_wins = sum(home_margins) / len(home_margins)
avg_margin_when_away_wins = sum(away_margins) / len(away_margins)

print(f"\n  Total matches: {total}")
print(f"  Home wins: {home_wins} ({home_win_rate:.1%})")
print(f"  Away wins: {away_wins} ({away_wins/total:.1%})")
print(f"  Draws: {draws}")
print(f"\n  Average home margin (all games): {avg_margin_all:+.2f} pts")
print(f"  (This is the true home advantage — same as 'home_advantage_points' should be)")
print(f"  Avg margin when home wins: +{avg_margin_when_home_wins:.1f}")
print(f"  Avg margin when away wins: {avg_margin_when_away_wins:.1f}")

print(f"\n  By Season:")
print(f"  {'Season':<8} {'Games':>6} {'HW%':>7} {'Avg Margin':>12}")
for season in sorted(by_season_margin):
    margins = by_season_margin[season]
    hw, tot = by_season_hw[season]
    avg_m = sum(margins) / len(margins)
    print(f"  {season:<8} {tot:>6} {hw/tot:>7.1%} {avg_m:>+12.2f}")

# Trend: last 5 seasons vs overall
recent = [m for s, ms in by_season_margin.items() if s >= 2022 for m in ms]
older  = [m for s, ms in by_season_margin.items() if s < 2022 for m in ms]
print(f"\n  2022-2026 avg margin: {sum(recent)/len(recent):+.2f} pts (n={len(recent)})")
print(f"  2009-2021 avg margin: {sum(older)/len(older):+.2f} pts (n={len(older)})")

# ── 2. Model H2H prediction accuracy: home vs away ────────────────────────
print()
print("=" * 70)
print("  MODEL H2H BIAS ANALYSIS (CLV files, R9-R15)")
print("=" * 70)

clv_dir = BE / "data/clv/nrl"
model_home_correct = 0
model_home_total   = 0
model_away_correct = 0
model_away_total   = 0

# Also track by prediction type (model vs market)
ml_home_correct = 0; ml_home_total = 0
ml_away_correct = 0; ml_away_total = 0

for f in sorted(clv_dir.glob("*.csv")):
    try:
        rows = list(csv.DictReader(open(f, encoding="utf-8-sig", errors="replace")))
    except Exception:
        continue
    for r in rows:
        if r.get("market", "").lower() != "h2h":
            continue
        signal = r.get("signal", "").lower()
        selection = r.get("selection", "")
        home_team = r.get("home_team", "")
        result = r.get("result", "").lower()
        winner_col = r.get("winner", "")

        # We want: when the model picks home vs away, how often is it right?
        if signal in ("model", "normal", "rules"):
            is_home_pick = (selection == home_team)
            correct = result == "win"
            if is_home_pick:
                model_home_total += 1
                if correct: model_home_correct += 1
            else:
                model_away_total += 1
                if correct: model_away_correct += 1
        elif signal == "ml":
            is_home_pick = (selection == home_team)
            correct = result == "win"
            if is_home_pick:
                ml_home_total += 1
                if correct: ml_home_correct += 1
            else:
                ml_away_total += 1
                if correct: ml_away_correct += 1

if model_home_total > 0:
    print(f"\n  Rules model — when picking HOME team: {model_home_correct}/{model_home_total} = {model_home_correct/model_home_total:.1%}")
if model_away_total > 0:
    print(f"  Rules model — when picking AWAY team: {model_away_correct}/{model_away_total} = {model_away_correct/model_away_total:.1%}")
if ml_home_total > 0:
    print(f"\n  ML model — when picking HOME team: {ml_home_correct}/{ml_home_total} = {ml_home_correct/ml_home_total:.1%}")
if ml_away_total > 0:
    print(f"  ML model — when picking AWAY team: {ml_away_correct}/{ml_away_total} = {ml_away_correct/ml_away_total:.1%}")

# ── 3. Model home odds vs market home odds ────────────────────────────────
print()
print("=" * 70)
print("  MODEL vs MARKET ODDS — HOME TEAM COMPARISON")
print("=" * 70)

model_home_odds = []
market_home_odds = []
home_team_results = []  # 1 = home won, 0 = away won

for f in sorted(clv_dir.glob("*_ml_comparison.csv")):
    try:
        rows = list(csv.DictReader(open(f, encoding="utf-8-sig", errors="replace")))
    except Exception:
        continue
    # Group by game to get both model and market home odds
    games = defaultdict(dict)
    for r in rows:
        if r.get("market", "").lower() != "h2h":
            continue
        key = (r.get("season",""), r.get("home_team",""), r.get("away_team",""))
        signal = r.get("signal","").lower()
        home_team = r.get("home_team","")
        selection = r.get("selection","")
        result = r.get("result","").lower()

        if signal == "model" and selection == home_team:
            # Model favours home — get fair odds
            mho = r.get("model_home_fair_odds","")
            try:
                games[key]["model_home_odds"] = float(mho)
                games[key]["home_won"] = (result == "win")
            except (ValueError, TypeError):
                pass
        elif signal == "market" and selection == home_team:
            # Market line for home
            co = r.get("close_odds","")
            try:
                games[key]["market_home_close"] = float(co)
            except (ValueError, TypeError):
                pass

    for key, g in games.items():
        if "model_home_odds" in g and "market_home_close" in g:
            model_home_odds.append(g["model_home_odds"])
            market_home_odds.append(g["market_home_close"])
            home_team_results.append(1 if g.get("home_won") else 0)

if model_home_odds:
    avg_model_prob = sum(1/o for o in model_home_odds) / len(model_home_odds)
    avg_market_prob = sum(1/o for o in market_home_odds) / len(market_home_odds)
    actual_hw_rate = sum(home_team_results) / len(home_team_results) if home_team_results else None
    print(f"\n  n={len(model_home_odds)} matched game pairs")
    print(f"  Avg model home win prob:  {avg_model_prob:.1%}")
    print(f"  Avg market home win prob: {avg_market_prob:.1%}")
    if actual_hw_rate is not None:
        print(f"  Actual home win rate:     {actual_hw_rate:.1%}")
        print(f"  Model overrates home by:  {avg_model_prob - actual_hw_rate:+.1%} vs actual")
        print(f"  Market overrates home by: {avg_market_prob - actual_hw_rate:+.1%} vs actual")
        print(f"  Model vs market home bias:{avg_model_prob - avg_market_prob:+.1%}")

# ── 4. Recommendation ────────────────────────────────────────────────────
print()
print("=" * 70)
print("  CALIBRATION RECOMMENDATION")
print("=" * 70)
print(f"\n  Current config:  home_advantage_points = 3.5")
print(f"  Empirical NRL home advantage (2009-2026): {avg_margin_all:+.2f} pts")
recent_avg = sum(recent)/len(recent)
print(f"  Recent (2022-2026): {recent_avg:+.2f} pts")
print(f"  Recommended value: {max(1.5, round(recent_avg * 2) / 2):.1f} pts")
print(f"  (nearest 0.5 increment to 2022-2026 empirical average)")
print(f"\n  Note: home_advantage_points in tiers.yaml feeds BOTH the ELO formula")
print(f"  and the ratings baseline. Reducing from 3.5 tightens both H2H odds")
print(f"  and the raw margin for home teams.")
