"""
Compute Championship pressing proxy from football-data.co.uk match stats.

PPDA (Passes Per Defensive Action) is unavailable for the Championship —
Understat only covers the top-5 European leagues. Instead we compute a proxy:

    press_proxy = opponent_shots_per_match (rolling 10-game average)

This correlates strongly with PPDA: high-pressing teams allow fewer opponent
shots (low proxy = low PPDA = intense press), low-block teams concede many
shots (high proxy = high PPDA = passive press).

2024/25 Championship validation:
    Leeds 6.7 (high press) → Burnley 9.4 → Sheff Utd 10.9 → Plymouth 15.7 (low press)
    Range 6.7–15.7, mean 11.8 — directly comparable to EPL PPDA scale (8–20, mean ~13).

Input:  ml/football/data/championship/matches/championship_matches.csv
        (must contain HS, AS, Date columns — populated by fetch_results.py)

Output: ml/football/data/championship/style/ppda_dated.csv
        (season, team, game_n, ppda_rolling10, date — consumed by price_match.py)

Usage:
    python ml/football/fetch/fetch_championship_ppda.py
    python ml/football/fetch/fetch_championship_ppda.py --season 2026/27
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data" / "championship"
MATCHES_CSV = DATA_DIR / "matches" / "championship_matches.csv"
OUT_CSV = DATA_DIR / "style" / "ppda_dated.csv"

ROLLING_WINDOW = 10
MIN_PERIODS = 3

# Pre-season seed for teams entering the Championship with no historical data.
# Values are their final EPL PPDA (from Understat) or estimated from league level.
# These are used as the fallback when a team has < MIN_PERIODS Championship games.
PRESEASON_SEEDS: dict[str, dict[str, float]] = {
    "2026/27": {
        "Burnley": 11.8,       # EPL 2023/24: 11.76
        "West Ham": 13.8,      # EPL 2024/25: 13.82
        "Wolves": 13.1,        # EPL 2024/25: 13.05
        "Bolton": 14.5,        # L1 promoted — estimate
        "Cardiff": 14.5,       # L1 promoted — estimate
        "Lincoln": 14.5,       # L1 promoted — estimate
        "Southampton": 14.5,   # EPL 2024/25: 15.80, but adapted to Championship
    },
}


def compute_ppda_proxy(matches_csv: Path = MATCHES_CSV,
                       season_filter: str | None = None) -> pd.DataFrame:
    """Compute opponent-shots pressing proxy from Championship match stats."""
    df = pd.read_csv(matches_csv, parse_dates=["Date"])

    # Need shots columns
    if "HS" not in df.columns or "AS" not in df.columns:
        raise ValueError("Matches CSV missing HS/AS columns — re-run fetch_results.py")

    df = df.dropna(subset=["HS", "AS", "Date"])

    # Build per-team-match records: each team's "shots faced" in that match
    rows = []
    for _, m in df.iterrows():
        home, away = m["HomeTeam"], m["AwayTeam"]
        date, season = m["Date"], m["Season"]
        # Home team faced AS (away shots), away team faced HS (home shots)
        rows.append({"season": season, "team": home, "date": date, "shots_faced": float(m["AS"])})
        rows.append({"season": season, "team": away, "date": date, "shots_faced": float(m["HS"])})

    team_df = pd.DataFrame(rows).sort_values(["team", "date"]).reset_index(drop=True)

    # Number games per team (across all seasons, chronologically)
    team_df["game_n"] = team_df.groupby("team").cumcount() + 1

    # Rolling 10-game average of shots faced (= our PPDA proxy)
    team_df["ppda_rolling10"] = (
        team_df.groupby("team")["shots_faced"]
        .transform(lambda x: x.rolling(ROLLING_WINDOW, min_periods=MIN_PERIODS).mean().round(2))
    )

    # Drop rows before rolling kicks in
    out = team_df.dropna(subset=["ppda_rolling10"]).copy()

    # Re-number game_n within each season
    out["game_n"] = out.groupby(["season", "team"]).cumcount() + 1

    result = out[["season", "team", "game_n", "ppda_rolling10", "date"]].copy()
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")

    if season_filter:
        result = result[result["season"] == season_filter]

    return result


def add_preseason_seeds(df: pd.DataFrame, season: str) -> pd.DataFrame:
    """Add seed rows for teams with no computed data in the target season."""
    seeds = PRESEASON_SEEDS.get(season, {})
    if not seeds:
        return df

    # Find teams already in the season's computed data
    season_teams = set(df[df["season"] == season]["team"].unique()) if not df.empty else set()

    seed_rows = []
    for team, ppda in seeds.items():
        if team not in season_teams:
            seed_rows.append({
                "season": season,
                "team": team,
                "game_n": 0,
                "ppda_rolling10": ppda,
                "date": _season_start_date(season),
            })

    if seed_rows:
        seed_df = pd.DataFrame(seed_rows)
        df = pd.concat([seed_df, df], ignore_index=True)
        df = df.sort_values(["date", "team"]).reset_index(drop=True)

    return df


def _season_start_date(season: str) -> str:
    """Return pre-season date for seed entries (Aug 1 of start year)."""
    year = int(season.split("/")[0])
    return f"{year}-08-01"


def main():
    parser = argparse.ArgumentParser(description="Compute Championship pressing proxy")
    parser.add_argument("--season", default=None, help="Filter to single season (e.g. 2026/27)")
    args = parser.parse_args()

    if not MATCHES_CSV.exists():
        print(f"ERROR: {MATCHES_CSV} not found — run fetch_results.py --league championship first")
        return

    print(f"Reading {MATCHES_CSV} ...")
    result = compute_ppda_proxy(season_filter=args.season)
    print(f"Computed {len(result)} team-match PPDA proxy rows")

    # Always add pre-season seeds for seasons that have them
    for seed_season in PRESEASON_SEEDS:
        if args.season is None or args.season == seed_season:
            before = len(result)
            result = add_preseason_seeds(result, seed_season)
            added = len(result) - before
            if added:
                print(f"Added {added} pre-season seeds for {seed_season}")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT_CSV, index=False)
    print(f"Saved to {OUT_CSV}")

    # Summary for latest season
    latest = result["season"].iloc[-1] if not result.empty else "?"
    season_data = result[result["season"] == latest]
    if not season_data.empty:
        latest_per_team = season_data.groupby("team")["ppda_rolling10"].last().sort_values()
        print(f"\n{latest} pressing proxy (lower = more pressing):")
        for team, val in latest_per_team.items():
            print(f"  {team:25s} {val:.1f}")
        print(f"\n  League avg: {latest_per_team.mean():.1f}")


if __name__ == "__main__":
    main()
