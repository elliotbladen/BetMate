#!/usr/bin/env python3
"""
scripts/nrl_ht_live.py

NRL halftime live stats scraper — no login, no browser required.
Polls NRL.com draw API for halftime, then extracts all stats from
the match centre /data endpoint.

Usage:
    uv run python scripts/nrl_ht_live.py --round 15
    uv run python scripts/nrl_ht_live.py --round 15 --season 2026
    uv run python scripts/nrl_ht_live.py --round 15 --home Warriors --away Sharks
    uv run python scripts/nrl_ht_live.py --round 15 --force   # skip halftime check (testing)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

_ROOT = Path(__file__).resolve().parents[1]
HALFTIME_DIR = _ROOT / "data" / "nrl" / "halfTime"
PRICING_SCRIPT = _ROOT / "scripts" / "halfTime_price_nrl.py"

NRL_DRAW_API = "https://www.nrl.com/draw/data/?competition=111&season={season}&round={round}"
NRL_BASE     = "https://www.nrl.com"
POLL_INTERVAL = 30   # seconds between draw API checks

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json,*/*",
}

# First half = 0–2400 game seconds (40 minutes)
FIRST_HALF_END = 2400


# ── Draw API ──────────────────────────────────────────────────────────────────

def fetch_fixtures(season: int, round_num: int) -> list[dict]:
    url = NRL_DRAW_API.format(season=season, round=round_num)
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return [f for f in r.json().get("fixtures", []) if f.get("type") == "Match"]
    except Exception as exc:
        print(f"  Draw API error: {exc}")
        return []


def is_halftime(fixture: dict) -> bool:
    state = (fixture.get("matchState") or "").lower()
    game_secs = fixture.get("gameSeconds", 0) or 0
    if any(s in state for s in ("halftime", "half time", "half_time", "ht", "interval")):
        return True
    # Live game that has hit 40 mins
    if game_secs >= FIRST_HALF_END and "live" in state:
        return True
    return False


def fixture_label(f: dict) -> str:
    h = f.get("homeTeam", {}).get("nickName", "?")
    a = f.get("awayTeam", {}).get("nickName", "?")
    return f"{h} vs {a}"


def match_centre_url(fixture: dict) -> str:
    return NRL_BASE + fixture.get("matchCentreUrl", "").rstrip("/")


# ── Match data fetcher ────────────────────────────────────────────────────────

def fetch_match_data(mc_url: str) -> dict | None:
    url = mc_url.rstrip("/") + "/data"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        print(f"  Match data fetch error: {exc}")
        return None


# ── Stats extraction ──────────────────────────────────────────────────────────

def get_stat(groups: list[dict], stat_title: str) -> tuple[float, float] | None:
    """Find a stat by title across all groups. Returns (home_value, away_value)."""
    for group in groups:
        for stat in group.get("stats", []):
            if stat.get("title", "").lower() == stat_title.lower():
                home = stat.get("homeValue", {})
                away = stat.get("awayValue", {})
                return float(home.get("value", 0) or 0), float(away.get("value", 0) or 0)
    return None


def count_timeline_events(timeline: list[dict], event_type: str, team_id: int, max_seconds: int = FIRST_HALF_END) -> int:
    """Count timeline events of a given type for a team in the first half."""
    return sum(
        1 for e in timeline
        if e.get("type") == event_type
        and e.get("teamId") == team_id
        and (e.get("gameSeconds") or 0) <= max_seconds
    )


def extract_halftime_stats(data: dict, season: int, round_num: int) -> dict:
    """Extract all halftime stats from NRL match centre data."""
    home = data.get("homeTeam", {})
    away = data.get("awayTeam", {})
    home_id = home.get("teamId")
    away_id = away.get("teamId")

    home_scoring = home.get("scoring") or {}
    away_scoring = away.get("scoring") or {}

    # HT scores
    home_ht = int(home_scoring.get("halfTimeScore") or 0)
    away_ht = int(away_scoring.get("halfTimeScore") or 0)

    # Stats groups (at halftime these ARE the first half stats)
    groups = data.get("stats", {}).get("groups", [])

    # Possession & completion
    poss = get_stat(groups, "Possession %")
    home_poss = poss[0] if poss else 0.0
    away_poss = poss[1] if poss else 0.0

    comp = get_stat(groups, "Completion Rate")
    home_comp = comp[0] if comp else 0.0
    away_comp = comp[1] if comp else 0.0

    # Run metres
    metres = get_stat(groups, "All Run Metres")
    home_metres = int(metres[0]) if metres else 0
    away_metres = int(metres[1]) if metres else 0

    # Errors
    errors = get_stat(groups, "Errors")
    home_errors = int(errors[0]) if errors else 0
    away_errors = int(errors[1]) if errors else 0

    # Penalties
    pens = get_stat(groups, "Penalties Conceded")
    home_pens = int(pens[0]) if pens else 0
    away_pens = int(pens[1]) if pens else 0

    # Set restarts — may be in stats groups or must be counted from timeline
    set_restarts = get_stat(groups, "Set Restarts") or get_stat(groups, "6 Agains") or get_stat(groups, "Six Agains")
    if set_restarts:
        home_restarts = int(set_restarts[0])
        away_restarts = int(set_restarts[1])
    else:
        # Count from timeline (SetRestart events = restarts RECEIVED by that team's opponent)
        timeline = data.get("timeline", [])
        # SetRestart event is conceded BY a team — meaning opponent receives an extra set
        # home_restarts_received = restarts conceded by away team
        away_restart_count = count_timeline_events(timeline, "SetRestart", away_id)
        home_restart_count = count_timeline_events(timeline, "SetRestart", home_id)
        # A SetRestart penalises the team that conceded it → the other team gets the restart
        home_restarts = away_restart_count   # restarts received by home = conceded by away
        away_restarts = home_restart_count

    # Tries in first half (from timeline, filtered to first half)
    timeline = data.get("timeline", [])
    home_tries_ht = count_timeline_events(timeline, "Try", home_id)
    away_tries_ht = count_timeline_events(timeline, "Try", away_id)

    # Conversions in first half (Goal events in NRL timeline = conversions/penalty goals)
    # Filter to only events preceded by a Try (conversions, not penalty goals)
    home_conv_ht = count_timeline_events(timeline, "Goal", home_id)
    away_conv_ht = count_timeline_events(timeline, "Goal", away_id)

    # Inside 20m — not directly in stats API, set to 0
    home_in20 = 0
    away_in20 = 0

    # Kickoff time
    start_raw = data.get("startTime", "")
    try:
        game_date = start_raw[:10]
    except Exception:
        game_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    home_name = home.get("name") or home.get("nickName", "Home")
    away_name = away.get("name") or away.get("nickName", "Away")

    stats = {
        "season": season,
        "round": round_num,
        "game_date": game_date,
        "home_team": home_name,
        "away_team": away_name,
        "source": "nrl_api",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "home_ht_score": home_ht,
        "away_ht_score": away_ht,
        "home_tries": home_tries_ht,
        "away_tries": away_tries_ht,
        "home_conversions_made": home_conv_ht,
        "away_conversions_made": away_conv_ht,
        "home_errors": home_errors,
        "away_errors": away_errors,
        "home_set_restarts_received": home_restarts,
        "away_set_restarts_received": away_restarts,
        "home_run_metres": home_metres,
        "away_run_metres": away_metres,
        "home_possession_pct": home_poss,
        "away_possession_pct": away_poss,
        "home_completion_pct": home_comp,
        "away_completion_pct": away_comp,
        "home_penalties_conceded": home_pens,
        "away_penalties_conceded": away_pens,
        "home_inside_20_possessions": home_in20,
        "away_inside_20_possessions": away_in20,
        "notes": "",
    }

    return stats


def print_stats(stats: dict) -> None:
    h = stats["home_team"]
    a = stats["away_team"]
    print(f"\n  {'─'*50}")
    print(f"  HT Score:      {h} {stats['home_ht_score']} – {stats['away_ht_score']} {a}")
    print(f"  Tries:         {h} {stats['home_tries']} / {a} {stats['away_tries']}")
    print(f"  Conversions:   {h} {stats['home_conversions_made']} / {a} {stats['away_conversions_made']}")
    print(f"  Errors:        {h} {stats['home_errors']} / {a} {stats['away_errors']}")
    print(f"  Set Restarts:  {h} {stats['home_set_restarts_received']} / {a} {stats['away_set_restarts_received']}")
    print(f"  Run Metres:    {h} {stats['home_run_metres']} / {a} {stats['away_run_metres']}")
    print(f"  Possession:    {h} {stats['home_possession_pct']:.0f}% / {a} {stats['away_possession_pct']:.0f}%")
    print(f"  Completion:    {h} {stats['home_completion_pct']:.0f}% / {a} {stats['away_completion_pct']:.0f}%")
    print(f"  Penalties:     {h} {stats['home_penalties_conceded']} / {a} {stats['away_penalties_conceded']}")
    print(f"  {'─'*50}")


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
    cmd = [sys.executable, str(PRICING_SCRIPT), "--file", str(stats_path), "--save"]
    subprocess.run(cmd)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="NRL halftime live stats scraper")
    p.add_argument("--round",  type=int, required=True)
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--home",   type=str, default=None, help="Filter to this home team nick")
    p.add_argument("--away",   type=str, default=None, help="Filter to this away team nick")
    p.add_argument("--force",  action="store_true", help="Skip halftime check (for testing on completed games)")
    p.add_argument("--once",   action="store_true", help="Poll once and exit (don't loop)")
    args = p.parse_args()

    print(f"\nNRL Halftime Scraper — R{args.round} {args.season}")
    print(f"Polling every {POLL_INTERVAL}s. Ctrl+C to stop.\n")

    processed = set()

    while True:
        fixtures = fetch_fixtures(args.season, args.round)

        # Optional filter by team name
        if args.home or args.away:
            filtered = []
            for f in fixtures:
                h = f.get("homeTeam", {}).get("nickName", "").lower()
                a = f.get("awayTeam", {}).get("nickName", "").lower()
                if args.home and args.home.lower() not in h:
                    continue
                if args.away and args.away.lower() not in a:
                    continue
                filtered.append(f)
            fixtures = filtered

        halftime_fixtures = [f for f in fixtures if (is_halftime(f) or args.force) and fixture_label(f) not in processed]

        if not halftime_fixtures:
            states = [(fixture_label(f), f.get("matchState", "?"), f.get("gameSeconds", 0)) for f in fixtures]
            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] No halftime games yet. States: {states}")
        else:
            for fixture in halftime_fixtures:
                label = fixture_label(fixture)
                print(f"\n{'='*55}")
                print(f"  HALFTIME DETECTED: {label}")
                print(f"{'='*55}")

                mc_url = match_centre_url(fixture)
                print(f"  Fetching: {mc_url}/data")
                data = fetch_match_data(mc_url)
                if not data:
                    print("  ERROR: Could not fetch match data.")
                    continue

                stats = extract_halftime_stats(data, args.season, args.round)
                print_stats(stats)

                stats_path = save_stats(stats)
                processed.add(label)

                print("\n  Running pricing model...")
                run_pricing(stats_path)

        if args.once:
            break

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
