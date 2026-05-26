"""
lib/scraper/afl_injuries.py

Scrapes the AFL injury list from footywire.com.

Source: https://www.footywire.com/afl/footy/injury_list

Outputs:
  data/afl/injuries/raw/YYYY/round-N.json
  data/afl/injuries/processed/YYYY/round-N-injuries.json
  data/afl/injuries/processed/latest-injuries.json
  data/afl/injuries/logs/scrape.log

Usage:
  uv run --with requests --with beautifulsoup4 python lib/scraper/afl_injuries.py --season 2026
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT          = Path(__file__).resolve().parents[1]
BASE_DIR      = ROOT / "data" / "afl" / "injuries"
RAW_DIR       = BASE_DIR / "raw"
PROCESSED_DIR = BASE_DIR / "processed"
LOG_DIR       = BASE_DIR / "logs"
LOG_PATH      = LOG_DIR / "scrape.log"

URL = "https://www.footywire.com/afl/footy/injury_list"

DEFAULT_TIMEOUT      = 30
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RETRY_DELAY  = 30
DEFAULT_ROUND_ONE_THURSDAY = "2026-03-06"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}

TEAM_MAP = {
    "Adelaide Crows":            "Adelaide Crows",
    "Brisbane Lions":            "Brisbane Lions",
    "Carlton Blues":             "Carlton Blues",
    "Collingwood Magpies":       "Collingwood Magpies",
    "Essendon Bombers":          "Essendon Bombers",
    "Fremantle Dockers":         "Fremantle Dockers",
    "Geelong Cats":              "Geelong Cats",
    "Gold Coast Suns":           "Gold Coast Suns",
    "GWS Giants":                "Greater Western Sydney Giants",
    "Hawthorn Hawks":            "Hawthorn Hawks",
    "Melbourne Demons":          "Melbourne Demons",
    "North Melbourne Kangaroos": "North Melbourne Kangaroos",
    "Port Adelaide Power":       "Port Adelaide Power",
    "Richmond Tigers":           "Richmond Tigers",
    "St Kilda Saints":           "St Kilda Saints",
    "Sydney Swans":              "Sydney Swans",
    "West Coast Eagles":         "West Coast Eagles",
    "Western Bulldogs":          "Western Bulldogs",
}

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
    today = datetime.now().date()
    if today < thursday:
        return 1
    return (today - thursday).days // 7 + 1


def canon_team(raw: str) -> str | None:
    name = re.sub(r"\s*\(\d+ Players?\)\s*", "", raw).strip()
    return TEAM_MAP.get(name)


def parse_return_status(returning: str) -> str:
    r = returning.strip().lower()
    if not r or r in ("tbc", "indefinite", "season"):
        return "out"
    if "concussion" in r or r == "test":
        return "doubtful"
    if "individual" in r or "program" in r:
        return "out"
    m = re.match(r"(\d+)", r)
    if m:
        return "doubtful" if int(m.group(1)) <= 1 else "out"
    return "out"


def fetch_html(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        log.warning("Fetch failed %s -- %s", url, exc)
        return None


def parse_injuries(html: str, season: int, round_number: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    records = []
    scraped_at = datetime.now(timezone.utc).isoformat()

    # Tables come in pairs from index 6: (team header, player data)
    i = 6
    while i < len(tables) - 1:
        team_table = tables[i]
        player_table = tables[i + 1]

        first_cell = team_table.find("td") or team_table.find("th")
        if not first_cell:
            i += 2
            continue

        team = canon_team(first_cell.get_text(strip=True))
        if not team:
            break  # past the injury section

        rows = player_table.find_all("tr")
        for row in rows[1:]:  # skip header
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            player    = cells[0].get_text(strip=True)
            injury    = cells[1].get_text(strip=True)
            returning = cells[2].get_text(strip=True)
            if not player:
                continue

            status = parse_return_status(returning)
            records.append({
                "season":     season,
                "round":      round_number,
                "team":       team,
                "player":     player,
                "status":     status,
                "notes":      f"{injury} | Return: {returning}",
                "scraped_at": scraped_at,
            })
            log.debug("  %-35s %-28s [%s] %s", team, player, status, injury)

        i += 2

    log.info("Parsed %d player records across all teams", len(records))
    return records


def write_outputs(records: list[dict], raw_html: str, season: int, round_number: int) -> None:
    scraped_at = datetime.now(timezone.utc).isoformat()

    raw_dir = RAW_DIR / str(season)
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"round-{round_number}.json").write_text(
        json.dumps({"scraped_at": scraped_at, "source": URL, "raw_length": len(raw_html)}, indent=2),
        encoding="utf-8",
    )

    proc_dir = PROCESSED_DIR / str(season)
    proc_dir.mkdir(parents=True, exist_ok=True)
    (proc_dir / f"round-{round_number}-injuries.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    (PROCESSED_DIR / "latest-injuries.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Wrote latest-injuries.json -- %d records, round %d", len(records), round_number)


def scrape(season: int, round_number: int, max_attempts: int, retry_delay: int) -> int:
    for attempt in range(1, max_attempts + 1):
        log.info("Attempt %d/%d -- AFL injuries R%d %d", attempt, max_attempts, round_number, season)
        html = fetch_html(URL)
        if html:
            records = parse_injuries(html, season, round_number)
            write_outputs(records, html, season, round_number)
            return len(records)
        if attempt < max_attempts:
            log.warning("Fetch failed, retrying in %ds", retry_delay)
            time.sleep(retry_delay)
    log.error("All attempts exhausted -- no AFL injury data")
    return 0


def main() -> None:
    setup_logging()
    p = argparse.ArgumentParser(description="Scrape AFL injuries from footywire.com")
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--round", dest="round_number", type=int, default=0)
    p.add_argument("--round-one-thursday", default=DEFAULT_ROUND_ONE_THURSDAY)
    p.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    p.add_argument("--retry-delay-seconds", type=int, default=DEFAULT_RETRY_DELAY)
    args = p.parse_args()

    round_number = args.round_number or infer_round(args.round_one_thursday)
    log.info("Targeting season=%d round=%d", args.season, round_number)
    count = scrape(args.season, round_number, args.max_attempts, args.retry_delay_seconds)
    sys.exit(0 if count >= 0 else 1)


if __name__ == "__main__":
    main()
