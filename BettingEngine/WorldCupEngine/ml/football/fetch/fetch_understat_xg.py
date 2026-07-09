"""
Fetch match-level xG from Understat for EPL 2014/15 – 2024/25.

Uses the undocumented Understat JSON API (same source as understatapi package).
No authentication required. Rate-limited to 1 req/s to be polite.

Output: ml/football/data/xg/understat_xg.csv

Columns:
  season, date, home_team, away_team,
  home_xg, away_xg, home_goals, away_goals,
  understat_match_id
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

OUT_DIR = Path(__file__).parent.parent / "data" / "epl" / "xg"
OUT_CSV = OUT_DIR / "understat_xg.csv"

BASE_URL = "https://understat.com/getLeagueData/EPL/{year}"
SEASONS = list(range(2014, 2025))  # 2014 = 2014/15, ..., 2024 = 2024/25
SLEEP   = 1.5  # seconds between requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://understat.com/league/EPL/2023",
    "X-Requested-With": "XMLHttpRequest",
}

# Understat team names → normalised names matching football-data.co.uk
TEAM_MAP = {
    "Manchester City":    "Man City",
    "Manchester United":  "Man United",
    "Newcastle United":   "Newcastle",
    "Tottenham":          "Tottenham",
    "Nottingham Forest":  "Nott'm Forest",
    "West Bromwich Albion": "West Brom",
    "West Ham":           "West Ham",
    "Wolverhampton Wanderers": "Wolves",
    "Sheffield United":   "Sheffield United",
    "Leeds United":       "Leeds",
    "Brentford":          "Brentford",
    "Brighton":           "Brighton",
    "Leicester":          "Leicester",
    "Aston Villa":        "Aston Villa",
    "Crystal Palace":     "Crystal Palace",
    "Bournemouth":        "Bournemouth",
    "Fulham":             "Fulham",
    "Burnley":            "Burnley",
    "Watford":            "Watford",
    "Southampton":        "Southampton",
    "Chelsea":            "Chelsea",
    "Arsenal":            "Arsenal",
    "Liverpool":          "Liverpool",
    "Everton":            "Everton",
    "Stoke":              "Stoke",
    "Swansea":            "Swansea",
    "Huddersfield":       "Huddersfield",
    "Cardiff":            "Cardiff",
    "Norwich":            "Norwich",
    "Sunderland":         "Sunderland",
    "Middlesbrough":      "Middlesbrough",
    "Hull":               "Hull",
    "QPR":                "QPR",
    "Blackburn":          "Blackburn",
    "Wigan":              "Wigan",
    "Bolton":             "Bolton",
    "Ipswich":            "Ipswich",
    "Luton":              "Luton",
}


def _normalise(name: str) -> str:
    return TEAM_MAP.get(name, name)


def fetch_season(year: int) -> list[dict]:
    label = f"{year}/{str(year+1)[-2:]}"
    url   = BASE_URL.format(year=year)

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ERROR {label}: {e}")
        return []

    matches = data.get("dates", [])
    if not matches:
        print(f"  {label}: no match data returned")
        return []

    rows = []
    for match in matches:
        try:
            if not match.get("isResult"):
                continue  # skip future matches
            rows.append({
                "season":             label,
                "date":               match["datetime"][:10],
                "home_team":          _normalise(match["h"]["title"]),
                "away_team":          _normalise(match["a"]["title"]),
                "home_xg":            float(match["xG"]["h"]),
                "away_xg":            float(match["xG"]["a"]),
                "home_goals":         int(match["goals"]["h"]),
                "away_goals":         int(match["goals"]["a"]),
                "understat_match_id": match["id"],
            })
        except (KeyError, TypeError, ValueError):
            continue

    print(f"  {label}: {len(rows)} matches")
    return rows


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing data to avoid re-fetching complete seasons
    existing_seasons: set[str] = set()
    if OUT_CSV.exists():
        existing = pd.read_csv(OUT_CSV)
        # Only skip seasons where we have a full dataset (≥350 matches)
        counts = existing.groupby("season").size()
        existing_seasons = set(counts[counts >= 350].index)
        print(f"Already have complete data for: {sorted(existing_seasons)}")

    all_rows: list[dict] = []
    if OUT_CSV.exists():
        all_rows = pd.read_csv(OUT_CSV).to_dict("records")

    for year in SEASONS:
        label = f"{year}/{str(year+1)[-2:]}"
        if label in existing_seasons:
            print(f"  {label}: skipping (already complete)")
            continue

        print(f"Fetching {label} ...")
        rows = fetch_season(year)
        if rows:
            # Remove any existing rows for this season and replace
            all_rows = [r for r in all_rows if r.get("season") != label]
            all_rows.extend(rows)
        time.sleep(SLEEP)

    if not all_rows:
        print("No data.")
        return

    df = pd.DataFrame(all_rows).sort_values(["date", "home_team"])
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved {len(df)} matches to {OUT_CSV}")
    print(f"Seasons: {df['season'].nunique()}")
    print(f"Date range: {df['date'].min()} – {df['date'].max()}")
    print(f"Avg home xG: {df['home_xg'].mean():.3f}")
    print(f"Avg away xG: {df['away_xg'].mean():.3f}")


if __name__ == "__main__":
    main()
