#!/usr/bin/env python3
"""Backfill per-player match stats from ESPN for Championship seasons.

Fetches match summaries, extracts per-player stats (goals, assists, shots,
saves, fouls, cards) plus starter/sub status and estimated minutes from
substitution events. Outputs a flat CSV for building rolling player features.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

LEAGUE_CODES = {
    "championship": "eng.2",
    "epl": "eng.1",
    "league1": "eng.3",
}
DEFAULT_LEAGUE = "championship"
BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.2"
OUT = Path(__file__).resolve().parents[1] / "data" / "championship" / "player_layer"

# ESPN name → backtest name (shared with train_starter_shadow.py)
ALIASES = {
    "Blackburn Rovers": "Blackburn", "Bristol City": "Bristol City",
    "Cardiff City": "Cardiff", "Coventry City": "Coventry",
    "Hull City": "Hull", "Ipswich Town": "Ipswich",
    "Leeds United": "Leeds", "Leicester City": "Leicester",
    "Norwich City": "Norwich", "Preston North End": "Preston",
    "Queens Park Rangers": "QPR", "Sheffield United": "Sheffield United",
    "Sheffield Wednesday": "Sheffield Weds", "Stoke City": "Stoke",
    "Swansea City": "Swansea", "West Bromwich Albion": "West Brom",
    "Plymouth Argyle": "Plymouth", "Oxford United": "Oxford",
    "Derby County": "Derby", "Luton Town": "Luton",
    "Birmingham City": "Birmingham", "Huddersfield Town": "Huddersfield",
    "Rotherham United": "Rotherham", "Southampton": "Southampton",
    "Burnley": "Burnley", "Sunderland": "Sunderland",
    "Middlesbrough": "Middlesbrough", "Millwall": "Millwall",
    "Watford": "Watford", "Portsmouth": "Portsmouth",
    "Charlton Athletic": "Charlton", "Wrexham": "Wrexham",
    "Wolverhampton Wanderers": "Wolves", "West Ham United": "West Ham",
    "Bolton Wanderers": "Bolton", "Lincoln City": "Lincoln",
}

# Map ESPN position abbreviations to position groups
POSITION_MAP = {
    "G": "GK", "GK": "GK",
    "CD": "DEF", "CD-L": "DEF", "CD-R": "DEF", "CB": "DEF",
    "LB": "DEF", "RB": "DEF", "LWB": "DEF", "RWB": "DEF",
    "WB": "DEF", "WB-L": "DEF", "WB-R": "DEF",
    "DM": "MID", "DM-L": "MID", "DM-R": "MID",
    "CM": "MID", "CM-L": "MID", "CM-R": "MID",
    "LM": "MID", "RM": "MID",
    "AM": "ATT", "AM-L": "ATT", "AM-R": "ATT",
    "LW": "ATT", "RW": "ATT", "W": "ATT",
    "CF": "ATT", "CF-L": "ATT", "CF-R": "ATT",
    "F": "ATT", "ST": "ATT",
    "SUB": "SUB",
}


def fetch(url: str) -> dict:
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
    })
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def event_ids(season: int) -> set[str]:
    """Get all match IDs for a Championship season from team schedules."""
    teams = fetch(f"{BASE}/teams")["sports"][0]["leagues"][0]["teams"]
    ids: set[str] = set()
    for item in teams:
        team_id = item["team"]["id"]
        schedule = fetch(f"{BASE}/teams/{team_id}/schedule?season={season}")
        ids.update(str(event["id"]) for event in schedule.get("events", []))
    return ids


def _parse_sub_minute(text: str) -> int | None:
    """Extract minute from sub event text like '60' or '90+2'."""
    match = re.search(r"(\d+)", str(text))
    return int(match.group(1)) if match else None


def _estimate_minutes(player: dict, sub_events: dict[str, int],
                      match_length: int = 90) -> float:
    """Estimate minutes played from starter/sub status and sub events."""
    name = player.get("athlete", {}).get("displayName", "")
    starter = player.get("starter", False)
    subbed_in = player.get("subbedIn", False)
    subbed_out = player.get("subbedOut", False)

    if not starter and not subbed_in:
        return 0.0

    sub_in_min = sub_events.get(f"in:{name}")
    sub_out_min = sub_events.get(f"out:{name}")

    if starter and not subbed_out:
        return float(match_length)
    elif starter and subbed_out and sub_out_min is not None:
        return float(sub_out_min)
    elif starter and subbed_out:
        return 65.0  # fallback: average sub-out time
    elif subbed_in and sub_in_min is not None:
        return float(match_length - sub_in_min)
    elif subbed_in:
        return 25.0  # fallback: average sub-in time remaining
    return 0.0


def parse_match(event_id: str, payload: dict | None = None) -> list[dict]:
    """Extract per-player stats from an ESPN match summary."""
    if payload is None:
        payload = fetch(f"{BASE}/summary?event={event_id}")

    header = payload.get("header", {}).get("competitions", [{}])[0]
    competitors = {c.get("homeAway"): c for c in header.get("competitors", [])}
    if not {"home", "away"}.issubset(competitors):
        return []

    home_c, away_c = competitors["home"], competitors["away"]
    kickoff = header.get("date", "")
    home_team = home_c["team"]["displayName"]
    away_team = away_c["team"]["displayName"]
    home_goals = home_c.get("score")
    away_goals = away_c.get("score")

    # Parse substitution events for minute estimation
    sub_events: dict[str, int] = {}
    for event in payload.get("keyEvents", []):
        etype = event.get("type", {}).get("text", "")
        if "Substitution" in etype or "sub" in etype.lower():
            minute = _parse_sub_minute(event.get("clock", {}).get("displayValue", ""))
            text = event.get("text", "")
            # Pattern: "Substitution, Team. PlayerIn replaces PlayerOut."
            m = re.search(r"\.?\s*(.+?)\s+replaces\s+(.+?)\.?$", text)
            if m and minute is not None:
                sub_events[f"in:{m.group(1).strip()}"] = minute
                sub_events[f"out:{m.group(2).strip()}"] = minute

    rows = []
    for roster in payload.get("rosters", []):
        team = roster.get("team", {}).get("displayName")
        side = roster.get("homeAway")
        for player in roster.get("roster", []):
            athlete = player.get("athlete", {})
            player_id = athlete.get("id")
            if not player_id:
                continue

            pos_raw = player.get("position", {}).get("abbreviation", "SUB")
            pos_group = POSITION_MAP.get(pos_raw, "MID")

            stats = {s["name"]: s["value"] for s in player.get("stats", [])}
            minutes = _estimate_minutes(player, sub_events)

            rows.append({
                "event_id": event_id,
                "kickoff": kickoff,
                "home_team": home_team,
                "away_team": away_team,
                "home_goals": home_goals,
                "away_goals": away_goals,
                "team": team,
                "side": side,
                "player_id": player_id,
                "player_name": athlete.get("displayName", ""),
                "position_raw": pos_raw,
                "position_group": pos_group,
                "starter": int(player.get("starter", False)),
                "subbed_in": int(player.get("subbedIn", False)),
                "subbed_out": int(player.get("subbedOut", False)),
                "minutes": minutes,
                "goals": stats.get("totalGoals", 0),
                "assists": stats.get("goalAssists", 0),
                "shots": stats.get("totalShots", 0),
                "shots_on_target": stats.get("shotsOnTarget", 0),
                "saves": stats.get("saves", 0),
                "fouls_committed": stats.get("foulsCommitted", 0),
                "fouls_suffered": stats.get("foulsSuffered", 0),
                "yellow_cards": stats.get("yellowCards", 0),
                "red_cards": stats.get("redCards", 0),
                "own_goals": stats.get("ownGoals", 0),
            })
    return rows


def main() -> None:
    global BASE
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--season", type=int, default=2025)
    ap.add_argument("--league", default="championship",
                    choices=list(LEAGUE_CODES.keys()),
                    help="League to fetch (default: championship)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--use-cached", action="store_true",
                    help="Read from match_feeds/ cache instead of fetching")
    args = ap.parse_args()

    league_code = LEAGUE_CODES[args.league]
    BASE = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}"

    # Separate cache/output dirs per league
    league_suffix = f"_{args.league}" if args.league != "championship" else ""
    cache_dir = OUT / f"match_feeds{league_suffix}"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if args.use_cached:
        ids = sorted(p.stem for p in cache_dir.glob("*.json"))
        print(f"Using {len(ids)} cached match feeds")
    else:
        print(f"Fetching event IDs for {args.league} season {args.season}...")
        ids = sorted(event_ids(args.season))
        print(f"Found {len(ids)} events")

    rows: list[dict] = []
    errors = 0

    def process(eid: str) -> list[dict]:
        cached = cache_dir / f"{eid}.json"
        if cached.exists():
            with open(cached) as f:
                return parse_match(eid, json.load(f))
        payload = fetch(f"{BASE}/summary?event={eid}")
        cached.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return parse_match(eid, payload)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process, eid): eid for eid in ids}
        for i, future in enumerate(as_completed(futures), 1):
            try:
                rows.extend(future.result())
            except Exception as exc:
                errors += 1
                print(f"{futures[future]} failed: {exc}")
            if i % 50 == 0:
                print(f"Processed {i}/{len(ids)} ({len(rows)} player rows)")

    OUT.mkdir(parents=True, exist_ok=True)
    filename = f"player_match_stats_espn_{args.league}_{args.season}.csv" if args.league != "championship" else f"player_match_stats_espn_{args.season}.csv"
    path = OUT / filename
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    matches = df.event_id.nunique() if len(df) else 0
    print(f"Saved {len(df)} player rows across {matches} matches to {path}")
    if errors:
        print(f"  {errors} events failed")


if __name__ == "__main__":
    main()
