"""
Fetch EPL match results + bookmaker odds from football-data.co.uk.

Seasons: 2014/15 – 2024/25 (11 seasons)
Output:  ml/football/data/matches/epl_matches.csv

Columns retained:
  Date, Season, HomeTeam, AwayTeam, FTHG, FTAG, FTR,
  Referee, B365H, B365D, B365A, MaxH, MaxD, MaxA,
  Max>2.5, Max<2.5, MaxAHH (Asian Handicap)
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

OUT_DIR = Path(__file__).parent.parent / "data" / "epl" / "matches"
OUT_CSV = OUT_DIR / "epl_matches.csv"

# football-data.co.uk URL pattern
BASE_URL = "https://www.football-data.co.uk/mmz4281/{code}/E0.csv"

SEASONS = [
    ("1415", "2014/15"),
    ("1516", "2015/16"),
    ("1617", "2016/17"),
    ("1718", "2017/18"),
    ("1819", "2018/19"),
    ("1920", "2019/20"),
    ("2021", "2020/21"),
    ("2122", "2021/22"),
    ("2223", "2022/23"),
    ("2324", "2023/24"),
    ("2425", "2024/25"),
]

# Columns to keep (some may be absent in older seasons — handled gracefully)
KEEP_COLS = [
    "Date", "HomeTeam", "AwayTeam",
    "FTHG", "FTAG", "FTR",
    "Referee",
    "HS", "AS",           # shots
    "HST", "AST",         # shots on target
    "HC", "AC",           # corners
    "HF", "AF",           # fouls
    "HY", "AY",           # yellow cards
    "B365H", "B365D", "B365A",
    "MaxH",  "MaxD",  "MaxA",
    "Max>2.5", "Max<2.5",
    "MaxAHH", "MaxAHA", "AHh",
]

DATE_FMTS = ["%d/%m/%Y", "%d/%m/%y"]


def _parse_date(s: str) -> pd.Timestamp | None:
    for fmt in DATE_FMTS:
        try:
            return pd.to_datetime(s, format=fmt)
        except Exception:
            pass
    return pd.NaT


def fetch_season(code: str, label: str) -> pd.DataFrame | None:
    url = BASE_URL.format(code=code)
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  ERROR {label}: {e}")
        return None

    df = pd.read_csv(io.StringIO(r.text), encoding="latin-1", on_bad_lines="skip")
    df["Season"] = label

    # Parse dates
    if "Date" in df.columns:
        df["Date"] = df["Date"].apply(_parse_date)
        df = df[df["Date"].notna()]

    # Keep only recognised columns
    cols = ["Season"] + [c for c in KEEP_COLS if c in df.columns]
    df = df[cols].copy()

    # Drop rows with no result
    df = df[df["FTR"].isin(["H", "D", "A"])]

    print(f"  {label}: {len(df)} matches")
    return df


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for code, label in SEASONS:
        print(f"Fetching {label} ...")
        df = fetch_season(code, label)
        if df is not None and not df.empty:
            frames.append(df)

    if not frames:
        print("No data fetched.")
        return

    combined = pd.concat(frames, ignore_index=True).sort_values("Date")
    combined.to_csv(OUT_CSV, index=False)
    print(f"\nSaved {len(combined)} matches to {OUT_CSV}")
    print(f"Seasons: {combined['Season'].nunique()}")
    print(f"Date range: {combined['Date'].min().date()} – {combined['Date'].max().date()}")


if __name__ == "__main__":
    main()
