"""
InPlayEngine/data/processors/extract_halftime.py

Reads raw Betfair Match Odds CSVs and extracts the halftime price for each game.
Output: data/inplay/{sport}/halftime/extracted/halftime_prices_{year}.csv

Usage:
    uv run python InPlayEngine/data/processors/extract_halftime.py --sport nrl --year 2022
    uv run python InPlayEngine/data/processors/extract_halftime.py --sport nrl --all-years
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "InPlayEngine"))

from inplay_engine.core.exchange import load_match_odds_csv, split_markets
from inplay_engine.core.halftime import extract_halftime

DATA_ROOT = REPO_ROOT / "data" / "inplay"


def process_year(sport: str, year: int, halftime_seconds: int, window_seconds: int) -> pd.DataFrame:
    raw_dir = DATA_ROOT / sport / "betfair" / "raw" / str(year)
    csv_files = list(raw_dir.glob("*.csv"))

    if not csv_files:
        print(f"  [warn] No CSVs found in {raw_dir}")
        return pd.DataFrame()

    rows = []
    for csv_path in csv_files:
        print(f"  Processing {csv_path.name} ...")
        try:
            df = load_match_odds_csv(csv_path)
        except Exception as e:
            print(f"    [err] Load failed: {e}")
            continue

        markets = split_markets(df)
        print(f"    {len(markets)} markets found")

        for market_id, market_df in markets.items():
            ht = extract_halftime(market_df, halftime_seconds, window_seconds)

            if not ht.found:
                continue

            # Each market has 2 selections (home + away)
            selections = list(ht.prices.keys())
            if len(selections) < 2:
                continue

            row = {
                "year": year,
                "market_id": market_id,
                "kickoff_utc": ht.kickoff,
                "halftime_utc": ht.halftime_ts,
            }
            # Store as selection_1 / selection_2 — ordering reflects Betfair alphabetical
            for i, sel in enumerate(selections, 1):
                row[f"selection_{i}"] = sel
                row[f"price_{i}"] = ht.prices[sel]

            rows.append(row)

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract halftime prices from Betfair CSVs")
    parser.add_argument("--sport", required=True, choices=["nrl", "afl"])
    parser.add_argument("--year", type=int)
    parser.add_argument("--all-years", action="store_true")
    args = parser.parse_args()

    if args.sport == "nrl":
        from inplay_engine.sports.nrl.config import NRL as cfg
    else:
        from inplay_engine.sports.afl.config import AFL as cfg

    years = list(cfg.available_years) if args.all_years else [args.year]
    if not years:
        print("Specify --year or --all-years")
        return

    out_dir = DATA_ROOT / args.sport / "halftime" / "extracted"
    out_dir.mkdir(parents=True, exist_ok=True)

    for year in years:
        if year < 2022:
            print(f"Skipping {year} (pre-2022)")
            continue
        print(f"\n--- {args.sport.upper()} {year} ---")
        result = process_year(args.sport, year, cfg.halftime_seconds, cfg.halftime_window_seconds)
        if result.empty:
            print("  No data extracted.")
            continue
        out_path = out_dir / f"halftime_prices_{year}.csv"
        result.to_csv(out_path, index=False)
        print(f"  Saved {len(result)} records → {out_path}")


if __name__ == "__main__":
    main()
