"""
Backtest: does the new T4B venue scoring profile improve AFL totals MAE?

Method:
  1. Load actual 2026 results from historical xlsx
  2. Join with afl_shadow_predictions from DB by (home_team, round_number)
  3. For each game: new_rules_total = rules_total - old_t4_tot + new_t4_tot
  4. Compare MAE before vs after, per venue and overall
"""

import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB   = ROOT / "data" / "model.db"
XLSX = ROOT / "outputs" / "afl_weekly_review" / "historical" / "afl_20260616_160032.xlsx"

# ── Old profile (30% scaled, no season adjustment, old cap=5) ────────────────
OLD_PROFILE = {
    'ENGIE Stadium':          +2.0,
    'Marvel Stadium':         +1.9,
    'Marvel':                 +1.9,
    'Docklands':              +1.9,
    'Ninja Stadium':          +1.5,
    'Manuka Oval':            +1.2,
    'GMHBA Stadium':          +1.5,
    'Kardinia Park':          +1.5,
    'SCG':                    +0.5,
    'Optus Stadium':          -0.9,
    'The Gabba':              -1.0,
    'Gabba':                  -1.0,
    'UTAS Stadium':           -1.5,
    'Blundstone Arena':       -1.5,
    'People First Stadium':   -4.6,
    'Cazalys Stadium':        -3.0,
    'TIO Stadium':            -3.0,
    'Traeger Park':           -3.0,
}
OLD_CAP = 5.0

# ── New profile (season-adjusted 70/30, new cap=10) ──────────────────────────
NEW_PROFILE = {
    'UTAS Stadium':           -10.0,
    'Blundstone Arena':       -10.0,
    'Optus Stadium':           -7.8,
    'Adelaide Oval':           -4.2,
    'MCG':                     -3.9,
    'Manuka Oval':             +0.7,
    'People First Stadium':    +2.0,
    'Ninja Stadium':           +2.3,
    'The Gabba':               +2.4,
    'Gabba':                   +2.4,
    'Marvel Stadium':          +4.5,
    'Marvel':                  +4.5,
    'Docklands':               +4.5,
    'SCG':                     +5.4,
    'GMHBA Stadium':           +6.0,
    'Kardinia Park':           +6.0,
    'ENGIE Stadium':           +8.7,
    'TIO Stadium':            +10.0,
    'Cazalys Stadium':         -3.0,
    'Traeger Park':            -3.0,
}
NEW_CAP = 10.0

VENUE_NORM = {
    "Docklands":                "Marvel Stadium",
    "Etihad Stadium":           "Marvel Stadium",
    "Blundstone Arena":         "UTAS Stadium",
    "Kardinia Park":            "GMHBA Stadium",
    "Spotless Stadium":         "ENGIE Stadium",
    "GIANTS Stadium":           "ENGIE Stadium",
    "Sydney Showground":        "ENGIE Stadium",
    "Heritage Bank Stadium":    "People First Stadium",
    "Metricon Stadium":         "People First Stadium",
    "Cbus Super Stadium":       "People First Stadium",
    "The Gabba":                "The Gabba",
    "Gabba":                    "The Gabba",
}


def clamp(v, cap):
    return max(-cap, min(cap, v))


# ── Load xlsx actuals for 2026 ────────────────────────────────────────────────
raw = pd.read_excel(XLSX, header=1)
raw.columns = (
    ["Date", "KickOff", "HomeTeam", "AwayTeam", "Venue",
     "HomeScore", "AwayScore", "Playoff", "HomeGoals", "HomeBehinds",
     "AwayGoals", "AwayBehinds"]
    + list(range(len(raw.columns) - 12))
)
raw["HomeScore"] = pd.to_numeric(raw["HomeScore"], errors="coerce")
raw["AwayScore"]  = pd.to_numeric(raw["AwayScore"],  errors="coerce")
raw = raw[raw["HomeScore"].notna() & raw["AwayScore"].notna()].copy()
raw = raw[raw["Playoff"].isna() | (raw["Playoff"] == 0)].copy()
raw["Date"]   = pd.to_datetime(raw["Date"], errors="coerce")
raw["Year"]   = raw["Date"].dt.year
raw["Total"]  = raw["HomeScore"] + raw["AwayScore"]
raw["Venue"]  = raw["Venue"].map(lambda v: VENUE_NORM.get(str(v).strip(), str(v).strip()))
actuals_2026  = raw[raw["Year"] == 2026][["HomeTeam", "AwayTeam", "Venue", "Total"]].copy()
actuals_2026.columns = ["home_team_xlsx", "away_team_xlsx", "venue_xlsx", "actual_total"]

# Normalise xlsx team names to match DB (DB uses full Odds API names)
TEAM_NORM_XLSX = {
    "Adelaide":          "Adelaide Crows",
    "Brisbane":          "Brisbane Lions",
    "Carlton":           "Carlton Blues",
    "Collingwood":       "Collingwood Magpies",
    "Essendon":          "Essendon Bombers",
    "Fremantle":         "Fremantle Dockers",
    "Geelong":           "Geelong Cats",
    "GWS":               "Greater Western Sydney Giants",
    "Hawthorn":          "Hawthorn Hawks",
    "Melbourne":         "Melbourne Demons",
    "North Melbourne":   "North Melbourne Kangaroos",
    "Port Adelaide":     "Port Adelaide Power",
    "Richmond":          "Richmond Tigers",
    "St Kilda":          "St Kilda Saints",
    "Sydney":            "Sydney Swans",
    "West Coast":        "West Coast Eagles",
    "Western Bulldogs":  "Western Bulldogs",
    "Gold Coast":        "Gold Coast Suns",
}
actuals_2026["home_team_db"] = actuals_2026["home_team_xlsx"].map(
    lambda n: TEAM_NORM_XLSX.get(str(n).strip(), str(n).strip())
)

