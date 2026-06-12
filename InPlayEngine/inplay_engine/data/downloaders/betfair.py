"""
InPlayEngine/data/downloaders/betfair.py

Downloads Betfair Datascientists Match Odds CSVs for a given sport and year range.
Files land in: data/inplay/{sport}/betfair/raw/{year}/

Usage:
    uv run --with requests python InPlayEngine/data/downloaders/betfair.py --sport nrl --from-year 2022
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

# Root of the Apps repo — two levels up from this file
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = REPO_ROOT / "data" / "inplay"

CHUNK_SIZE = 1024 * 1024  # 1 MB


def download_file(url: str, dest: Path, force: bool = False) -> bool:
    if dest.exists() and not force:
        print(f"  [skip] {dest.name} already exists")
        return False

    print(f"  Downloading {url} ...")
    try:
        r = requests.get(url, stream=True, timeout=120)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
        size_mb = dest.stat().st_size / 1_048_576
        print(f"  [ok]   {dest.name} ({size_mb:.1f} MB)")
        return True
    except requests.HTTPError as e:
        print(f"  [err]  HTTP {e.response.status_code} — {url}")
        return False
    except Exception as e:
        print(f"  [err]  {e}")
        return False


def get_sport_config(sport: str):
    """Import and return the config for the given sport."""
    if sport == "nrl":
        from inplay_engine.sports.nrl.config import NRL
        return NRL
    if sport == "afl":
        from inplay_engine.sports.afl.config import AFL
        return AFL
    raise ValueError(f"Unknown sport: {sport}. Add a config to InPlayEngine/sports/{sport}/config.py")


def download_betfair(sport: str, from_year: int, to_year: int, force: bool = False) -> None:
    try:
        cfg = get_sport_config(sport)
    except ImportError:
        # Fallback: construct URL from pattern without importing config
        base = "https://betfair-datascientists.github.io/assets"
        years = range(from_year, to_year + 1)
        urls = {y: f"{base}/{sport.upper()}_{y}_Match_Odds.csv" for y in years}
    else:
        years = [y for y in cfg.available_years if from_year <= y <= to_year]
        urls = {y: cfg.betfair_url(y) for y in years}

    if not urls:
        print(f"No years available for {sport} between {from_year}–{to_year}")
        return

    raw_root = DATA_ROOT / sport / "betfair" / "raw"
    downloaded = 0

    print(f"\nDownloading Betfair {sport.upper()} Match Odds CSVs ({from_year}–{to_year})")
    print(f"Destination: {raw_root}\n")

    for year, url in sorted(urls.items()):
        year_dir = raw_root / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)
        filename = url.split("/")[-1]
        dest = year_dir / filename
        if download_file(url, dest, force=force):
            downloaded += 1

    print(f"\nDone. {downloaded} file(s) downloaded.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Betfair historical Match Odds CSVs")
    parser.add_argument("--sport", required=True, choices=["nrl", "afl", "epl"], help="Sport code")
    parser.add_argument("--from-year", type=int, default=2022, help="Start year (default: 2022)")
    parser.add_argument("--to-year", type=int, default=2026, help="End year (default: 2026)")
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    args = parser.parse_args()

    download_betfair(args.sport, args.from_year, args.to_year, args.force)


if __name__ == "__main__":
    # Allow running without the package installed
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    try:
        import inplay_engine  # noqa: F401
    except ImportError:
        pass
    main()
