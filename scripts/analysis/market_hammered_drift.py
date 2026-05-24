# /// script
# dependencies = ["openpyxl", "pandas"]
# ///
"""
market_hammered_drift.py

Find all NRL games (3 seasons) where the market moved >= 15% against a team
from open to close (H2H and/or handicap).

"Hammered" = team's price drifted OUT by >= 15%
  e.g. open 2.00 -> close 2.40 = +20% drift = market turned hard against them

Output: every such game with open/close odds, drift %, result, and whether
the hammered team covered / won.
"""

import pandas as pd
import sys
from pathlib import Path

ROOT  = Path(__file__).resolve().parents[1]
XLSX  = ROOT / "data/nrl/historical/latest.xlsx"

# ── Load xlsx (row 0 = title, row 1 = actual headers, row 2+ = data) ─────────

df = pd.read_excel(XLSX, header=1)
df.columns = df.columns.str.strip()

# Rename to clean names
rename = {
    "Date":                   "date",
    "Home Team":              "home_team",
    "Away Team":              "away_team",
    "Home Score":             "home_score",
    "Away Score":             "away_score",
    "Home Odds Open":         "h_h2h_open",
    "Home Odds Close":        "h_h2h_close",
    "Away Odds Open":         "a_h2h_open",
    "Away Odds Close":        "a_h2h_close",
    "Home Line Close":        "h_line_close",
    "Away Line Close":        "a_line_close",
    "Home Line Odds Open":    "h_hcap_open",
    "Home Line Odds Close":   "h_hcap_close",
    "Away Line Odds Open":    "a_hcap_open",
    "Away Line Odds Close":   "a_hcap_close",
}
df = df.rename(columns=rename)
df["date"] = pd.to_datetime(df["date"], errors="coerce")

# Drop non-data rows (some files have a second header row baked in)
df = df.dropna(subset=["date", "home_team", "away_team"])
df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
df["away_score"]  = pd.to_numeric(df["away_score"],  errors="coerce")
df = df.dropna(subset=["home_score", "away_score"])

# Limit to last 3 seasons (2023, 2024/2025, 2026)
df = df[df["date"].dt.year >= 2023]

print(f"Games loaded: {len(df)}  ({df['date'].dt.year.min()} – {df['date'].dt.year.max()})")

# ── Compute drift % ───────────────────────────────────────────────────────────

def drift_pct(open_price, close_price):
    """Positive = odds drifted OUT (market turned against team). Negative = tightened."""
    try:
        o, c = float(open_price), float(close_price)
        if o > 0 and c > 0:
            return round((c - o) / o * 100, 1)
    except (TypeError, ValueError):
        pass
    return None

rows = []

for _, g in df.iterrows():
    margin = g["home_score"] - g["away_score"]
    home_won = margin > 0
    away_won = margin < 0

    for side in ("home", "away"):
        team     = g["home_team"] if side == "home" else g["away_team"]
        opponent = g["away_team"] if side == "home" else g["home_team"]
        won      = home_won if side == "home" else away_won

        # H2H drift
        h2h_open  = g["h_h2h_open"]  if side == "home" else g["a_h2h_open"]
        h2h_close = g["h_h2h_close"] if side == "home" else g["a_h2h_close"]
        h2h_drift = drift_pct(h2h_open, h2h_close)

        # Handicap drift (odds only — line moves are separate)
        hcap_open  = g["h_hcap_open"]  if side == "home" else g["a_hcap_open"]
        hcap_close = g["h_hcap_close"] if side == "home" else g["a_hcap_close"]
        hcap_drift = drift_pct(hcap_open, hcap_close)
        hcap_line  = g["h_line_close"] if side == "home" else g["a_line_close"]

        # Score margin from this team's perspective
        score_margin = margin if side == "home" else -margin

        row = {
            "date":         g["date"].strftime("%Y-%m-%d"),
            "team":         team,
            "opponent":     opponent,
            "team_score":   int(g["home_score"] if side == "home" else g["away_score"]),
            "opp_score":    int(g["away_score"]  if side == "home" else g["home_score"]),
            "score_margin": int(score_margin),
            "won":          won,
            "h2h_open":     h2h_open,
            "h2h_close":    h2h_close,
            "h2h_drift":    h2h_drift,
            "hcap_open":    hcap_open,
            "hcap_close":   hcap_close,
            "hcap_drift":   hcap_drift,
            "hcap_line":    hcap_line,
        }
        rows.append(row)

