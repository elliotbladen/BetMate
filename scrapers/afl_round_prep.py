"""
lib/scraper/afl_round_prep.py

Orchestrator — runs AFL round-prep scrapers in sequence:
  1. afl_injuries.py  → data/afl/injuries/processed/latest-injuries.json

Usage:
  uv run --with requests --with beautifulsoup4 python lib/scraper/afl_round_prep.py --season 2026
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT     = Path(__file__).resolve().parents[2]
LOG_DIR  = ROOT / "data" / "afl" / "logs"
LOG_PATH = LOG_DIR / "round_prep.log"

DEFAULT_ROUND_ONE_THURSDAY = "2026-03-06"

log = logging.getLogger(__name__)


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def infer_round(round_one_thursday: str) -> int:
    thursday = datetime.strptime(round_one_thursday, "%Y-%m-%d").date()
    today    = datetime.now().date()
    if today < thursday:
        return 1
    return (today - thursday).days // 7 + 1


def run_injuries(season: int, round_number: int, max_attempts: int, retry_delay: int) -> bool:
    from afl_injuries import scrape as inj_scrape, setup_logging as inj_log
    inj_log()
    log.info("=== INJURIES ===")
    count = inj_scrape(season, round_number, max_attempts, retry_delay)
    log.info("Injury scrape complete -- %d records", count)
    return True


def main() -> None:
    setup_logging()

    p = argparse.ArgumentParser(description="AFL round prep -- injuries + umpires")
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--round", dest="round_number", type=int, default=0)
    p.add_argument("--round-one-thursday", default=DEFAULT_ROUND_ONE_THURSDAY)
    p.add_argument("--max-attempts", type=int, default=3)
    p.add_argument("--retry-delay-seconds", type=int, default=30)
    p.add_argument("--skip-injuries", action="store_true")
    args = p.parse_args()

    scraper_dir = Path(__file__).parent
    if str(scraper_dir) not in sys.path:
        sys.path.insert(0, str(scraper_dir))

    round_number = args.round_number or infer_round(args.round_one_thursday)
    log.info("AFL Round Prep -- season=%d round=%d -- %s UTC",
             args.season, round_number,
             datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))

    results: dict[str, bool] = {}

    if not args.skip_injuries:
        results["injuries"] = run_injuries(args.season, round_number, args.max_attempts, args.retry_delay_seconds)

    log.info("=== SUMMARY ===")
    for name, ok in results.items():
        log.info("  %-12s %s", name, "OK" if ok else "WARN")

    log.info("AFL round prep complete -- R%d", round_number)
    sys.exit(0)


if __name__ == "__main__":
    main()
