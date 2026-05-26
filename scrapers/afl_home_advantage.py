"""
lib/scraper/afl_home_advantage.py

Scrapes AFL home/away win percentages from aussportstipping.com and saves
them as JSON so BetMate can badge teams with strong venue splits.

Output:
  data/afl/home-away/processed/latest-home-away.json

Usage:
  uv run --with requests --with beautifulsoup4 python lib/scraper/afl_home_advantage.py
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "afl" / "home-away" / "processed"
OUT = OUT_DIR / "latest-home-away.json"
URL = "https://www.aussportstipping.com/sports/afl/home_advantage/"
LOOKBACK_YEARS = 1

TEAM_MAP: dict[str, str] = {
    "Adelaide": "Adelaide Crows",
    "Adelaide Crows": "Adelaide Crows",
    "Brisbane": "Brisbane Lions",
    "Brisbane Lions": "Brisbane Lions",
    "Carlton": "Carlton Blues",
    "Carlton Blues": "Carlton Blues",
    "Collingwood": "Collingwood Magpies",
    "Collingwood Magpies": "Collingwood Magpies",
    "Essendon": "Essendon Bombers",
    "Essendon Bombers": "Essendon Bombers",
    "Fremantle": "Fremantle Dockers",
    "Fremantle Dockers": "Fremantle Dockers",
    "Geelong": "Geelong Cats",
    "Geelong Cats": "Geelong Cats",
    "Gold Coast": "Gold Coast Suns",
    "Gold Coast Suns": "Gold Coast Suns",
    "GWS": "Greater Western Sydney Giants",
    "GWS Giants": "Greater Western Sydney Giants",
    "Greater Western Sydney": "Greater Western Sydney Giants",
    "Greater Western Sydney Giants": "Greater Western Sydney Giants",
    "Hawthorn": "Hawthorn Hawks",
    "Hawthorn Hawks": "Hawthorn Hawks",
    "Melbourne": "Melbourne Demons",
    "Melbourne Demons": "Melbourne Demons",
    "North Melbourne": "North Melbourne Kangaroos",
    "North Melbourne Kangaroos": "North Melbourne Kangaroos",
    "Port Adelaide": "Port Adelaide Power",
    "Port Adelaide Power": "Port Adelaide Power",
    "Richmond": "Richmond Tigers",
    "Richmond Tigers": "Richmond Tigers",
    "St Kilda": "St Kilda Saints",
    "St Kilda Saints": "St Kilda Saints",
    "Sydney": "Sydney Swans",
    "Sydney Swans": "Sydney Swans",
    "West Coast": "West Coast Eagles",
    "West Coast Eagles": "West Coast Eagles",
    "Western Bulldogs": "Western Bulldogs",
    "Bulldogs": "Western Bulldogs",
    "Doggies": "Western Bulldogs",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def _parse_pct(value: str) -> float | None:
    match = re.fullmatch(r"(-?\d+(?:\.\d+)?)%", value.strip())
    if not match:
        return None
    return float(match.group(1))


def _parse_record(value: str) -> dict[str, int] | None:
    match = re.fullmatch(r"\((\d+)/(\d+)\)", value.strip())
    if not match:
        return None
    return {"wins": int(match.group(1)), "games": int(match.group(2))}


def scrape() -> list[dict]:
    log.info("Fetching AFL home advantage data from %s", URL)
    now = datetime.now(timezone.utc)
    start = now.replace(year=now.year - LOOKBACK_YEARS)
    log.info("Date range: %s to %s", start.date().isoformat(), now.date().isoformat())
    resp = requests.post(
        URL,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0"},
        data={
            "start_day": f"{start.day:02d}",
            "start_month": f"{start.month:02d}",
            "start_year": f"{start.year}",
            "end_day": f"{now.day:02d}",
            "end_month": f"{now.month:02d}",
            "end_year": f"{now.year}",
        },
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip()]
    rows = []

    for i, line in enumerate(lines):
        canonical = TEAM_MAP.get(line)
        if not canonical:
            continue

        window = lines[i + 1 : i + 8]
        percentages = [_parse_pct(item) for item in window]
        percentages = [pct for pct in percentages if pct is not None]
        records = [_parse_record(item) for item in window]
        records = [record for record in records if record is not None]

        if len(percentages) >= 3:
            rows.append(
                {
                    "name": canonical,
                    "home_win_pct": percentages[0],
                    "away_win_pct": percentages[1],
                    "difference_pct": percentages[2],
                    "home_record": records[0] if len(records) >= 1 else None,
                    "away_record": records[1] if len(records) >= 2 else None,
                }
            )

    seen: set[str] = set()
    unique = []
    for row in rows:
        if row["name"] in seen:
            continue
        seen.add(row["name"])
        unique.append(row)

    unique.sort(key=lambda row: row["difference_pct"], reverse=True)
    for rank, row in enumerate(unique, 1):
        row["rank"] = rank

    return unique


def main() -> None:
    rows = scrape()
    if len(rows) < 18:
        log.error("Only %d teams found — page structure may have changed. Aborting.", len(rows))
        sys.exit(1)

    now = datetime.now(timezone.utc)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated": now.isoformat(),
        "source": URL,
        "date_range": {
            "start": now.replace(year=now.year - LOOKBACK_YEARS).date().isoformat(),
            "end": now.date().isoformat(),
        },
        "thresholds": {
            "home_win_pct": 70,
            "away_win_pct": 65,
        },
        "teams": {
            row["name"]: {
                "rank": row["rank"],
                "home_win_pct": round(row["home_win_pct"], 2),
                "away_win_pct": round(row["away_win_pct"], 2),
                "difference_pct": round(row["difference_pct"], 2),
                "home_record": row["home_record"],
                "away_record": row["away_record"],
            }
            for row in rows
        },
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("Wrote %d teams to %s", len(rows), OUT)

    from supabase_push import push  # noqa: PLC0415
    push("afl_home_away", payload)


if __name__ == "__main__":
    main()
