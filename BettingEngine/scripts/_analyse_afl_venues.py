import pandas as pd

XLSX = "outputs/afl_weekly_review/historical/afl_20260616_160032.xlsx"

df = pd.read_excel(XLSX, header=1)
df.columns = (
    ["Date", "KickOff", "HomeTeam", "AwayTeam", "Venue",
     "HomeScore", "AwayScore", "Playoff", "HomeGoals", "HomeBehinds",
     "AwayGoals", "AwayBehinds"]
    + list(range(len(df.columns) - 12))
)

df["HomeScore"] = pd.to_numeric(df["HomeScore"], errors="coerce")
df["AwayScore"]  = pd.to_numeric(df["AwayScore"],  errors="coerce")
df = df[df["HomeScore"].notna() & df["AwayScore"].notna()]

# Regular season only — Playoff column is blank/NaN for regular games
df = df[df["Playoff"].isna() | (df["Playoff"] == 0)]

df["Total"] = df["HomeScore"] + df["AwayScore"]
df["Date"]  = pd.to_datetime(df["Date"], errors="coerce")
df["Year"]  = df["Date"].dt.year
df = df[df["Year"] >= 2018].copy()

# Season averages (removes year-to-year scoring drift)
season_avg = df.groupby("Year")["Total"].mean()
print("Season averages (regular season):")
for yr, avg in season_avg.items():
    n = len(df[df["Year"] == yr])
    print(f"  {int(yr)}: {avg:.1f}  (n={n})")

df["SeasonAvg"] = df["Year"].map(season_avg)
df["Residual"]  = df["Total"] - df["SeasonAvg"]

venue_stats = (
    df.groupby("Venue")
    .agg(n=("Total", "count"), avg=("Total", "mean"), delta=("Residual", "mean"))
    .reset_index()
)
venue_stats = venue_stats[venue_stats["n"] >= 10].sort_values("delta")

print()
print(f"{'Venue':<35} {'N':>5} {'Avg Total':>10} {'Season-adj delta':>17}")
print("-" * 72)
for _, r in venue_stats.iterrows():
    bar = "+" * int(abs(r["delta"]) / 0.5) if r["delta"] > 0 else "-" * int(abs(r["delta"]) / 0.5)
    print(f"  {r['Venue']:<33} {int(r['n']):>5} {r['avg']:>10.1f}    {r['delta']:>+8.1f}  {bar}")

print()
league_avg = df["Total"].mean()
print(f"Overall avg (2018-2026): {league_avg:.1f}  n={len(df)}")

# Also check just recent 3 years for recency
recent = df[df["Year"] >= 2023].copy()
recent_avg = recent.groupby("Year")["Total"].mean()
recent["SeasonAvg"] = recent["Year"].map(recent_avg)
recent["Residual"]  = recent["Total"] - recent["SeasonAvg"]
recent_venue = (
    recent.groupby("Venue")
    .agg(n=("Total", "count"), delta=("Residual", "mean"))
    .reset_index()
)
recent_venue = recent_venue[recent_venue["n"] >= 8].sort_values("delta")

print()
print("Recent 3 years (2023-2026) — stability check:")
print(f"{'Venue':<35} {'N':>5} {'Recent delta':>13}")
print("-" * 55)
for _, r in recent_venue.iterrows():
    print(f"  {r['Venue']:<33} {int(r['n']):>5}  {r['delta']:>+10.1f}")