all_df = pd.DataFrame(rows)

THRESH = 15.0

# ── Table 1: H2H hammered ≥15% ───────────────────────────────────────────────

h2h_hammered = all_df[all_df["h2h_drift"] >= THRESH].copy()
h2h_hammered = h2h_hammered.sort_values("h2h_drift", ascending=False)

print(f"\n{'='*90}")
print(f"H2H: market drifted team OUT >= {THRESH}%  ({len(h2h_hammered)} cases)")
print(f"{'='*90}")
print(f"{'Date':<12} {'Team':<32} {'vs':<3} {'Opponent':<28} {'Open':>5} {'Close':>6} {'Drift':>6} {'Result'}")
print("-" * 90)
for _, r in h2h_hammered.iterrows():
    result = f"{int(r['team_score'])}-{int(r['opp_score'])} {'WIN' if r['won'] else 'LOSS'}"
    print(f"{r['date']:<12} {r['team']:<32} vs  {r['opponent']:<28} "
          f"{r['h2h_open']:>5.2f} {r['h2h_close']:>6.2f} {r['h2h_drift']:>+5.1f}%  {result}")

# ── Table 2: Handicap hammered ≥15% ─────────────────────────────────────────

hcap_hammered = all_df[
    (all_df["hcap_drift"] >= THRESH) &
    all_df["hcap_line"].notna()
].copy()
hcap_hammered = hcap_hammered.sort_values("hcap_drift", ascending=False)

print(f"\n{'='*100}")
print(f"HANDICAP: market drifted team OUT >= {THRESH}%  ({len(hcap_hammered)} cases)")
print(f"{'='*100}")
print(f"{'Date':<12} {'Team':<32} {'vs':<3} {'Opponent':<28} {'Line':>5} {'Open':>5} {'Close':>6} {'Drift':>6} {'Score':<8} {'Cover?'}")
print("-" * 100)
for _, r in hcap_hammered.iterrows():
    try:
        line = float(r["hcap_line"])
        covered = (r["score_margin"] + line) > 0
        cover_str = "COV" if covered else "NO"
    except (TypeError, ValueError):
        cover_str = "?"
    score = f"{int(r['team_score'])}-{int(r['opp_score'])}"
    print(f"{r['date']:<12} {r['team']:<32} vs  {r['opponent']:<28} "
          f"{r['hcap_line']:>+5.1f} {r['hcap_open']:>5.2f} {r['hcap_close']:>6.2f} "
          f"{r['hcap_drift']:>+5.1f}%  {score:<8} {cover_str}")

# ── Summary: how often hammered teams win / cover ─────────────────────────────

print(f"\n{'='*50}")
print("SUMMARY")
print(f"{'='*50}")

h2h_won = h2h_hammered["won"].sum()
print(f"\nH2H hammered (>= {THRESH}% drift):")
print(f"  {h2h_won}/{len(h2h_hammered)} won  ({h2h_won/len(h2h_hammered)*100:.1f}%)")

if len(hcap_hammered):
    covers = []
    for _, r in hcap_hammered.iterrows():
        try:
            line = float(r["hcap_line"])
            covers.append((r["score_margin"] + line) > 0)
        except (TypeError, ValueError):
            pass
    cov = sum(covers)
    print(f"\nHandicap hammered (>= {THRESH}% drift):")
    print(f"  {cov}/{len(covers)} covered  ({cov/len(covers)*100:.1f}%)")

# ── By team: who gets hammered most and still wins ───────────────────────────

print(f"\n-- Teams most hammered on H2H, win rate --")
team_h2h = (h2h_hammered.groupby("team")
    .agg(times=("won","count"), wins=("won","sum"))
    .assign(win_pct=lambda d: d["wins"]/d["times"]*100)
    .sort_values("times", ascending=False))
for team, r in team_h2h.iterrows():
    print(f"  {team:<32} hammered {int(r['times'])}x  |  won {int(r['wins'])}/{int(r['times'])}  ({r['win_pct']:.0f}%)")
