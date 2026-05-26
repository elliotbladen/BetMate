"""
lib/scraper/nrl_home_advantage.py

Scrapes NRL home/away win percentages from aussportstipping.com and saves
them as JSON so BetMate can badge teams with strong venue splits.

Output:
  data/nrl/home-away/processed/latest-home-away.json

Usage:
  uv run --with requests --with beautifulsoup4 python lib/scraper/nrl_home_advantage.py
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
OUT_DIR = ROOT / "data" / "nrl" / "home-away" / "processed"
OUT = OUT_DIR / "latest-home-away.json"
URL = "https://www.aussportstipping.com/sports/nrl/home_advantage/"
LOOKBACK_YEARS = 1

# Canonical names must match keys in lib/teams.ts NRL_TEAMS exactly
TEAM_MAP: dict[str, str] = {
    "Broncos":                      "Brisbane Broncos",
    "Brisbane Broncos":             "Brisbane Broncos",
    "Brisbane":                     "Brisbane Broncos",
    "Raiders":                      "Canberra Raiders",
    "Canberra Raiders":             "Canberra Raiders",
    "Canberra":                     "Canberra Raiders",
    "Bulldogs":                     "Canterbury Bulldogs",
    "Canterbury Bulldogs":          "Canterbury Bulldogs",
    "Canterbury-Bankstown Bulldogs":"Canterbury Bulldogs",
    "Canterbury":                   "Canterbury Bulldogs",
    "Sharks":                       "Cronulla Sutherland Sharks",
    "Cronulla Sutherland Sharks":   "Cronulla Sutherland Sharks",
    "Cronulla-Sutherland Sharks":   "Cronulla Sutherland Sharks",
    "Cronulla":                     "Cronulla Sutherland Sharks",
    "Dolphins":                     "Dolphins",
    "Titans":                       "Gold Coast Titans",
    "Gold Coast Titans":            "Gold Coast Titans",
    "Gold Coast":                   "Gold Coast Titans",
    "Sea Eagles":                   "Manly Warringah Sea Eagles",
    "Manly Warringah Sea Eagles":   "Manly Warringah Sea Eagles",
    "Manly-Warringah Sea Eagles":   "Manly Warringah Sea Eagles",
    "Manly":                        "Manly Warringah Sea Eagles",
    "Storm":                        "Melbourne Storm",
    "Melbourne Storm":              "Melbourne Storm",
    "Melbourne":                    "Melbourne Storm",
    "Warriors":                     "New Zealand Warriors",
    "New Zealand Warriors":         "New Zealand Warriors",
    "NZ Warriors":                  "New Zealand Warriors",
    "Knights":                      "Newcastle Knights",
    "Newcastle Knights":            "Newcastle Knights",
    "Newcastle":                    "Newcastle Knights",
    "Cowboys":                      "North Queensland Cowboys",
    "North Queensland Cowboys":     "North Queensland Cowboys",
    "North Queensland":             "North Queensland Cowboys",
    "Eels":                         "Parramatta Eels",
    "Parramatta Eels":              "Parramatta Eels",
    "Parramatta":                   "Parramatta Eels",
    "Panthers":                     "Penrith Panthers",
    "Penrith Panthers":             "Penrith Panthers",
    "Penrith":                      "Penrith Panthers",
    "Rabbitohs":                    "South Sydney Rabbitohs",
    "South Sydney Rabbitohs":       "South Sydney Rabbitohs",
    "South Sydney":                 "South Sydney Rabbitohs",
    "Dragons":                      "St George Illawarra Dragons",
    "St George Illawarra Dragons":  "St George Illawarra Dragons",
    "St. George Illawarra Dragons": "St George Illawarra Dragons",
    "St George Illawarra":          "St George Illawarra Dragons",
    "Roosters":                     "Sydney Roosters",
    "Sydney Roosters":              "Sydney Roosters",
    "Sydney":                       "Sydney Roosters",
    "Tigers":                       "Wests Tigers",
    "Wests Tigers":                 "Wests Tigers",
    "Wests":                        "Wests Tigers",
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
    log.info("Fetching NRL home advantage data from %s", URL)
    now = datetime.now(timezone.utc)
    start = now.replace(year=now.year - LOOKBACK_YEARS)
    log.info("Date range: %s to %s", start.date().isoformat(), now.date().isoformat())
    resp = requests.post(
        URL,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0"},
        data={
            "start_day":   f"{start.day:02d}",
            "start_month": f"{start.month:02d}",
            "start_year":  f"{start.year}",
            "end_day":     f"{now.day:02d}",
            "end_month":   f"{now.month:02d}",
            "end_year":    f"{now.year}",
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
                    "name":           canonical,
                    "home_win_pct":   percentages[0],
                    "away_win_pct":   percentages[1],
                    "difference_pct": percentages[2],
                    "home_record":    records[0] if len(records) >= 1 else None,
                    "away_record":    records[1] if len(records) >= 2 else None,
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
    if len(rows) < 6:
        log.error("Only %d teams found — page structure may have changed. Aborting.", len(rows))
        sys.exit(1)

    now = datetime.now(timezone.utc)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated": now.isoformat(),
        "source":  URL,
        "date_range": {
            "start": now.replace(year=now.year - LOOKBACK_YEARS).date().isoformat(),
            "end":   now.date().isoformat(),
        },
        "thresholds": {
            "home_win_pct": 70,
            "away_win_pct": 65,
        },
        "teams": {
            row["name"]: {
                "rank":           row["rank"],
                "home_win_pct":   round(row["home_win_pct"], 2),
                "away_win_pct":   round(row["away_win_pct"], 2),
                "difference_pct": round(row["difference_pct"], 2),
                "home_record":    row["home_record"],
                "away_record":    row["away_record"],
            }
            for row in rows
        },
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("Wrote %d teams to %s", len(rows), OUT)

    from supabase_push import push  # noqa: PLC0415
    push("nrl_home_away", payload)


if __name__ == "__main__":
    main()
