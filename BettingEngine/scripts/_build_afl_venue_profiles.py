"""
Build season-adjusted AFL venue scoring deltas from historical odds xlsx.

Method:
  1. Compute each season's average total score (removes year-to-year scoring drift)
  2. Residual per game = actual_total - season_avg
  3. Venue delta = mean(residuals) for that venue
  4. Blend = 70% recent-3yr delta + 30% all-time delta
     (falls back to all-time only if recent_n < 8)
  5. Clamp at +-10 pts

Outputs blended venue deltas ready to paste into afl_tier4_venue.py.
"""

import pandas as pd

XLSX   = "outputs/afl_weekly_review/historical/afl_20260616_160032.xlsx"
RECENT = 3   # years to weight at 70%
W_REC  = 0.7
W_ALL  = 0.3
MIN_N_RECENT = 8
MIN_N_TOTAL  = 15
CLAMP        = 10.0

# ── Load ──────────────────────────────────────────────────────────────────────
df = pd.read_excel(XLSX, header=1)
df.columns = (
    ["Date", "KickOff", "HomeTeam", "AwayTeam", "Venue",
     "HomeScore", "AwayScore", "Playoff", "HomeGoals", "HomeBehinds",
     "AwayGoals", "AwayBehinds"]
    + list(range(len(df.columns) - 12))
)

df["HomeScore"] = pd.to_numeric(df["HomeScore"], errors="coerce")
df["AwayScore"]  = pd.to_numeric(df["AwayScore"],  errors="coerce")
df = df[df["HomeScore"].notna() & df["AwayScore"].notna()].copy()
df = df[df["Playoff"].isna() | (df["Playoff"] == 0)].copy()  # regular season only
df["Total"] = df["HomeScore"] + df["AwayScore"]
df["Date"]  = pd.to_datetime(df["Date"], errors="coerce")
df["Year"]  = df["Date"].dt.year.astype("Int64")
df = df[df["Year"] >= 2018].copy()

# Normalise venue names (handle name changes over the data period)
VENUE_NORM = {
    "Docklands":                "Marvel Stadium",
    "Etihad Stadium":           "Marvel Stadium",
    "Blundstone Arena":         "UTAS Stadium",
    "Kardinia Park":            "GMHBA Stadium",
    "Spotless Stadium":         "ENGIE Stadium",
    "GIANTS Stadium":           "ENGIE Stadium",
    "Sydney Showground":        "ENGIE Stadium",
    "Cazalys Stadium":          "Cazalys Stadium",
    "TIO Traeger Park":         "Traeger Park",
    "TIO Stadium":              "TIO Stadium",
    "Heritage Bank Stadium":    "People First Stadium",
    "Metricon Stadium":         "People First Stadium",
    "Cbus Super Stadium":       "People First Stadium",
    "The Gabba":                "The Gabba",
    "Gabba":                    "The Gabba",
    "Ninja Stadium":            "Ninja Stadium",
}
df["Venue"] = df["Venue"].map(lambda v: VENUE_NORM.get(str(v).strip(), str(v).strip()))

# ── Season averages ───────────────────────────────────────────────────────────
season_avg = df.groupby("Year")["Total"].mean()
df["SeasonAvg"] = df["Year"].map(season_avg)
df["Residual"]  = df["Total"] - df["SeasonAvg"]

# ── All-time stats ────────────────────────────────────────────────────────────
all_stats = (
    df.groupby("Venue")
    .agg(n_all=("Residual", "count"), delta_all=("Residual", "mean"))
    .reset_index()
)

# ── Recent-n-year stats ───────────────────────────────────────────────────────
max_year = df["Year"].max()
recent = df[df["Year"] >= max_year - RECENT + 1].copy()
rec_avg = recent.groupby("Year")["Total"].mean()
recent["SeasonAvg"] = recent["Year"].map(rec_avg)
recent["Residual"]  = recent["Total"] - recent["SeasonAvg"]
rec_stats = (
    recent.groupby("Venue")
    .agg(n_rec=("Residual", "count"), delta_rec=("Residual", "mean"))
    .reset_index()
)

merged = pd.merge(all_stats, rec_stats, on="Venue", how="left")
merged["n_rec"]    = merged["n_rec"].fillna(0).astype(int)
merged["delta_rec"] = merged["delta_rec"].fillna(0.0)

# ── Blend ─────────────────────────────────────────────────────────────────────
def blend(row):
    if row["n_rec"] >= MIN_N_RECENT:
        b = W_REC * row["delta_rec"] + W_ALL * row["delta_all"]
    else:
        b = row["delta_all"]           # not enough recent data — use all-time
    return max(-CLAMP, min(CLAMP, round(b, 1)))

merged["blended"] = merged.apply(blend, axis=1)
merged = merged[merged["n_all"] >= MIN_N_TOTAL].sort_values("blended")

# ── Print ─────────────────────────────────────────────────────────────────────
print("AFL VENUE SCORING DELTAS — season-adjusted, 70/30 recent/all-time blend")
print("=" * 85)
print(f"  {'Venue':<35} {'N_all':>6} {'N_rec':>6} {'All-time':>10} {'Recent3yr':>10} {'BLENDED':>10}")
print("-" * 85)
for _, r in merged.iterrows():
    rec_str = f"{r['delta_rec']:>+.1f}" if r["n_rec"] >= MIN_N_RECENT else "  n/a "
    print(f"  {r['Venue']:<35} {int(r['n_all']):>6} {int(r['n_rec']):>6} "
          f"{r['delta_all']:>+10.1f} {rec_str:>10} {r['blended']:>+10.1f}")

print()
print("Ready to paste into VENUE_SCORING_PROFILE in afl_tier4_venue.py")
print()
print("Python dict:")
print("VENUE_SCORING_PROFILE = {")
for _, r in merged.sort_values("Venue").iterrows():
    print(f"    '{r['Venue']}': {r['blended']:>+.1f},   # n={int(r['n_all'])} games ({int(r['n_rec'])} recent)")
print("}")
