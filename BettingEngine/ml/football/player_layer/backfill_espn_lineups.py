#!/usr/bin/env python3
"""Backfill one Championship season of official starters for ML training."""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.2"
OUT = Path(__file__).resolve().parents[1] / "data" / "championship" / "player_layer"


def fetch(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36",
                                "Accept": "application/json,text/plain,*/*"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def event_ids(season: int) -> set[str]:
    teams = fetch(f"{BASE}/teams")["sports"][0]["leagues"][0]["teams"]
    ids = set()
    for item in teams:
        team_id = item["team"]["id"]
        schedule = fetch(f"{BASE}/teams/{team_id}/schedule?season={season}")
        ids.update(str(event["id"]) for event in schedule.get("events", []))
    return ids


def parse(event_id: str) -> list[dict]:
    payload = fetch(f"{BASE}/summary?event={event_id}")
    header = payload.get("header", {}).get("competitions", [{}])[0]
    competitors = {c.get("homeAway"): c for c in header.get("competitors", [])}
    if not {"home", "away"}.issubset(competitors):
        return []
    home, away = competitors["home"], competitors["away"]
    common = {"event_id": event_id, "kickoff": header.get("date"),
              "home_team": home["team"]["displayName"], "away_team": away["team"]["displayName"],
              "home_goals": home.get("score"), "away_goals": away.get("score")}
    rows = []
    for roster in payload.get("rosters", []):
        team = roster.get("team", {}).get("displayName")
        side = roster.get("homeAway")
        for player in roster.get("roster", []):
            if not player.get("starter"):
                continue
            rows.append({**common, "team": team, "side": side,
                         "player_id": player.get("athlete", {}).get("id"),
                         "player_name": player.get("athlete", {}).get("displayName"),
                         "position": player.get("position", {}).get("abbreviation")})
    return rows if len(rows) == 22 else []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2025)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    ids = sorted(event_ids(args.season))
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(parse, event_id): event_id for event_id in ids}
        for i, future in enumerate(as_completed(futures), 1):
            try: rows.extend(future.result())
            except Exception as exc: print(f"{futures[future]} failed: {exc}")
            if i % 50 == 0: print(f"Processed {i}/{len(ids)}")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"historical_starters_espn_{args.season}.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"Saved {len(rows)} starter rows across {len(set(r['event_id'] for r in rows))} matches to {path}")


if __name__ == "__main__":
    main()
