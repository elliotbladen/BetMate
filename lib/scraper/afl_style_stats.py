"""
lib/scraper/afl_style_stats.py

Scrapes AFL team style stats from afltables.com and saves as CSV.

Source: https://afltables.com/afl/stats/YYYYt.html

Outputs:
  data/afl/style-stats/raw/YYYY/round-N.json
  data/afl/style-stats/processed/YYYY/round-N-style-stats.csv
  data/afl/style-stats/processed/latest-style-stats.csv
  data/afl/style-stats/logs/scrape.log

Usage:
  uv run --with requests --with beautifulsoup4 python lib/scraper/afl_style_stats.py --season 2026
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT          = Path(__file__).resolve().parents[2]
BASE_DIR      = ROOT / "data" / "afl" / "style-stats"
RAW_DIR       = BASE_DIR / "raw"
PROCESSED_DIR = BASE_DIR / "processed"
LOG_DIR       = BASE_DIR / "logs"
LOG_PATH      = LOG_DIR / "scrape.log"

DEFAULT_TIMEOUT      = 30
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RETRY_DELAY  = 30
DEFAULT_ROUND_ONE_THURSDAY = "2026-03-06"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}

TEAM_MAP = {
    "Adelaide":              "Adelaide Crows",
    "Brisbane Lions":        "Brisbane Lions",
    "Carlton":               "Carlton Blues",
    "Collingwood":           "Collingwood Magpies",
    "Essendon":              "Essendon Bombers",
    "Fremantle":             "Fremantle Dockers",
    "Geelong":               "Geelong Cats",
    "Gold Coast":            "Gold Coast Suns",
    "Greater Western Sydney":"Greater Western Sydney Giants",
    "Hawthorn":              "Hawthorn Hawks",
    "Melbourne":             "Melbourne Demons",
    "North Melbourne":       "North Melbourne Kangaroos",
    "Port Adelaide":         "Port Adelaide Power",
    "Richmond":              "Richmond Tigers",
    "St Kilda":              "St Kilda Saints",
    "Sydney":                "Sydney Swans",
    "West Coast":            "West Coast Eagles",
    "Western Bulldogs":      "Western Bulldogs",
}

STAT_COLS = {
    "FF": "free_kicks_for_pg",
    "FA": "free_kicks_against_pg",
    "CP": "contested_possessions_pg",
    "UP": "uncontested_possessions_pg",
    "CM": "contested_marks_pg",
    "MI": "marks_inside_50_pg",
    "1%": "one_percenters_pg",
    "GA": "goal_assists_pg",
}

FIELDNAMES = [
    "team", "season", "round", "as_of_date", "games_played",
    "free_kicks_for_pg", "free_kicks_against_pg",
    "contested_possessions_pg", "uncontested_possessions_pg",
    "contested_marks_pg", "marks_inside_50_pg",
    "one_percenters_pg", "goal_assists_pg",
    "source_url", "scraped_at",
]

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


def fetch_html(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        log.warning("Fetch failed %s -- %s", url, exc)
        return None


def extract_team_name(table) -> str | None:
    header = table.find("tr")
    if not header:
        return None
    text = header.get_text(strip=True)
    # "Adelaide Team Statistics [Players]" -> "Adelaide"
    m = re.match(r"^(.+?)\s+Team Statistics", text)
    if not m:
        return None
    raw = m.group(1).strip()
    return TEAM_MAP.get(raw)


def parse_for_value(cell_text: str) -> float | None:
    # Stats are "for-against" pairs e.g. "139-115" — take the first number
    parts = cell_text.split("-")
    try:
        return float(parts[0])
    except (ValueError, IndexError):
        return None


def parse_team_table(table) -> tuple[str | None, dict]:
    team = extract_team_name(table)
    if not team:
        return None, {}

    rows = table.find_all("tr")
    if len(rows) < 3:
        return team, {}

    # Row 1: column headers
    col_headers = [td.get_text(strip=True) for td in rows[1].find_all(["th", "td"])]
    col_indices = {
        STAT_COLS[h]: i
        for i, h in enumerate(col_headers)
        if h in STAT_COLS
    }

    if not col_indices:
        return team, {}

    totals: dict[str, float] = {f: 0.0 for f in col_indices}
    games = 0

    # Each data row: starts with round label e.g. "R2"
    for row in rows[2:]:
        cells = [td.get_text(strip=True) for td in row.find_all(["th", "td"])]
        if not cells:
            continue
        # Skip W-D-L summary row
        if not re.match(r"^R\d+$", cells[0]):
            continue
        games += 1
        for field, idx in col_indices.items():
            if idx < len(cells):
                val = parse_for_value(cells[idx])
                if val is not None:
                    totals[field] += val

    if games == 0:
        return team, {}

    avgs = {field: round(total / games, 2) for field, total in totals.items()}
    avgs["games_played"] = games
    return team, avgs


def parse_all_teams(html: str, season: int, round_number: int, source_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    scraped_at = datetime.now(timezone.utc).isoformat()
    as_of_date = datetime.now().date().isoformat()

    records = []
    seen_teams: set[str] = set()

    for table in tables:
        team, avgs = parse_team_table(table)
        if not team or team in seen_teams or not avgs:
            continue
        seen_teams.add(team)

        row: dict = {f: None for f in FIELDNAMES}
        row.update({
            "team":       team,
            "season":     season,
            "round":      round_number,
            "as_of_date": as_of_date,
            "source_url": source_url,
            "scraped_at": scraped_at,
        })
        row.update(avgs)
        records.append(row)
        log.debug("  %-35s %d games", team, avgs.get("games_played", 0))

    log.info("Parsed %d teams", len(records))
    return records


def write_outputs(records: list[dict], raw_html: str, season: int, round_number: int, source_url: str) -> None:
    scraped_at = datetime.now(timezone.utc).isoformat()

    raw_dir = RAW_DIR / str(season)
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"round-{round_number}.json").write_text(
        json.dumps({"scraped_at": scraped_at, "source": source_url, "raw_length": len(raw_html)}, indent=2),
        encoding="utf-8",
    )

    proc_dir = PROCESSED_DIR / str(season)
    proc_dir.mkdir(parents=True, exist_ok=True)

    for path in (proc_dir / f"round-{round_number}-style-stats.csv", PROCESSED_DIR / "latest-style-stats.csv"):
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(records)

    log.info("Wrote latest-style-stats.csv -- %d teams, round %d", len(records), round_number)


def scrape(season: int, round_number: int, max_attempts: int, retry_delay: int) -> int:
    url = f"https://afltables.com/afl/stats/{season}t.html"
    for attempt in range(1, max_attempts + 1):
        log.info("Attempt %d/%d -- AFL style stats R%d %d", attempt, max_attempts, round_number, season)
        html = fetch_html(url)
        if html:
            records = parse_all_teams(html, season, round_number, url)
            if records:
                write_outputs(records, html, season, round_number, url)
                return len(records)
            log.warning("No team records parsed -- page structure may have changed")
        if attempt < max_attempts:
            log.warning("Retrying in %ds", retry_delay)
            time.sleep(retry_delay)
    log.error("All attempts exhausted")
    return 0


def main() -> None:
    setup_logging()
    p = argparse.ArgumentParser(description="Scrape AFL team style stats from afltables.com")
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--round", dest="round_number", type=int, default=0)
    p.add_argument("--round-one-thursday", default=DEFAULT_ROUND_ONE_THURSDAY)
    p.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    p.add_argument("--retry-delay-seconds", type=int, default=DEFAULT_RETRY_DELAY)
    args = p.parse_args()

    round_number = args.round_number or infer_round(args.round_one_thursday)
    log.info("Targeting season=%d round=%d", args.season, round_number)
    count = scrape(args.season, round_number, args.max_attempts, args.retry_delay_seconds)
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