# ── Load DB predictions ───────────────────────────────────────────────────────
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
preds = conn.execute("""
    SELECT season, round_number, home_team, away_team, venue,
           rules_total, t4_tot
    FROM   afl_shadow_predictions
    WHERE  season = 2026
    ORDER  BY round_number, game_date
""").fetchall()
conn.close()

if not preds:
    print("No predictions found in afl_shadow_predictions for 2026.")
    raise SystemExit(0)

# ── Join predictions with actuals ─────────────────────────────────────────────
records = []
unmatched = []

for p in preds:
    match = actuals_2026[actuals_2026["home_team_db"] == p["home_team"]]
    if match.empty:
        unmatched.append(f"R{p['round_number']} {p['home_team']}")
        continue

    actual = match.iloc[0]["actual_total"]

    old_t4_stored = p["t4_tot"]
    new_t4 = clamp(NEW_PROFILE.get(p["venue"], 0.0), NEW_CAP)

    new_rules_tot = p["rules_total"] - old_t4_stored + new_t4

    records.append({
        "round":        p["round_number"],
        "home":         p["home_team"],
        "away":         p["away_team"],
        "venue":        p["venue"],
        "old_t4":       old_t4_stored,
        "new_t4":       new_t4,
        "old_pred":     p["rules_total"],
        "new_pred":     new_rules_tot,
        "actual":       actual,
        "old_err":      abs(p["rules_total"] - actual),
        "new_err":      abs(new_rules_tot - actual),
    })

if unmatched:
    print(f"Note: {len(unmatched)} predictions unmatched to actuals: {unmatched[:5]}")

if not records:
    print("No matched records found.")
    raise SystemExit(0)

# ── Summary ───────────────────────────────────────────────────────────────────
n = len(records)
old_mae = sum(r["old_err"] for r in records) / n
new_mae = sum(r["new_err"] for r in records) / n
improved = sum(1 for r in records if r["new_err"] < r["old_err"] - 0.05)
worsened = sum(1 for r in records if r["new_err"] > r["old_err"] + 0.05)

print("AFL T4B VENUE — BACKTEST RESULTS (2026 R8–R14)")
print("=" * 65)
print(f"  Games matched:        {n}")
print(f"  Old T4B rules MAE:    {old_mae:.2f} pts")
print(f"  New T4B rules MAE:    {new_mae:.2f} pts  ({new_mae - old_mae:+.2f})")
print(f"  Games improved:       {improved}/{n} ({100*improved/n:.0f}%)")
print(f"  Games worsened:       {worsened}/{n} ({100*worsened/n:.0f}%)")
print()

# Per-venue breakdown
from collections import defaultdict
venue_old = defaultdict(list)
venue_new = defaultdict(list)
venue_delta = defaultdict(list)
for r in records:
    venue_old[r["venue"]].append(r["old_err"])
    venue_new[r["venue"]].append(r["new_err"])
    venue_delta[r["venue"]].append(r["new_t4"] - r["old_t4"])

print(f"  {'Venue':<28} {'N':>4}  {'T4 delta':>9}  {'Old MAE':>8}  {'New MAE':>8}  {'Change':>8}")
print("  " + "-" * 72)
for v in sorted(venue_old, key=lambda v: -len(venue_old[v])):
    n_v = len(venue_old[v])
    d = sum(venue_delta[v]) / n_v
    o = sum(venue_old[v]) / n_v
    ne = sum(venue_new[v]) / n_v
    flag = " OK" if ne < o - 0.5 else (" XX" if ne > o + 0.5 else "  -")
    print(f"  {v:<28} {n_v:>4}  {d:>+9.2f}  {o:>8.2f}  {ne:>8.2f}  {ne-o:>+8.2f}{flag}")

print()
print(f"  OVERALL: {old_mae:.2f} -> {new_mae:.2f} pts MAE  ({new_mae-old_mae:+.2f})")

# ── Bias (mean signed error) — the real test for systematic venue mismatch ────
print()
print("BIAS (mean signed error = pred - actual, positive = over-predicting)")
print("=" * 65)
old_bias = sum(r["old_pred"] - r["actual"] for r in records) / n
new_bias = sum(r["new_pred"] - r["actual"] for r in records) / n
print(f"  Overall old bias: {old_bias:+.2f} pts")
print(f"  Overall new bias: {new_bias:+.2f} pts  ({new_bias - old_bias:+.2f})")
print()
print(f"  {'Venue':<28} {'N':>4}  {'Old bias':>9}  {'New bias':>9}  {'Change':>8}")
print("  " + "-" * 65)
for v in sorted(venue_old, key=lambda v: -len(venue_old[v])):
    n_v = len(venue_old[v])
    match_v = [r for r in records if r["venue"] == v]
    old_b = sum(r["old_pred"] - r["actual"] for r in match_v) / n_v
    new_b = sum(r["new_pred"] - r["actual"] for r in match_v) / n_v
    closer = abs(new_b) < abs(old_b)
    flag = " OK" if closer else "  -"
    print(f"  {v:<28} {n_v:>4}  {old_b:>+9.2f}  {new_b:>+9.2f}  {new_b-old_b:>+8.2f}{flag}")
