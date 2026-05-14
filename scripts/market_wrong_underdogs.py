"""
market_wrong_underdogs.py

Find teams the market consistently misprices as underdogs.

For each NRL game with closing H2H odds:
  - Identify fav (lower odds) and dog (higher odds)
  - Compare implied win% from odds vs actual result
  - Group by team, filter to games where team was an underdog

Output: ranked table of teams where market underestimates them most
        (i.e. they win more often than their odds implied)
"""
# /// script
# dependencies = ["pandas"]
# ///

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ── Load all seasons ──────────────────────────────────────────────────────────

odds_files = [
    ROOT / "BettingEngine/data/import/odds_2023.csv",
    ROOT / "BettingEngine/data/import/odds_2025.csv",
    ROOT / "BettingEngine/data/import/odds_2026_r1_r5.csv",
]
results_files = [
    ROOT / "BettingEngine/data/import/results_2023.csv",
    ROOT / "BettingEngine/data/import/results_2025.csv",
    ROOT / "BettingEngine/data/import/results_2026_r1_r5.csv",
]

odds_df    = pd.concat([pd.read_csv(f) for f in odds_files if f.exists()], ignore_index=True)
results_df = pd.concat([pd.read_csv(f) for f in results_files if f.exists()], ignore_index=True)

print(f"Odds rows: {len(odds_df)}  |  Results rows: {len(results_df)}")

# ── Filter to closing H2H odds only ──────────────────────────────────────────

closing = odds_df[(odds_df["is_closing"] == 1) & (odds_df["market_type"] == "h2h")].copy()

# Pivot so we have one row per game: home_odds, away_odds
home_odds = closing[closing["selection"] == "home"][["season","round","match_date","home_team","away_team","odds"]].rename(columns={"odds": "home_odds"})
away_odds = closing[closing["selection"] == "away"][["season","round","match_date","home_team","away_team","odds"]].rename(columns={"odds": "away_odds"})

game_odds = home_odds.merge(away_odds, on=["season","round","match_date","home_team","away_team"])

# ── Join with results ─────────────────────────────────────────────────────────

results_df["home_win"] = (results_df["home_score"] > results_df["away_score"]).astype(int)

merged = game_odds.merge(
    results_df[["season","round","match_date","home_team","away_team","home_score","away_score","home_win"]],
    on=["season","round","match_date","home_team","away_team"],
    how="inner"
)

print(f"Matched games: {len(merged)}")

# ── Build per-team underdog record ───────────────────────────────────────────

rows = []

for _, g in merged.iterrows():
    home_implied = 1 / g["home_odds"]
    away_implied = 1 / g["away_odds"]
    # Normalise (remove vig)
    total = home_implied + away_implied
    home_prob = home_implied / total
    away_prob = away_implied / total

    home_won = g["home_win"] == 1
    away_won = not home_won

    # Home team
    rows.append({
        "team":         g["home_team"],
        "role":         "fav" if g["home_odds"] < g["away_odds"] else "dog",
        "odds":         g["home_odds"],
        "implied_prob": home_prob,
        "won":          int(home_won),
        "season":       g["season"],
        "opponent":     g["away_team"],
    })
    # Away team
    rows.append({
        "team":         g["away_team"],
        "role":         "fav" if g["away_odds"] < g["home_odds"] else "dog",
        "odds":         g["away_odds"],
        "implied_prob": away_prob,
        "won":          int(away_won),
        "season":       g["season"],
        "opponent":     g["home_team"],
    })

df = pd.DataFrame(rows)

# ── Analysis 1: underdog calibration by team ─────────────────────────────────
# Only games where team was the underdog (odds >= 2.0)

underdogs = df[df["odds"] >= 2.0].copy()
underdogs["edge"] = underdogs["won"] - underdogs["implied_prob"]

summary = (
    underdogs.groupby("team")
    .agg(
        games       = ("won", "count"),
        wins        = ("won", "sum"),
        actual_win_pct  = ("won", "mean"),
        market_win_pct  = ("implied_prob", "mean"),
    )
    .reset_index()
)
summary["edge_pct"] = (summary["actual_win_pct"] - summary["market_win_pct"]) * 100
summary = summary.sort_values("edge_pct", ascending=False)

print("\n--- Teams the market UNDERESTIMATES as underdogs (win more than implied) ---")
print("  (min 5 underdog games, odds >= 2.0)\n")
top = summary[summary["games"] >= 5]
print(f"{'Team':<35} {'Games':>5} {'Wins':>5} {'Actual%':>8} {'Implied%':>9} {'Edge':>7}")
print("-" * 75)
for _, r in top.iterrows():
    edge_str = f"+{r['edge_pct']:.1f}%" if r['edge_pct'] >= 0 else f"{r['edge_pct']:.1f}%"
    print(f"{r['team']:<35} {r['games']:>5} {int(r['wins']):>5} "
          f"{r['actual_win_pct']*100:>7.1f}% {r['market_win_pct']*100:>8.1f}% {edge_str:>7}")

# ── Analysis 2: hammered dogs specifically (odds >= 2.5) ─────────────────────

hammered = df[df["odds"] >= 2.5].copy()
hammered["edge"] = hammered["won"] - hammered["implied_prob"]

hammered_summary = (
    hammered.groupby("team")
    .agg(
        games           = ("won", "count"),
        wins            = ("won", "sum"),
        actual_win_pct  = ("won", "mean"),
        market_win_pct  = ("implied_prob", "mean"),
        avg_odds        = ("odds", "mean"),
    )
    .reset_index()
)
hammered_summary["edge_pct"] = (hammered_summary["actual_win_pct"] - hammered_summary["market_win_pct"]) * 100
hammered_summary = hammered_summary.sort_values("edge_pct", ascending=False)

print("\n--- HAMMERED dogs (odds >= 2.5) --- market most wrong ---\n")
top_h = hammered_summary[hammered_summary["games"] >= 3]
print(f"{'Team':<35} {'Games':>5} {'Wins':>5} {'Actual%':>8} {'Implied%':>9} {'Edge':>7} {'AvgOdds':>8}")
print("-" * 83)
for _, r in top_h.iterrows():
    edge_str = f"+{r['edge_pct']:.1f}%" if r['edge_pct'] >= 0 else f"{r['edge_pct']:.1f}%"
    print(f"{r['team']:<35} {r['games']:>5} {int(r['wins']):>5} "
          f"{r['actual_win_pct']*100:>7.1f}% {r['market_win_pct']*100:>8.1f}% "
          f"{edge_str:>7} {r['avg_odds']:>8.2f}")

# ── Analysis 3: consistent upset teams (win rate > 40% as heavy dogs >=2.5) ──

print("\n--- Consistent upset specialists (win% > 35% as heavy dog) ---\n")
upsets = top_h[top_h["actual_win_pct"] > 0.35].sort_values("actual_win_pct", ascending=False)
for _, r in upsets.iterrows():
    print(f"  {r['team']:<33} {int(r['wins'])}/{int(r['games'])} as dog  "
          f"({r['actual_win_pct']*100:.0f}% actual vs {r['market_win_pct']*100:.0f}% implied)  "
          f"avg odds {r['avg_odds']:.2f}")
