#!/usr/bin/env python3
"""Fetch preseason English ClubElo ratings used by Championship T8."""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from ml.football.league_config import load_league


def fetch_season(season: str) -> pd.DataFrame:
    date = f"{season.split('/')[0]}-08-01"
    response = requests.get(f"https://api.clubelo.com/{date}", timeout=30,
                            headers={"User-Agent": "BetMate research model"})
    response.raise_for_status()
    raw = pd.read_csv(io.StringIO(response.text))
    raw.columns = [str(c).strip() for c in raw.columns]
    english = raw[raw["Country"].astype(str).str.strip().eq("ENG")].copy()
    english["Level"] = pd.to_numeric(english["Level"], errors="coerce")
    english = english[english["Level"].isin([1, 2, 3])]
    return pd.DataFrame({"season": season, "club": english["Club"].str.strip(),
                         "elo": pd.to_numeric(english["Elo"], errors="coerce"),
                         "level": english["Level"].astype(int)})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", nargs="+", default=["2026/27"])
    args = ap.parse_args()
    cfg = load_league("championship")
    old = pd.read_csv(cfg.clubelo_csv) if cfg.clubelo_csv and cfg.clubelo_csv.exists() else pd.DataFrame()
    fresh = pd.concat([fetch_season(s) for s in args.seasons], ignore_index=True)
    combined = pd.concat([old[~old["season"].isin(args.seasons)], fresh], ignore_index=True) if not old.empty else fresh
    cfg.clubelo_csv.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(cfg.clubelo_csv, index=False)
    print(f"Saved {len(fresh)} current rows to {cfg.clubelo_csv}")


if __name__ == "__main__":
    main()
