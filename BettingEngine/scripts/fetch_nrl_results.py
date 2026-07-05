#!/usr/bin/env python3
"""
scripts/fetch_nrl_results.py

Automated NRL results scraper.

Hits the NRL.com draw API for rounds that are missing actual scores in the DB,
writes a results CSV, then calls load_results.py to ingest into the database.

Scheduled: every Monday at 09:00 via Windows Task Scheduler.

Round offset note:
  The DB has a pre-season R1 (Feb 28 World Club Challenge games) that the NRL
  official API does not count. So DB round N = NRL API round N-1.
  NRL_API_ROUND_OFFSET accounts for this. If the offset ever changes, set it
  via --api-round-offset or adjust the constant.

Usage:
  python scripts/fetch_nrl_results.py                    # auto-detect missing rounds
  python scripts/fetch_nrl_results.py --round 10         # specific DB round
  python scripts/fetch_nrl_results.py --season 2026 --round 10 --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

ROOT       = Path(__file__).resolve().parent.parent
LOG_DIR    = ROOT / "logs"
LOG_PATH   = LOG_DIR / "nrl_results_fetch.log"
IMPORT_DIR = ROOT / "data" / "import"
RAW_DIR    = ROOT / "data" / "nrl" / "results" / "raw"

NRL_DRAW_API = (
    "https://www.nrl.com/draw/data/"
    "?competition=111&season={season}&round={round}"
)

# DB round N = NRL API round (N + OFFSET).
# After the May 2026 round renumbering migration, DB rounds align with NRL official rounds.
NRL_API_ROUND_OFFSET = 0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json,*/*",
    "Accept-Language": "en-AU,en;q=0.9",
}

# Canonical name map -- nicknames and alternates to DB team_name
TEAM_MAP = {
    "Brisbane Broncos":              "Brisbane Broncos",
    "Broncos":                       "Brisbane Broncos",
    "Canterbury Bulldogs":           "Canterbury-Bankstown Bulldogs",
    "Canterbury-Bankstown Bulldogs": "Canterbury-Bankstown Bulldogs",
    "Bulldogs":                      "Canterbury-Bankstown Bulldogs",
    "Canberra Raiders":              "Canberra Raiders",
    "Raiders":                       "Canberra Raiders",
    "Cronulla Sharks":               "Cronulla-Sutherland Sharks",
    "Cronulla-Sutherland Sharks":    "Cronulla-Sutherland Sharks",
    "Sharks":                        "Cronulla-Sutherland Sharks",
    "Dolphins":                      "Dolphins",
    "Gold Coast Titans":             "Gold Coast Titans",
    "Titans":                        "Gold Coast Titans",
    "Manly Sea Eagles":              "Manly-Warringah Sea Eagles",
    "Manly-Warringah Sea Eagles":    "Manly-Warringah Sea Eagles",
    "Sea Eagles":                    "Manly-Warringah Sea Eagles",
    "Melbourne Storm":               "Melbourne Storm",
    "Storm":                         "Melbourne Storm",
    "Newcastle Knights":             "Newcastle Knights",
    "Knights":                       "Newcastle Knights",
    "New Zealand Warriors":          "New Zealand Warriors",
    "Warriors":                      "New Zealand Warriors",
    "North Queensland Cowboys":      "North Queensland Cowboys",
    "Cowboys":                       "North Queensland Cowboys",
    "Parramatta Eels":               "Parramatta Eels",
    "Eels":                          "Parramatta Eels",
    "Penrith Panthers":              "Penrith Panthers",
    "Panthers":                      "Penrith Panthers",
    "South Sydney Rabbitohs":        "South Sydney Rabbitohs",
    "Rabbitohs":                     "South Sydney Rabbitohs",
    "St. George Illawarra Dragons":  "St. George Illawarra Dragons",
    "St George Illawarra Dragons":   "St. George Illawarra Dragons",
    "Dragons":                       "St. George Illawarra Dragons",
    "Sydney Roosters":               "Sydney Roosters",
    "Roosters":                      "Sydney Roosters",
    "Wests Tigers":                  "Wests Tigers",
    "Tigers":                        "Wests Tigers",
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


def canon_team(raw: str) -> str:
    return TEAM_MAP.get(raw.strip(), raw.strip())


def fetch_json(url: str) -> dict | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        log.warning("Fetch failed %s -- %s", url, exc)
        return None


def extract_score(fixture: dict, side: str) -> int | None:
    """
    Try multiple field locations for team score. Returns None if not found.

    NRL.com draw API uses homeTeam.score / awayTeam.score for completed games.
    Fallbacks cover alternate field names in case the API schema changes.
    """
    team_data = fixture.get(side, {})
    for field in ("score", "points", "totalScore"):
        val = team_data.get(field)
        if val is not None:
            try:
                return int(val)
            except (TypeError, ValueError):
                pass

    # top-level fallback
    top_key = "homeScore" if side == "homeTeam" else "awayScore"
    val = fixture.get(top_key)
    if val is not None:
        try:
            return int(val)
        except (TypeError, ValueError):
            pass

    return None


def _fetch_one_api_round(season: int, api_round: int) -> list[dict]:
    """Fetch and parse one NRL API round. Returns [] if no scored games found."""
    url = NRL_DRAW_API.format(season=season, round=api_round)
    log.info("NRL draw API (api_round=%d): %s", api_round, url)
    raw = fetch_json(url)
    if not raw:
        return []

    # Save raw JSON for debugging
    raw_dir = RAW_DIR / str(season)
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"api-round-{api_round}.json"
    raw_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Saved raw -> %s", raw_path.name)

    fixtures = raw.get("fixtures", [])
    if not fixtures:
        log.warning("No fixtures in API response for api_round=%d", api_round)
        return []

    results = []
    for f in fixtures:
        if f.get("type") != "Match":
            continue

        home_name = canon_team(f.get("homeTeam", {}).get("nickName", ""))
        away_name = canon_team(f.get("awayTeam", {}).get("nickName", ""))
        if not home_name or not away_name:
            continue

        home_score = extract_score(f, "homeTeam")
        away_score = extract_score(f, "awayTeam")
        if home_score is None or away_score is None:
            log.info("  No score yet: %s vs %s", home_name, away_name)
            continue

        results.append({
            "home_team":  home_name,
            "away_team":  away_name,
            "home_score": home_score,
            "away_score": away_score,
        })
        log.info("  %s %d - %d %s", home_name, home_score, away_score, away_name)

    log.info("api_round=%d: %d scored games found", api_round, len(results))
    return results


def fetch_round_results(season: int, db_round: int, api_offset: int) -> list[dict]:
    """
    Fetch scored games for a DB round. Tries primary offset then adjacent rounds
    as fallback in case the offset drifts.
    """
    primary = db_round + api_offset
    for api_round in [primary, primary + 1, primary - 1]:
        if api_round < 1:
            continue
        results = _fetch_one_api_round(season, api_round)
        if results:
            log.info("DB R%d matched api_round=%d (offset=%d)", db_round, api_round, api_round - db_round)
            return results
    log.warning("No scored games found for DB R%d (tried api_rounds %d, %d, %d)",
                db_round, primary, primary + 1, primary - 1)
    return []


def find_match_id(conn: sqlite3.Connection, home_team: str, away_team: str,
                  db_round: int, season: int) -> int | None:
    row = conn.execute(
        """
        SELECT m.match_id
        FROM matches m
        JOIN teams th ON th.team_id = m.home_team_id
        JOIN teams ta ON ta.team_id = m.away_team_id
        WHERE th.team_name = ?
          AND ta.team_name = ?
          AND m.round_number = ?
          AND m.season = ?
          AND m.sport = 'NRL'
        LIMIT 1
        """,
        (home_team, away_team, db_round, season),
    ).fetchone()
    return row[0] if row else None


def rounds_missing_results(conn: sqlite3.Connection, season: int) -> list[int]:
    """Return sorted list of NRL DB round numbers that have matches but no results."""
    rows = conn.execute(
        """
        SELECT DISTINCT m.round_number
        FROM matches m
        LEFT JOIN results r ON r.match_id = m.match_id
        WHERE m.season = ?
          AND m.sport = 'NRL'
          AND r.result_id IS NULL
        ORDER BY m.round_number ASC
        """,
        (season,),
    ).fetchall()
    return [r[0] for r in rows]


def write_csv(db_round: int, season: int, rows: list[dict]) -> Path:
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = IMPORT_DIR / f"r{db_round}_results_{season}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["match_id", "home_team", "away_team", "home_score", "away_score", "match_date"],
        )
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote CSV: %s (%d rows)", csv_path.name, len(rows))
    return csv_path


def call_load_results(csv_path: Path) -> bool:
    cmd = [sys.executable, str(ROOT / "scripts" / "load_results.py"), str(csv_path)]
    log.info("Running load_results.py for %s", csv_path.name)
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        log.error("load_results.py exited with code %d", result.returncode)
        return False
    return True


def process_round(conn: sqlite3.Connection, season: int, db_round: int,
                  api_offset: int, dry_run: bool) -> bool:
    log.info("=== Processing DB R%d %d ===", db_round, season)

    api_results = fetch_round_results(season, db_round, api_offset)
    if not api_results:
        log.warning("No scored games -- R%d may not have played yet, skipping", db_round)
        return False

    csv_rows: list[dict] = []
    skipped = 0
    for game in api_results:
        match_id = find_match_id(conn, game["home_team"], game["away_team"], db_round, season)
        if match_id is None:
            log.warning(
                "No DB match_id for %s vs %s DB R%d %d",
                game["home_team"], game["away_team"], db_round, season,
            )
            skipped += 1
            continue
        row_meta = conn.execute(
            "SELECT match_date FROM matches WHERE match_id=?", (match_id,)
        ).fetchone()
        match_date = row_meta[0] if row_meta else ""
        csv_rows.append({
            "match_id":   match_id,
            "home_team":  game["home_team"],
            "away_team":  game["away_team"],
            "home_score": game["home_score"],
            "away_score": game["away_score"],
            "match_date": match_date,
        })

    if not csv_rows:
        log.error("No games could be matched to DB entries for R%d -- check TEAM_MAP and round offset", db_round)
        return False
    if skipped:
        log.warning("%d game(s) not matched to DB (check TEAM_MAP or DB fixture data)", skipped)

    csv_path = write_csv(db_round, season, csv_rows)

    if dry_run:
        log.info("DRY RUN -- CSV written but load_results.py skipped")
        return True

    return call_load_results(csv_path)


def main() -> None:
    setup_logging()
    p = argparse.ArgumentParser(description="Fetch NRL round results from NRL.com draw API")
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--round", dest="db_round", type=int, default=0,
                   help="DB round number to fetch (0 = auto-detect all rounds missing results)")
    p.add_argument("--api-round-offset", type=int, default=NRL_API_ROUND_OFFSET,
                   help=f"NRL API round = DB round + offset (default {NRL_API_ROUND_OFFSET})")
    p.add_argument("--settings", default="config/settings.yaml")
    p.add_argument("--dry-run", action="store_true",
                   help="Fetch and write CSV but do not load into DB")
    args = p.parse_args()

    settings = yaml.safe_load(open(args.settings))
    conn = sqlite3.connect(settings["database"]["path"])

    if args.db_round:
        rounds = [args.db_round]
    else:
        rounds = rounds_missing_results(conn, args.season)
        if not rounds:
            log.info("No rounds missing results for %d NRL -- nothing to do", args.season)
            conn.close()
            sys.exit(0)
        log.info("Rounds missing results in DB: %s", rounds)

    success = 0
    for rnd in rounds:
        ok = process_round(conn, args.season, rnd, args.api_round_offset, args.dry_run)
        if ok:
            success += 1

    conn.close()
    log.info("Done -- %d/%d rounds processed successfully", success, len(rounds))
    sys.exit(0 if success > 0 else 1)


if __name__ == "__main__":
    main()
