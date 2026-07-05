#!/usr/bin/env python3
"""
scripts/afl_ht_live.py

AFL halftime live stats scraper — no login, no browser required.
Polls Squiggle API for AFL games at halftime, extracts quarter scores,
saves JSON, and fires the AFL halftime pricing script.

Squiggle API: https://api.squiggle.com.au/?q=games;year=YYYY;round=RR
  complete=50  → game is at halftime
  timestr      → "Half Time" (or in-quarter like "Q2  3:45")
  hgoals/hbehinds/agoals/abehinds → live cumulative scores

Usage:
    uv run python scripts/afl_ht_live.py --round 14
    uv run python scripts/afl_ht_live.py --round 14 --season 2026
    uv run python scripts/afl_ht_live.py --round 14 --home Melbourne --away Essendon
    uv run python scripts/afl_ht_live.py --round 14 --force   # skip halftime check (testing)
    uv run python scripts/afl_ht_live.py --round 14 --once    # poll once and exit
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

_ROOT = Path(__file__).resolve().parents[1]
HALFTIME_DIR = _ROOT / "data" / "afl" / "halfTime"
PRICING_SCRIPT = _ROOT / "scripts" / "halfTime_price_afl.py"

SQUIGGLE_URL = "https://api.squiggle.com.au/?q=games;year={year};round={round}"
POLL_INTERVAL = 30  # seconds between polls

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json,*/*",
}

FW_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}
FOOTYWIRE_SCOREBOARD = "https://www.footywire.com/afl/footy/live_scoreboard"
FOOTYWIRE_STATS_URL  = "https://www.footywire.com/afl/footy/live_stats?mid={mid}"


# ── Squiggle API ───────────────────────────────────────────────────────────────

def fetch_games(season: int, round_num: int) -> list[dict]:
    url = SQUIGGLE_URL.format(year=season, round=round_num)
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json().get("games", [])
    except Exception as exc:
        print(f"  Squiggle API error: {exc}")
        return []


def is_halftime(game: dict) -> bool:
    """Detect halftime: complete==50 or timestr contains 'half time'."""
    complete = game.get("complete", 0) or 0
    timestr = (game.get("timestr") or "").lower()
    if "half time" in timestr or "halftime" in timestr:
        return True
    if complete == 50:
        return True
    return False


def game_label(g: dict) -> str:
    return f"{g.get('hteam','?')} vs {g.get('ateam','?')}"


# ── FootyWire live stats ───────────────────────────────────────────────────────

def fetch_footywire_mid(home_team: str, away_team: str) -> int | None:
    """
    Find the FootyWire live match ID by scraping the live scoreboard page
    and matching team names against the game we want.
    Returns the mid integer, or None if not found.
    """
    try:
        r = requests.get(FOOTYWIRE_SCOREBOARD, headers=FW_HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as exc:
        print(f"  FootyWire scoreboard error: {exc}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    home_short = home_team.split()[-1].lower()
    away_short = away_team.split()[-1].lower()

    for a in soup.find_all("a", href=True):
        if "live_stats?mid=" not in a["href"]:
            continue
        try:
            mid = int(a["href"].split("mid=")[-1])
        except ValueError:
            continue
        # Check surrounding container for both team names
        container = a.find_parent("tr") or a.find_parent("div") or a.find_parent("table")
        if container is None:
            continue
        text = container.get_text(" ", strip=True).lower()
        if home_short in text and away_short in text:
            return mid

    return None


def fetch_footywire_stats(mid: int) -> dict:
    """
    Scrape the Head-to-Head stats table from a FootyWire live stats page.
    Returns dict with home/away inside 50s, clearances, clangers.
    Returns empty dict on any failure — caller falls back gracefully.
    """
    try:
        r = requests.get(FOOTYWIRE_STATS_URL.format(mid=mid), headers=FW_HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as exc:
        print(f"  FootyWire stats error: {exc}")
        return {}

    html = r.text

    def _extract(label: str) -> tuple[int, int] | None:
        """Parse '{home_val} {label} {away_val}' from H2H table text."""
        m = re.search(rf"(\d+)\s+{re.escape(label)}\s+(\d+)", html)
        if m:
            return int(m.group(1)), int(m.group(2))
        return None

    result: dict = {}

    i50 = _extract("Inside 50s")
    if i50:
        result["home_inside_50s"], result["away_inside_50s"] = i50

    clr = _extract("Clearances")
    if clr:
        result["home_clearances"], result["away_clearances"] = clr

    clg = _extract("Clangers")
    if clg:
        result["home_clangers"], result["away_clangers"] = clg

    return result


def enrich_with_live_stats(stats: dict) -> dict:
    """
    Auto-find FootyWire match ID and scrape live team stats.
    Enriches stats dict in-place. Prints what was found.
    """
    home = stats["home_team"]
    away = stats["away_team"]

    print(f"  Fetching FootyWire live stats for {home} vs {away}...")
    mid = fetch_footywire_mid(home, away)
    if mid is None:
        print("  FootyWire: match not found on live scoreboard — stats unavailable")
        return stats

    print(f"  FootyWire: found mid={mid}")
    fw_stats = fetch_footywire_stats(mid)

    if not fw_stats:
        print("  FootyWire: stats table empty or parse failed")
        return stats

    stats.update(fw_stats)
    stats["footywire_mid"] = mid

    home_i50 = fw_stats.get("home_inside_50s", "?")
    away_i50 = fw_stats.get("away_inside_50s", "?")
    home_clr = fw_stats.get("home_clearances", "?")
    away_clr = fw_stats.get("away_clearances", "?")
    home_clg = fw_stats.get("home_clangers", "?")
    away_clg = fw_stats.get("away_clangers", "?")
    print(f"  I50: {home} {home_i50} / {away} {away_i50}")
    print(f"  Clearances: {home} {home_clr} / {away} {away_clr}")
    print(f"  Clangers: {home} {home_clg} / {away} {away_clg}")

    return stats


# ── Stats extraction ───────────────────────────────────────────────────────────

def extract_halftime_stats(game: dict, season: int, round_num: int) -> dict:
    home_team = game.get("hteam", "Home")
    away_team = game.get("ateam", "Away")

    home_goals    = int(game.get("hgoals") or 0)
    home_behinds  = int(game.get("hbehinds") or 0)
    away_goals    = int(game.get("agoals") or 0)
    away_behinds  = int(game.get("abehinds") or 0)

    home_ht_score = home_goals * 6 + home_behinds
    away_ht_score = away_goals * 6 + away_behinds

    # Date: Squiggle 'date' is local time in format "2026-06-13 13:15:00"
    date_raw = game.get("date", "")
    try:
        game_date = date_raw[:10]
    except Exception:
        game_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    venue = game.get("venue", "")

    stats = {
        "season":         season,
        "round":          round_num,
        "game_date":      game_date,
        "home_team":      home_team,
        "away_team":      away_team,
        "venue":          venue,
        "source":         "squiggle_api",
        "collected_at":   datetime.now(timezone.utc).isoformat(),
        "home_ht_score":  home_ht_score,
        "away_ht_score":  away_ht_score,
        "home_goals":     home_goals,
        "home_behinds":   home_behinds,
        "away_goals":     away_goals,
        "away_behinds":   away_behinds,
        "squiggle_id":    game.get("id"),
        "timestr":        game.get("timestr", ""),
        "notes":          "",
    }
    return stats


def print_stats(stats: dict) -> None:
    h = stats["home_team"]
    a = stats["away_team"]
    print(f"\n  {'─'*52}")
    print(f"  HT Score:  {h} {stats['home_goals']}.{stats['home_behinds']} ({stats['home_ht_score']}) "
          f"– {a} {stats['away_goals']}.{stats['away_behinds']} ({stats['away_ht_score']})")
    print(f"  Venue:     {stats['venue']}")
    print(f"  {'─'*52}")


def save_stats(stats: dict) -> Path:
    round_dir = HALFTIME_DIR / f"R{stats['round']:02d}"
    round_dir.mkdir(parents=True, exist_ok=True)
    home_nick = stats["home_team"].split()[-1].lower()
    away_nick = stats["away_team"].split()[-1].lower()
    filename = f"{stats['game_date']}_{home_nick}_vs_{away_nick}_stats.json"
    path = round_dir / filename
    path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"\n  Saved → {path}")
    return path


def run_pricing(stats_path: Path) -> None:
    if not PRICING_SCRIPT.exists():
        print(f"  (AFL pricing script not yet built at {PRICING_SCRIPT} — skipping)")
        return
    cmd = [sys.executable, str(PRICING_SCRIPT), "--file", str(stats_path), "--save"]
    subprocess.run(cmd)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="AFL halftime live stats scraper (Squiggle API)")
    p.add_argument("--round",  type=int, required=True)
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--home",   type=str, default=None, help="Filter to home team name (partial match)")
    p.add_argument("--away",   type=str, default=None, help="Filter to away team name (partial match)")
    p.add_argument("--force",  action="store_true", help="Skip halftime check (for testing on completed games)")
    p.add_argument("--once",   action="store_true", help="Poll once and exit")
    args = p.parse_args()

    print(f"\nAFL Halftime Scraper — R{args.round} {args.season}")
    print(f"Polling every {POLL_INTERVAL}s. Ctrl+C to stop.\n")

    processed = set()

    while True:
        games = fetch_games(args.season, args.round)

        # Optional team filter
        if args.home or args.away:
            filtered = []
            for g in games:
                h = g.get("hteam", "").lower()
                a = g.get("ateam", "").lower()
                if args.home and args.home.lower() not in h:
                    continue
                if args.away and args.away.lower() not in a:
                    continue
                filtered.append(g)
            games = filtered

        halftime_games = [
            g for g in games
            if (is_halftime(g) or args.force) and game_label(g) not in processed
        ]

        if not halftime_games:
            states = [(game_label(g), g.get("timestr", "?"), g.get("complete", 0)) for g in games]
            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] No halftime games yet. States: {states}")
        else:
            for game in halftime_games:
                label = game_label(game)
                print(f"\n{'='*56}")
                print(f"  HALFTIME DETECTED: {label}")
                print(f"  timestr={game.get('timestr')}  complete={game.get('complete')}")
                print(f"{'='*56}")

                stats = extract_halftime_stats(game, args.season, args.round)
                print_stats(stats)

                enrich_with_live_stats(stats)

                stats_path = save_stats(stats)
                processed.add(label)

                print("\n  Running AFL pricing model...")
                run_pricing(stats_path)

        if args.once:
            break

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
