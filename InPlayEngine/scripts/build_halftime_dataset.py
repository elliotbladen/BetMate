"""
Entry point: extract halftime prices from all raw Betfair CSVs and build
the model-ready dataset at data/inplay/{sport}/halftime/processed/halftime_dataset.csv

Run this after downloading Betfair CSVs.

Usage:
    uv run python InPlayEngine/scripts/build_halftime_dataset.py --sport nrl
"""
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "InPlayEngine"))

from inplay_engine.data.processors.extract_halftime import process_year

DATA_ROOT = REPO_ROOT / "data" / "inplay"
YEARS = [2022, 2023, 2024, 2025, 2026]


def main(sport: str) -> None:
    if sport == "nrl":
        from inplay_engine.sports.nrl.config import NRL as cfg
        from inplay_engine.sports.nrl.features import build_features
    else:
        from inplay_engine.sports.afl.config import AFL as cfg
        build_features = None  # AFL features TBD

    all_rows = []
    for year in YEARS:
        print(f"\n=== {sport.upper()} {year} ===")
        df = process_year(sport, year, cfg.halftime_seconds, cfg.halftime_window_seconds)
        if not df.empty:
            df["year"] = year
            all_rows.append(df)

    if not all_rows:
        print("No data found. Run download_betfair_nrl.py first.")
        return

    combined = pd.concat(all_rows, ignore_index=True)

    if build_features is not None:
        combined = build_features(combined)

    out_dir = DATA_ROOT / sport / "halftime" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "halftime_dataset.csv"
    combined.to_csv(out_path, index=False)

    print(f"\nDataset: {len(combined)} games → {out_path}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--sport", default="nrl", choices=["nrl", "afl"])
    args = p.parse_args()
    main(args.sport)
