#!/usr/bin/env python3
"""
scrape_ladder.py — Scrape current AFL + NRL ladder positions.

AFL: afltables.com/afl/seas/2026.html
NRL: nrl.com/draw/premiership

Outputs JSON to data/line_movement/{sport}_ladder.json

Usage:
    python scripts/line_mover/scrape_ladder.py --sport AFL
    python scripts/line_mover/scrape_ladder.py --sport NRL
    python scripts/line_mover/scrape_ladder.py --sport ALL
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "line_movement"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# AFL team name mapping (afltables short → full Odds API name)
AFL_NAME_MAP = {
    "Adelaide": "Adelaide Crows",
    "Brisbane Lions": "Brisbane Lions",
    "Carlton": "Carlton Blues",
    "Collingwood": "Collingwood Magpies",
    "Essendon": "Essendon Bombers",
    "Fremantle": "Fremantle Dockers",
    "Geelong": "Geelong Cats",
    "Gold Coast": "Gold Coast Suns",
    "Greater Western Sydney": "Greater Western Sydney Giants",
    "GWS Giants": "Greater Western Sydney Giants",
    "GWS": "Greater Western Sydney Giants",
    "Hawthorn": "Hawthorn Hawks",
    "Melbourne": "Melbourne Demons",
    "North Melbourne": "North Melbourne Kangaroos",
    "Port Adelaide": "Port Adelaide Power",
    "Richmond": "Richmond Tigers",
    "St Kilda": "St Kilda Saints",
    "Sydney": "Sydney Swans",
    "West Coast": "West Coast Eagles",
    "Western Bulldogs": "Western Bulldogs",
}

NRL_NAME_MAP = {
    "Broncos": "Brisbane Broncos",
    "Raiders": "Canberra Raiders",
    "Bulldogs": "Canterbury-Bankstown Bulldogs",
    "Sharks": "Cronulla-Sutherland Sharks",
    "Dolphins": "Dolphins",
    "Titans": "Gold Coast Titans",
    "Sea Eagles": "Manly-Warringah Sea Eagles",
    "Storm": "Melbourne Storm",
    "Knights": "Newcastle Knights",
    "Cowboys": "North Queensland Cowboys",
    "Eels": "Parramatta Eels",
    "Panthers": "Penrith Panthers",
    "Rabbitohs": "South Sydney Rabbitohs",
    "Dragons": "St George Illawarra Dragons",
    "Roosters": "Sydney Roosters",
    "Warriors": "New Zealand Warriors",
    "Wests Tigers": "Wests Tigers",
    "Bears": "North Sydney Bears",
    "Chiefs": "Redcliffe Chiefs",
}


def scrape_afl_ladder(season: int = 2026) -> dict:
    """Scrape AFL ladder from afltables.com."""
    url = f"https://afltables.com/afl/seas/{season}.html"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    ladder = {}
    # afltables has the ladder in a table whose first row contains "Ladder"
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 19:
            continue

        first_text = rows[0].get_text(" ", strip=True)
        if "Ladder" not in first_text:
            continue

        # Header is row[1]: #, Team, P, W, ...
        # Data starts at row[2]: 1, Fremantle, 20, 18, ...
        for row in rows[2:]:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            pos_text = cells[0].get_text(strip=True)
            team_text = cells[1].get_text(strip=True)

            try:
                position = int(pos_text)
            except ValueError:
                continue

            if not team_text or len(team_text) < 3:
                continue

            full_name = None
            for short, full in AFL_NAME_MAP.items():
                if short.lower() == team_text.lower() or team_text.lower() == short.lower():
                    full_name = full
                    break
            if not full_name:
                for short, full in AFL_NAME_MAP.items():
                    if short.lower() in team_text.lower() or team_text.lower() in short.lower():
                        full_name = full
                        break

            ladder[full_name or team_text] = position

        if len(ladder) >= 15:
            break

    return ladder


def scrape_nrl_ladder() -> dict:
    """Build NRL ladder — uses model.db results (most reliable source)."""
    return build_nrl_ladder_from_db()


def scrape_nrl_ladder_api() -> dict:
    """Fallback: try NRL.com draw API for ladder data."""
    url = "https://www.nrl.com/draw/nrl-premiership/2026/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            return {}
    except Exception:
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")
    ladder = {}

    # Look for JSON data in scripts
    for script in soup.find_all("script"):
        text = script.string or ""
        if "ladder" in text.lower() or "standings" in text.lower():
            # Try to extract team positions from embedded data
            for m in re.finditer(r'"teamName"\s*:\s*"([^"]+)"', text):
                team = m.group(1)
                if team not in ladder:
                    full_name = None
                    for short, full in NRL_NAME_MAP.items():
                        if short.lower() in team.lower():
                            full_name = full
                            break
                    ladder[full_name or team] = len(ladder) + 1

    return ladder


def build_nrl_ladder_from_db() -> dict:
    """Build NRL ladder from model.db results if web scraping fails."""
    import sqlite3
    db_path = ROOT / "data" / "model.db"
    if not db_path.exists():
        return {}

    conn = sqlite3.connect(db_path)
    rows = conn.execute("""
        SELECT t.team_name,
               SUM(CASE
                   WHEN (r.home_score > r.away_score AND m.home_team_id = t.team_id)
                     OR (r.away_score > r.home_score AND m.away_team_id = t.team_id)
                   THEN 2 ELSE 0 END) as points,
               SUM(CASE WHEN r.home_score = r.away_score THEN 1 ELSE 0 END) as draws
        FROM teams t
        JOIN matches m ON (m.home_team_id = t.team_id OR m.away_team_id = t.team_id)
        JOIN results r ON r.match_id = m.match_id
        WHERE m.season = 2026 AND m.sport = 'NRL'
        GROUP BY t.team_name
        ORDER BY points DESC
    """).fetchall()
    conn.close()

    ladder = {}
    for i, (name, pts, draws) in enumerate(rows, 1):
        ladder[name] = i
    return ladder


def main():
    parser = argparse.ArgumentParser(description="Scrape ladder positions")
    parser.add_argument("--sport", required=True, choices=["NRL", "AFL", "ALL"])
    parser.add_argument("--season", type=int, default=2026)
    args = parser.parse_args()

    sports = ["NRL", "AFL"] if args.sport == "ALL" else [args.sport]

    for sport in sports:
        print(f"Scraping {sport} ladder...")

        if sport == "AFL":
            ladder = scrape_afl_ladder(args.season)
        else:
            ladder = scrape_nrl_ladder()
            if not ladder:
                print("  Web scrape failed, building from model.db...")
                ladder = build_nrl_ladder_from_db()

        if not ladder:
            print(f"  WARNING: No ladder data found for {sport}")
            continue

        out_path = DATA_DIR / f"{sport.lower()}_ladder.json"
        with open(out_path, "w") as f:
            json.dump(ladder, f, indent=2)

        print(f"  {len(ladder)} teams loaded")
        for team, pos in sorted(ladder.items(), key=lambda x: x[1]):
            print(f"    {pos:>2}. {team}")
        print(f"  Saved: {out_path}")


if __name__ == "__main__":
    main()
