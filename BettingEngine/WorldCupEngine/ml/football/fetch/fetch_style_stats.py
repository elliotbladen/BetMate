"""
Fetch team-level PPDA and style stats from Understat (same API, no extra requests).

PPDA = Passes Per Defensive Action — lower = higher press intensity.
Also captures: deep completions, xG, xGA, npxG, npxGA per team per season.

The Understat getLeagueData API returns team history with per-match PPDA.
We aggregate to rolling averages for use as T2 style features.

Output:
  ml/football/data/style/ppda_by_season.csv   — season-level team averages
  ml/football/data/style/ppda_rolling.csv     — rolling 10-game PPDA per team

Usage:
    python ml/football/fetch/fetch_style_stats.py
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

OUT_DIR = Path(__file__).parent.parent / "data" / "epl" / "style"

BASE_URL = "https://understat.com/getLeagueData/EPL/{year}"
SEASONS  = list(range(2014, 2025))
SLEEP    = 1.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://understat.com/league/EPL/2023",
    "X-Requested-With": "XMLHttpRequest",
}

TEAM_MAP = {
    "Manchester City":         "Man City",
    "Manchester United":       "Man United",
    "Newcastle United":        "Newcastle",
    "Nottingham Forest":       "Nott'm Forest",
    "West Bromwich Albion":    "West Brom",
    "Wolverhampton Wanderers": "Wolves",
    "Leeds United":            "Leeds",
    "Sheffield United":        "Sheffield United",
    "Tottenham":               "Tottenham",
    "West Ham":                "West Ham",
}


def _norm(name: str) -> str:
    return TEAM_MAP.get(name, name)


def _ppda_ratio(ppda: dict) -> float | None:
    """PPDA = attacking_passes / defensive_actions in opponent half."""
    try:
        att = float(ppda["att"])
        def_ = float(ppda["def"])
        return round(att / def_, 2) if def_ > 0 else None
    except (KeyError, TypeError, ValueError):
        return None


def fetch_season_style(year: int) -> tuple[list[dict], list[dict]]:
    """
    Returns (season_rows, match_rows).
    season_rows: one row per team with season-average PPDA/xG stats.
    match_rows: one row per team-match with per-game PPDA.
    """
    label = f"{year}/{str(year+1)[-2:]}"
    url   = BASE_URL.format(year=year)

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ERROR {label}: {e}")
        return [], []

    teams_data = data.get("teams", {})
    season_rows = []
    match_rows  = []

    for team_id, team_info in teams_data.items():
        name  = _norm(team_info["title"])
        hist  = team_info.get("history", [])

        ppda_vals    = [_ppda_ratio(m["ppda"]) for m in hist if _ppda_ratio(m["ppda"]) is not None]
        ppda_allowed = [_ppda_ratio(m["ppda_allowed"]) for m in hist if _ppda_ratio(m["ppda_allowed"]) is not None]

        season_rows.append({
            "season":        label,
            "team":          name,
            "games":         len(hist),
            "ppda_avg":      round(sum(ppda_vals) / len(ppda_vals), 2) if ppda_vals else None,
            "ppda_allowed_avg": round(sum(ppda_allowed) / len(ppda_allowed), 2) if ppda_allowed else None,
            "xg_avg":        round(sum(float(m["xG"]) for m in hist) / len(hist), 3) if hist else None,
            "xga_avg":       round(sum(float(m["xGA"]) for m in hist) / len(hist), 3) if hist else None,
            "npxg_avg":      round(sum(float(m["npxG"]) for m in hist) / len(hist), 3) if hist else None,
            "npxga_avg":     round(sum(float(m["npxGA"]) for m in hist) / len(hist), 3) if hist else None,
        })

        # Per-match rolling data
        for i, m in enumerate(hist):
            ppda_val = _ppda_ratio(m["ppda"])
            match_rows.append({
                "season":  label,
                "team":    name,
                "h_a":     m["h_a"],          # "h" or "a"
                "game_n":  i + 1,
                "ppda":    ppda_val,
                "xg":      float(m["xG"]),
                "xga":     float(m["xGA"]),
                "npxg":    float(m["npxG"]),
                "npxga":   float(m["npxGA"]),
                "wins":    int(m["wins"]),
                "draws":   int(m["draws"]),
                "loses":   int(m["loses"]),
            })

    print(f"  {label}: {len(season_rows)} teams, {len(match_rows)} team-matches")
    return season_rows, match_rows


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_season_rows = []
    all_match_rows  = []

    for year in SEASONS:
        label = f"{year}/{str(year+1)[-2:]}"
        print(f"Fetching style stats {label} ...")
        s_rows, m_rows = fetch_season_style(year)
        all_season_rows.extend(s_rows)
        all_match_rows.extend(m_rows)
        time.sleep(SLEEP)

    if all_season_rows:
        season_df = pd.DataFrame(all_season_rows)
        out = OUT_DIR / "ppda_by_season.csv"
        season_df.to_csv(out, index=False)
        print(f"\nSaved {len(season_df)} season rows to {out}")
        print("\nTop 10 highest-press teams (lowest PPDA) across all seasons:")
        print(season_df.nsmallest(10, "ppda_avg")[["season", "team", "ppda_avg", "xg_avg"]].to_string(index=False))

    if all_match_rows:
        match_df = pd.DataFrame(all_match_rows)
        # Compute rolling 10-game PPDA per team-season
        match_df = match_df.sort_values(["season", "team", "game_n"])
        match_df["ppda_rolling10"] = (
            match_df.groupby(["season", "team"])["ppda"]
            .transform(lambda x: x.rolling(10, min_periods=3).mean().round(2))
        )
        out = OUT_DIR / "ppda_rolling.csv"
        match_df.to_csv(out, index=False)
        print(f"Saved {len(match_df)} match rows to {out}")


if __name__ == "__main__":
    main()
