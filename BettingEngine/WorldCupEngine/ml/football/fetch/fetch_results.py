"""
Fetch match results + bookmaker odds from football-data.co.uk — league-parameterised.

Usage:
    python ml/football/fetch/fetch_results.py                      # EPL (E0)
    python ml/football/fetch/fetch_results.py --league championship  # E1

League code, seasons range, and output file come from ml/football/leagues/{key}.yaml
(`source:` block). Output lands in ml/football/data/{key}/matches/.

Columns retained include Pinnacle OPENING (PSH/PSD/PSA, P>2.5) and CLOSING
(PSCH/PSCD/PSCA, PC>2.5) odds where present (2019/20 onward) — these feed the
CLV backtest. Absent columns in older seasons are skipped gracefully.
"""

from __future__ import annotations

import argparse
import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_ROOT))

from ml.football.league_config import load_league

# football-data.co.uk URL pattern
BASE_URL = "https://www.football-data.co.uk/mmz4281/{code}/{league_code}.csv"

# Fallback: Internet Archive snapshot of the same file ("2026id_" = latest snapshot
# at/before 2026, raw bytes). Needed on networks that category-block betting sites
# (e.g. the work FortiGate, discovered 2026-07-10). Completed seasons are static so
# an archived copy is identical to the live file; verify row counts after fetching.
WAYBACK_URL = "https://web.archive.org/web/2026id_/{url}"

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
    # Pinnacle opening + closing (for CLV backtests; present from ~2019/20)
    "PSH", "PSD", "PSA",
    "PSCH", "PSCD", "PSCA",
    "P>2.5", "P<2.5",
    "PC>2.5", "PC<2.5",
    "AHCh", "PAHH", "PAHA", "PCAHH", "PCAHA",
]

DATE_FMTS = ["%d/%m/%Y", "%d/%m/%y"]


def _season_codes(seasons_from: str, seasons_to: str) -> list[tuple[str, str]]:
    """'2014/15'..'2025/26' → [('1415','2014/15'), ..., ('2526','2025/26')]"""
    start = int(seasons_from.split("/")[0])
    end   = int(seasons_to.split("/")[0])
    out = []
    for y in range(start, end + 1):
        label = f"{y}/{str(y + 1)[-2:]}"
        code  = f"{str(y)[-2:]}{str(y + 1)[-2:]}"
        out.append((code, label))
    return out


def _parse_date(s: str) -> pd.Timestamp | None:
    for fmt in DATE_FMTS:
        try:
            return pd.to_datetime(s, format=fmt)
        except Exception:
            pass
    return pd.NaT


def _get(url: str, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    # football-data files are latin-1; some carry a UTF-8 BOM
    text = raw.decode("latin-1")
    return text.lstrip("﻿").lstrip("ï»¿")


def fetch_season(code: str, label: str, league_code: str) -> pd.DataFrame | None:
    url = BASE_URL.format(code=code, league_code=league_code)
    text = None
    try:
        text = _get(url)
    except Exception as e:
        print(f"  direct fetch failed ({e.__class__.__name__}) — trying Internet Archive ...")
        try:
            text = _get(WAYBACK_URL.format(url=url), timeout=90)
        except Exception as e2:
            print(f"  ERROR {label}: {e2}")
            return None

    df = pd.read_csv(io.StringIO(text), encoding="latin-1", on_bad_lines="skip")
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
    parser = argparse.ArgumentParser(description="Fetch football-data.co.uk results")
    parser.add_argument("--league", default="epl", help="League config key (leagues/*.yaml)")
    args = parser.parse_args()

    cfg = load_league(args.league)
    src = cfg.raw["source"]
    league_code = src["league_code"]
    seasons = _season_codes(src["seasons_from"], src.get("seasons_to", "2025/26"))

    out_csv = cfg.matches_csv
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    frames = []
    for code, label in seasons:
        print(f"Fetching {label} ({league_code}) ...")
        df = fetch_season(code, label, league_code)
        if df is not None and not df.empty:
            frames.append(df)

    if not frames:
        print("No data fetched.")
        return

    combined = pd.concat(frames, ignore_index=True).sort_values("Date")
    combined.to_csv(out_csv, index=False)
    print(f"\nSaved {len(combined)} matches to {out_csv}")
    print(f"Seasons: {combined['Season'].nunique()}")
    print(f"Date range: {combined['Date'].min().date()} – {combined['Date'].max().date()}")


if __name__ == "__main__":
    main()
