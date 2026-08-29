#!/usr/bin/env python3
"""
scripts/bulk_import_nrl_2026.py

One-off script to bootstrap model.db on a fresh machine.
Fetches all 2026 NRL rounds from the NRL.com draw API,
creates match entries + results in one pass.

Usage:
    uv run --with requests --with pyyaml python scripts/bulk_import_nrl_2026.py
"""

import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "model.db"

NRL_DRAW_API = "https://www.nrl.com/draw/data/?competition=111&season={season}&round={round}"
SEASON = 2026
MAX_ROUND = 25  # fetch up to this round

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json,*/*",
}

TEAM_MAP = {
    "Broncos": "Brisbane Broncos",
    "Raiders": "Canberra Raiders",
    "Bulldogs": "Canterbury-Bankstown Bulldogs",
    "Sharks": "Cronulla-Sutherland Sharks",
    "Dolphins": "Dolphins",
    "Titans": "Gold Coast Titans",
    "Sea Eagles": "Manly-Warringah Sea Eagles",
    "Storm": "Melbourne Storm",
    "Knights": "Newcastle Knights",
    "Warriors": "New Zealand Warriors",
    "Cowboys": "North Queensland Cowboys",
    "Eels": "Parramatta Eels",
    "Panthers": "Penrith Panthers",
    "Rabbitohs": "South Sydney Rabbitohs",
    "Dragons": "St. George Illawarra Dragons",
    "Roosters": "Sydney Roosters",
    "Wests Tigers": "Wests Tigers",
    # Full names map to themselves
    "Brisbane Broncos": "Brisbane Broncos",
    "Canberra Raiders": "Canberra Raiders",
    "Canterbury-Bankstown Bulldogs": "Canterbury-Bankstown Bulldogs",
    "Cronulla-Sutherland Sharks": "Cronulla-Sutherland Sharks",
    "Gold Coast Titans": "Gold Coast Titans",
    "Manly-Warringah Sea Eagles": "Manly-Warringah Sea Eagles",
    "Melbourne Storm": "Melbourne Storm",
    "Newcastle Knights": "Newcastle Knights",
    "New Zealand Warriors": "New Zealand Warriors",
    "North Queensland Cowboys": "North Queensland Cowboys",
    "Parramatta Eels": "Parramatta Eels",
    "Penrith Panthers": "Penrith Panthers",
    "South Sydney Rabbitohs": "South Sydney Rabbitohs",
    "St. George Illawarra Dragons": "St. George Illawarra Dragons",
    "Sydney Roosters": "Sydney Roosters",
    "Wests Tigers": "Wests Tigers",
}


def canon(name: str) -> str:
    return TEAM_MAP.get(name.strip(), name.strip())


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    # Build team name -> id lookup
    team_rows = conn.execute("SELECT team_id, team_name FROM teams WHERE league='NRL'").fetchall()
    team_ids = {row[1]: row[0] for row in team_rows}
    print(f"NRL teams in DB: {len(team_ids)}")
    if len(team_ids) < 17:
        print("ERROR: Not enough NRL teams seeded. Run team seed first.")
        sys.exit(1)

    # Build venue name -> id lookup
    venue_rows = conn.execute("SELECT venue_id, venue_name FROM venues").fetchall()
    venue_ids = {row[1]: row[0] for row in venue_rows}

    now = datetime.now(timezone.utc).isoformat()
    total_matches = 0
    total_results = 0

    for rnd in range(1, MAX_ROUND + 1):
        url = NRL_DRAW_API.format(season=SEASON, round=rnd)
        print(f"\n--- Round {rnd} ---")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  FAILED: {e}")
            continue

        fixtures = data.get("fixtures", [])
        if not fixtures:
            print(f"  No fixtures returned")
            continue

        for f in fixtures:
            if f.get("type") != "Match":
                continue

            home_raw = f.get("homeTeam", {}).get("nickName", "")
            away_raw = f.get("awayTeam", {}).get("nickName", "")
            home_name = canon(home_raw)
            away_name = canon(away_raw)

            home_id = team_ids.get(home_name)
            away_id = team_ids.get(away_name)
            if not home_id or not away_id:
                print(f"  SKIP: Unknown team {home_raw!r}={home_name!r} or {away_raw!r}={away_name!r}")
                continue

            # Extract date
            kickoff = f.get("clock", {}).get("kickOffTimeLong", "") or ""
            match_date = ""
            if kickoff:
                try:
                    match_date = datetime.fromisoformat(kickoff.replace("Z", "+00:00")).strftime("%Y-%m-%d")
                except Exception:
                    pass
            if not match_date:
                match_date = f"2026-{rnd:02d}-01"  # placeholder

            # Find or match venue
            venue_raw = f.get("venue", "")
            venue_id = venue_ids.get(venue_raw)
            if not venue_id:
                # Try fuzzy match
                for vname, vid in venue_ids.items():
                    if venue_raw and (venue_raw.lower() in vname.lower() or vname.lower() in venue_raw.lower()):
                        venue_id = vid
                        break
            if not venue_id:
                # Insert new venue
                conn.execute(
                    "INSERT INTO venues (venue_name, city, country, surface_type) VALUES (?, '', 'Australia', 'grass')",
                    (venue_raw or f"Unknown R{rnd}",)
                )
                venue_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                venue_ids[venue_raw] = venue_id
                print(f"  NEW VENUE: {venue_raw!r} -> venue_id={venue_id}")

            source_key = f"nrl-{SEASON}-r{rnd}-{home_id}-{away_id}"

            # Check if match already exists
            existing = conn.execute(
                "SELECT match_id FROM matches WHERE source_match_key=?", (source_key,)
            ).fetchone()

            if existing:
                match_id = existing[0]
            else:
                conn.execute("""
                    INSERT INTO matches
                        (sport, competition, season, round_number, match_date,
                         kickoff_datetime, home_team_id, away_team_id, venue_id,
                         status, source_match_key, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    "NRL", "NRL Premiership", SEASON, rnd, match_date,
                    kickoff or match_date, home_id, away_id, venue_id,
                    "scheduled", source_key, now, now,
                ))
                match_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                total_matches += 1

            # Try to extract scores
            home_score = None
            away_score = None
            for field in ("score", "points", "totalScore"):
                hs = f.get("homeTeam", {}).get(field)
                aws = f.get("awayTeam", {}).get(field)
                if hs is not None and aws is not None:
                    try:
                        home_score = int(hs)
                        away_score = int(aws)
                        break
                    except (TypeError, ValueError):
                        pass

            if home_score is not None and away_score is not None:
                # Check if result already exists
                has_result = conn.execute(
                    "SELECT result_id FROM results WHERE match_id=?", (match_id,)
                ).fetchone()

                if not has_result:
                    total_pts = home_score + away_score
                    margin = home_score - away_score
                    winner_id = home_id if margin > 0 else (away_id if margin < 0 else None)

                    conn.execute("""
                        INSERT INTO results
                            (match_id, home_score, away_score, total_score, margin,
                             winning_team_id, result_status, captured_at)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (
                        match_id, home_score, away_score, total_pts, margin,
                        winner_id, "final", now,
                    ))
                    total_results += 1

                    # Update match status
                    conn.execute("UPDATE matches SET status='completed' WHERE match_id=?", (match_id,))

                print(f"  {home_name} {home_score} - {away_score} {away_name}")
            else:
                print(f"  {home_name} vs {away_name} (no score yet)")

        conn.commit()
        time.sleep(0.5)  # Be polite to the API

    conn.close()
    print(f"\n=== DONE ===")
    print(f"Matches inserted: {total_matches}")
    print(f"Results inserted: {total_results}")


if __name__ == "__main__":
    main()
