#!/usr/bin/env python3
"""
fetch/fetch_clubelo.py — Fetch ClubElo ratings at the start of each Championship season.

ClubElo is a free API covering all English football tiers.
API: http://api.clubelo.com/YYYY-MM-DD  → CSV of all clubs on that date.

Fields: Rank, Club, Country, Level, Elo, From, To
Level:  1=PL, 2=Championship, 3=League One, 4=League Two

We fetch ratings on August 1 of each season start year (before the season begins)
and save all English clubs at Level 1–3 so the T8 tier can seed new Championship
teams from ClubElo rather than blind league-average priors.

Output: data/championship/clubelo/season_ratings.csv
  season, club, elo, level

Usage:
    python ml/football/fetch/fetch_clubelo.py
    python ml/football/fetch/fetch_clubelo.py --seasons 2021/22 2022/23
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests

_ROOT = Path(__file__).resolve().parents[4]   # → BettingEngine/
sys.path.insert(0, str(_ROOT))

OUT_PATH = (
    _ROOT / "WorldCupEngine" / "ml" / "football"
    / "data" / "championship" / "clubelo" / "season_ratings.csv"
)

CLUBELO_DATE_URL = "http://api.clubelo.com/{date}"
HEADERS = {"User-Agent": "Mozilla/5.0 (academic/research use)", "Accept": "text/csv,*/*"}

DEFAULT_SEASONS = [
    "2014/15", "2015/16", "2016/17", "2017/18", "2018/19",
    "2019/20", "2020/21", "2021/22", "2022/23", "2023/24",
    "2024/25", "2025/26",
]

# Levels to save: PL (1), Championship (2), League One (3)
ENGLISH_LEVELS = {1, 2, 3}


def season_to_date(season: str) -> str:
    """'2021/22' → '2021-08-01'  (just before season starts)."""
    return f"{season.split('/')[0]}-08-01"


def fetch_on_date(date: str) -> pd.DataFrame | None:
    url = CLUBELO_DATE_URL.format(date=date)
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as exc:
        print(f"FAILED: {exc}")
        return None


def process_season(season: str) -> pd.DataFrame | None:
    date = season_to_date(season)
    print(f"  {season} ({date}) ...", end=" ", flush=True)

    raw = fetch_on_date(date)
    if raw is None:
        return None

    eng = raw[raw["Country"].astype(str).str.strip() == "ENG"].copy()
    eng["Level"] = pd.to_numeric(eng["Level"], errors="coerce")
    eng = eng[eng["Level"].isin(ENGLISH_LEVELS)].copy()

    if eng.empty:
        print("no English clubs found")
        return None

    result = pd.DataFrame({
        "season": season,
        "club":   eng["Club"].str.strip().values,
        "elo":    pd.to_numeric(eng["Elo"], errors="coerce").values,
        "level":  eng["Level"].astype(int).values,
    })
    print(f"OK ({len(result)} English clubs L1–3)")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", nargs="+", default=None,
                        help="Seasons to fetch e.g. '2021/22 2022/23'")
    args = parser.parse_args()

    seasons = args.seasons or DEFAULT_SEASONS
    all_rows: list[pd.DataFrame] = []

    for season in seasons:
        rows = process_season(season)
        if rows is not None:
            all_rows.append(rows)
        time.sleep(1.5)  # polite rate-limit for free API

    if not all_rows:
        print("No data fetched — check API connectivity.")
        return

    combined = pd.concat(all_rows, ignore_index=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUT_PATH, index=False)

    l2 = combined[combined["level"] == 2]
    print(f"\nSaved {len(combined)} rows → {OUT_PATH.relative_to(_ROOT)}")
    print(f"  Seasons: {combined['season'].nunique()}")
    print(f"  Level-2 rows: {len(l2)}")
    if not l2.empty:
        avg = l2.groupby("season")["elo"].mean()
        print(f"  Championship avg ELO by season:\n{avg.to_string()}")


if __name__ == "__main__":
    main()
