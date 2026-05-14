# /// script
# dependencies = ["openpyxl", "pandas"]
# ///
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "data/nrl/historical/latest.xlsx"

df = pd.read_excel(XLSX, header=1)
df.columns = df.columns.str.strip()
rename = {
    "Date": "date", "Home Team": "home_team", "Away Team": "away_team",
    "Home Score": "home_score", "Away Score": "away_score",
    "Home Odds Open": "h_h2h_open", "Home Odds Close": "h_h2h_close",
    "Away Odds Open": "a_h2h_open", "Away Odds Close": "a_h2h_close",
}
df = df.rename(columns=rename)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date", "home_team", "away_team"])
df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
df["away_score"]  = pd.to_numeric(df["away_score"],  errors="coerce")
df = df.dropna(subset=["home_score", "away_score"])
df = df[df["date"].dt.year >= 2023]

THRESH = 15.0

results = []

for _, g in df.iterrows():
    home_won = g["home_score"] > g["away_score"]
    try:
        h_open, h_close = float(g["h_h2h_open"]), float(g["h_h2h_close"])
        a_open, a_close = float(g["a_h2h_open"]), float(g["a_h2h_close"])
    except (TypeError, ValueError):
        continue
    if h_open <= 0 or h_close <= 0 or a_open <= 0 or a_close <= 0:
        continue

    h_drift = (h_close - h_open) / h_open * 100
    a_drift = (a_close - a_open) / a_open * 100

    # Home team hammered -> bet on away (shortened) at close
    if h_drift >= THRESH:
        results.append({
            "date": g["date"].strftime("%Y-%m-%d"),
            "hammered": g["home_team"],
            "bet_on": g["away_team"],
            "drift": round(h_drift, 1),
            "bet_odds": a_close,
            "won": int(not home_won),
        })
    # Away team hammered -> bet on home (shortened) at close
    if a_drift >= THRESH:
        results.append({
            "date": g["date"].strftime("%Y-%m-%d"),
            "hammered": g["away_team"],
            "bet_on": g["home_team"],
            "drift": round(a_drift, 1),
            "bet_odds": h_close,
            "won": int(home_won),
        })

res = pd.DataFrame(results)
print(f"Total bets (backing shortened team): {len(res)}")
print(f"Wins: {res['won'].sum()}  ({res['won'].mean()*100:.1f}%)")
print(f"Avg closing odds of shortened team: {res['bet_odds'].mean():.3f}")

res["profit"] = res.apply(lambda r: r["bet_odds"] - 1 if r["won"] else -1, axis=1)
total_profit = res["profit"].sum()
roi = total_profit / len(res) * 100
print(f"Total profit: {total_profit:+.2f}u")
print(f"ROI: {roi:+.2f}%")

# Break down by closing odds bucket
print("\n--- ROI by closing odds of shortened team ---")
res["odds_bucket"] = pd.cut(res["bet_odds"], bins=[1.0,1.3,1.5,1.7,2.0,2.5,99],
    labels=["1.00-1.30","1.30-1.50","1.50-1.70","1.70-2.00","2.00-2.50","2.50+"])
for bucket, grp in res.groupby("odds_bucket", observed=True):
    p = grp["profit"].sum()
    r = p / len(grp) * 100
    print(f"  {bucket}  bets:{len(grp):>3}  wins:{grp['won'].sum():>3} ({grp['won'].mean()*100:.0f}%)  ROI:{r:+.1f}%  profit:{p:+.2f}u")

# Break by drift magnitude
print("\n--- ROI by how hard the opposing team was hammered ---")
res["drift_bucket"] = pd.cut(res["drift"], bins=[15,25,40,60,999], labels=["15-25%","25-40%","40-60%","60%+"])
for bucket, grp in res.groupby("drift_bucket", observed=True):
    p = grp["profit"].sum()
    r = p / len(grp) * 100
    print(f"  Drift {bucket}  bets:{len(grp):>3}  wins:{grp['won'].sum():>3} ({grp['won'].mean()*100:.0f}%)  ROI:{r:+.1f}%  profit:{p:+.2f}u")

# Per-team ROI for the shortened (backed) team
print("\n--- Teams the market shortens — ROI of backing them (min 3 games) ---")
team_stats = (
    res.groupby("bet_on")
    .apply(lambda g: pd.Series({
        "bets":     len(g),
        "wins":     g["won"].sum(),
        "win_pct":  g["won"].mean() * 100,
        "avg_odds": g["bet_odds"].mean(),
        "profit":   g["profit"].sum(),
        "roi":      g["profit"].sum() / len(g) * 100,
    }), include_groups=False)
    .reset_index()
)
team_stats = team_stats[team_stats["bets"] >= 3].sort_values("roi")
print(f"  {'Team':<32} {'Bets':>5} {'Wins':>5} {'Win%':>6} {'AvgOdds':>8} {'ROI':>7}")
print("  " + "-"*67)
for _, r in team_stats.iterrows():
    print(f"  {r['bet_on']:<32} {int(r['bets']):>5} {int(r['wins']):>5} {r['win_pct']:>5.0f}% {r['avg_odds']:>8.2f} {r['roi']:>+7.1f}%")
