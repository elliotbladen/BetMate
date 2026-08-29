#!/usr/bin/env python3
"""Archive Championship fixtures and freeze official-XI player snapshots."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from .availability import AvailabilityStore
from ml.football.fetch.fetch_espn_rosters import TEAM_ALIASES

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.2"
OUT = Path(__file__).resolve().parents[1] / "data" / "championship" / "player_layer" / "match_feeds"


def fetch(url: str) -> dict:
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
    })
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def canon(name: str) -> str:
    return TEAM_ALIASES.get(name, name)


def roster_names(payload: dict, side: str) -> list[str]:
    for roster in payload.get("rosters", []):
        if roster.get("homeAway") == side:
            return [row["athlete"]["displayName"] for row in roster.get("roster", []) if row.get("starter")]
    return []


def already_frozen(store: AvailabilityStore, home: str, away: str, kickoff: str) -> bool:
    store.initialise()
    with store._connect() as conn:
        return conn.execute(
            "SELECT 1 FROM match_snapshots WHERE league=? AND home_team=? AND away_team=? AND kickoff_at=? AND stage='final' LIMIT 1",
            (store.league, home, away, kickoff),
        ).fetchone() is not None


def collect(day: str) -> list[dict]:
    board = fetch(f"{BASE}/scoreboard?dates={day.replace('-', '')}")
    store = AvailabilityStore.for_league("championship")
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for event in board.get("events", []):
        event_id = event["id"]
        summary = fetch(f"{BASE}/summary?event={event_id}")
        (OUT / f"{event_id}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        competition = event["competitions"][0]
        sides = {c["homeAway"]: c for c in competition["competitors"]}
        home, away = canon(sides["home"]["team"]["displayName"]), canon(sides["away"]["team"]["displayName"])
        home_xi, away_xi = roster_names(summary, "home"), roster_names(summary, "away")
        status = "WAITING_FOR_OFFICIAL_XI"
        snapshot_id = None
        if already_frozen(store, home, away, event["date"]):
            status = "FINAL_XI_ALREADY_FROZEN"
        elif len(home_xi) == 11 and len(away_xi) == 11:
            cutoff = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            try:
                snapshot_id = store.create_snapshot(home_team=home, away_team=away,
                    kickoff_at=event["date"], cutoff_at=cutoff, stage="final",
                    confirmed_home=home_xi, confirmed_away=away_xi)
                status = "FINAL_XI_FROZEN"
            except (ValueError, sqlite3.IntegrityError) as exc:
                status = f"NOT_FROZEN:{exc}"
        results.append({"event_id": event_id, "home": home, "away": away,
                        "kickoff": event["date"], "status": status, "snapshot_id": snapshot_id})
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    args = ap.parse_args()
    results = collect(args.date)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
