"""
Entry point: download NRL Betfair Match Odds CSVs for 2022–2026.

Usage:
    uv run --with requests python InPlayEngine/scripts/download_betfair_nrl.py
    uv run --with requests python InPlayEngine/scripts/download_betfair_nrl.py --force
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inplay_engine.data.downloaders.betfair import download_betfair

if __name__ == "__main__":
    force = "--force" in sys.argv
    download_betfair("nrl", from_year=2022, to_year=2026, force=force)
