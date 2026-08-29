"""Fetch current EPL or Championship rosters from ESPN's public competition feed.

This is roster ingestion only. It must never be used as injury, suspension or
line-up confirmation evidence. Availability is entered through player_tracker,
with a source and timestamp.

Usage:
  python3 ml/football/fetch/fetch_espn_rosters.py --league epl
  python3 ml/football/fetch/fetch_espn_rosters.py --league championship --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ml.football.league_config import load_league
from ml.football.player_layer.availability import AvailabilityStore


ESPN_SLUG = {"epl": "eng.1", "championship": "eng.2"}
POSITION_MAP = {
    "goalkeeper": "GK", "centre-back": "CB", "center-back": "CB",
    "defender": "CB", "right-back": "FB", "left-back": "FB", "full-back": "FB",
    "wing-back": "WB", "defensive midfielder": "DM", "central midfielder": "CM",
    "midfielder": "CM", "attacking midfielder": "AM", "winger": "W",
    "forward": "ST", "striker": "ST", "centre-forward": "ST", "center-forward": "ST",
}

# Only exceptions that cannot safely be inferred from punctuation/token matching.
TEAM_ALIASES = {
    "AFC Bournemouth": "Bournemouth", "Brighton & Hove Albion": "Brighton",
    "Leeds United": "Leeds", "Manchester City": "Man City", "Manchester United": "Man United",
    "Newcastle United": "Newcastle", "Nottingham Forest": "Nott'm Forest",
    "Sunderland": "Sunderland",
    "Tottenham Hotspur": "Tottenham", "West Ham United": "West Ham",
    "Wolverhampton Wanderers": "Wolves", "Queens Park Rangers": "QPR",
    "Sheffield United": "Sheffield United", "Sheffield Wednesday": "Sheffield Weds",
    "West Bromwich Albion": "West Brom", "Preston North End": "Preston",
    "Blackburn Rovers": "Blackburn", "Bristol City": "Bristol City",
    "Bolton Wanderers": "Bolton", "Burnley": "Burnley", "Cardiff City": "Cardiff",
    "Coventry City": "Coventry", "Derby County": "Derby", "Hull City": "Hull",
    "Ipswich Town": "Ipswich", "Leicester City": "Leicester", "Middlesbrough": "Middlesbrough",
    "Norwich City": "Norwich", "Oxford United": "Oxford", "Portsmouth": "Portsmouth",
    "Southampton": "Southampton", "Stoke City": "Stoke", "Swansea City": "Swansea",
    "Watford": "Watford", "Wrexham": "Wrexham", "Birmingham City": "Birmingham", "Lincoln City": "Lincoln",
    "Charlton Athletic": "Charlton", "Millwall": "Millwall",
}


def _fetch_json(url: str) -> dict:
    # ESPN rejects non-browser-looking user agents on some endpoints. This is a
    # read-only public request; we still archive/import only the roster fields.
    request = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
    })
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _position(athlete: dict) -> str | None:
    raw = athlete.get("position") or {}
    values = [raw.get("displayName"), raw.get("name"), raw.get("abbreviation")]
    for value in values:
        if value and str(value).strip().lower() in POSITION_MAP:
            return POSITION_MAP[str(value).strip().lower()]
    # ESPN normally supplies an abbreviation; handle common short forms.
    shorthand = str(raw.get("abbreviation") or "").upper()
    return {"GK": "GK", "DF": "CB", "MF": "CM", "FW": "ST"}.get(shorthand)


def _model_teams(league: str) -> set[str]:
    cfg = load_league(league)
    rows = __import__("pandas").read_csv(cfg.matches_csv)
    latest = sorted(rows["Season"].dropna().unique())[-1]
    season = rows[rows["Season"] == latest]
    return set(season["HomeTeam"].dropna()) | set(season["AwayTeam"].dropna())


def _canonical_team(espn_name: str, model_teams: set[str]) -> str | None:
    alias = TEAM_ALIASES.get(espn_name, espn_name)
    # An explicit alias is the Football-Data convention even if this club is a
    # newly promoted side absent from the currently archived match history.
    if espn_name in TEAM_ALIASES:
        return alias
    if alias in model_teams:
        return alias
    scored = sorted(((SequenceMatcher(None, alias.lower(), team.lower()).ratio(), team) for team in model_teams), reverse=True)
    if scored and scored[0][0] >= 0.72:
        return scored[0][1]
    return None


def fetch_rosters(league: str, dry_run: bool = False) -> list[dict]:
    if league not in ESPN_SLUG:
        raise ValueError("league must be epl or championship")
    slug = ESPN_SLUG[league]
    teams_payload = _fetch_json(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/teams")
    teams = teams_payload["sports"][0]["leagues"][0]["teams"]
    model_teams = _model_teams(league)
    rows: list[dict] = []
    unmapped: list[str] = []
    skipped: list[str] = []
    for item in teams:
        team = item["team"]
        canonical = _canonical_team(team["displayName"], model_teams)
        if canonical is None:
            unmapped.append(team["displayName"])
            continue
        payload = _fetch_json(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/teams/{team['id']}/roster")
        for athlete in payload.get("athletes", []):
            position = _position(athlete)
            if position is None:
                skipped.append(f"{team['displayName']}: {athlete.get('displayName', '?')} (no recognised position)")
                continue
            rows.append({"team": canonical, "player_name": athlete["displayName"], "position": position,
                         "source": "espn_public_roster", "source_team": team["displayName"],
                         "source_player_id": athlete.get("id", "")})
    if unmapped:
        raise RuntimeError(f"Refusing partial roster import; unmapped teams: {', '.join(unmapped)}")
    if not rows:
        raise RuntimeError("ESPN returned no recognised player rows")
    if dry_run:
        print(f"{league}: {len(rows)} players across {len(set(r['team'] for r in rows))} model teams; {len(skipped)} skipped")
        return rows
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    data_dir = load_league(league).data_dir / "player_layer"
    data_dir.mkdir(parents=True, exist_ok=True)
    archive = data_dir / f"roster_espn_{timestamp}.csv"
    with archive.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)
    store = AvailabilityStore.for_league(league)
    for row in rows:
        store.add_player(row["team"], row["player_name"], row["position"])
    print(f"{league}: imported {len(rows)} players across {len(set(r['team'] for r in rows))} teams")
    print(f"Archived roster source: {archive}")
    if skipped:
        print(f"Skipped {len(skipped)} unclassified players; review first: {skipped[0]}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch current public ESPN football rosters")
    parser.add_argument("--league", required=True, choices=sorted(ESPN_SLUG))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    fetch_rosters(args.league, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
