#!/usr/bin/env python3
"""Fetch preseason English ClubElo ratings used by Championship T8."""
from __future__ import annotations

import argparse
import io
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from ml.football.league_config import load_league


def fetch_season(season: str, retries: int = 3) -> pd.DataFrame:
    """Preseason (1 August) English ratings for `season`.

    The date matters. T8 is a PRESEASON prior that decays to zero by game 15, so
    it must be the 1 August snapshot — substituting a mid-season rating would feed
    current form into a term the model treats as a prior, and double-count it
    against the D-C fit. Every row therefore records the date it is really for.

    api.clubelo.com was returning 502 on 2026-09-14 while clubelo.com itself was
    up. The website only publishes CURRENT ratings, not a dated history, so there
    is no safe fallback — this raises rather than quietly writing the wrong date.
    """
    date = f"{season.split('/')[0]}-08-01"
    last: Exception | None = None
    for attempt in range(retries):
        try:
            response = requests.get(f"https://api.clubelo.com/{date}", timeout=30,
                                    headers={"User-Agent": "BetMate research model"})
            response.raise_for_status()
            break
        except Exception as exc:                                  # noqa: BLE001
            last = exc
            if attempt == retries - 1:
                raise RuntimeError(
                    f"ClubElo unavailable for {date} after {retries} attempts ({last}). "
                    "T8 will keep using the hardcoded new_team_elo_priors fallback. "
                    "Do NOT substitute a current rating from clubelo.com — it is not "
                    "the same quantity as a 1 August prior."
                ) from exc
            time.sleep(2 ** attempt)
    raw = pd.read_csv(io.StringIO(response.text))
    raw.columns = [str(c).strip() for c in raw.columns]
    english = raw[raw["Country"].astype(str).str.strip().eq("ENG")].copy()
    english["Level"] = pd.to_numeric(english["Level"], errors="coerce")
    english = english[english["Level"].isin([1, 2, 3])]
    return pd.DataFrame({"season": season, "club": english["Club"].str.strip(),
                         "elo": pd.to_numeric(english["Elo"], errors="coerce"),
                         "level": english["Level"].astype(int),
                         "as_of_date": date,
                         "fetched_at": datetime.now(timezone.utc).date().isoformat()})


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
