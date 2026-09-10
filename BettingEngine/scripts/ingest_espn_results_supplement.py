#!/usr/bin/env python3
"""Fill a football-data.co.uk publication lag with completed ESPN results.

football-data publishes E0/E1 in batches. A midweek round that has already been
played can therefore be absent from the matches CSV for days, which silently
(a) drops a full round from the D-C fit and Elo, and (b) makes `get_rest_days`
report the previous weekend, so a 3-day turnaround is priced as a 7-day one.

This writes only the match facts the engine reads (goals, result, referee,
shots, shots on target, corners, fouls, cards). Odds columns are left empty --
they feed backtests/CLV, not `price_match`. Rows are marked `SourceSupp=espn`.

`fetch_results.py --live-merge` de-duplicates on (Date, HomeTeam, AwayTeam) with
keep="last", so the official rows replace these as soon as they are published.

Usage:
    python scripts/ingest_espn_results_supplement.py --league championship \
        --start 2026-09-08 --end 2026-09-09            # preview
    ... --apply                                        # write (backs up first)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.football.league_config import load_league  # noqa: E402
from ml.football.player_layer.backfill_espn_player_stats import ALIASES  # noqa: E402

ESPN_LEAGUE = {"championship": "eng.2", "epl": "eng.1", "league1": "eng.3"}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}
# ESPN team stat name -> (home column, away column)
STAT_COLS = {
    "totalShots": ("HS", "AS"),
    "shotsOnTarget": ("HST", "AST"),
    "wonCorners": ("HC", "AC"),
    "foulsCommitted": ("HF", "AF"),
    "yellowCards": ("HY", "AY"),
    "redCards": ("HR", "AR"),
}


def fetch(url: str) -> dict:
    with urlopen(Request(url, headers=HEADERS), timeout=30) as resp:
        return json.loads(resp.read())


def fd_referee(full_name: str | None) -> str:
    """'Tim Robinson' -> 'T Robinson' (football-data.co.uk convention)."""
    if not full_name:
        return ""
    parts = full_name.split()
    return f"{parts[0][0]} {' '.join(parts[1:])}" if len(parts) > 1 else full_name


def season_label(date: pd.Timestamp) -> str:
    year = date.year if date.month >= 7 else date.year - 1
    return f"{year}/{str(year + 1)[-2:]}"


def parse_event(payload: dict) -> dict | None:
    comp = payload["header"]["competitions"][0]
    if not comp.get("status", {}).get("type", {}).get("completed"):
        return None
    sides = {c["homeAway"]: c for c in comp["competitors"]}
    if not {"home", "away"} <= sides.keys():
        return None

    date = pd.Timestamp(comp["date"]).tz_convert(timezone.utc)
    home = ALIASES.get(sides["home"]["team"]["displayName"], sides["home"]["team"]["displayName"])
    away = ALIASES.get(sides["away"]["team"]["displayName"], sides["away"]["team"]["displayName"])
    fthg, ftag = int(sides["home"]["score"]), int(sides["away"]["score"])

    row = {
        "Season": season_label(date),
        "Date": date.date().isoformat(),
        "Time": date.strftime("%H:%M"),
        "HomeTeam": home,
        "AwayTeam": away,
        "FTHG": float(fthg),
        "FTAG": float(ftag),
        "FTR": "H" if fthg > ftag else ("A" if ftag > fthg else "D"),
        "Referee": fd_referee(next(
            (o.get("fullName") for o in payload.get("gameInfo", {}).get("officials", [])
             if o.get("position", {}).get("name") == "Referee"), None)),
        "SourceSupp": "espn",
    }

    by_side = {}
    for team in payload.get("boxscore", {}).get("teams", []):
        name = ALIASES.get(team["team"]["displayName"], team["team"]["displayName"])
        side = "home" if name == home else "away"
        by_side[side] = {s.get("name"): s.get("displayValue") for s in team.get("statistics", [])}
    for stat, (hcol, acol) in STAT_COLS.items():
        for side, col in (("home", hcol), ("away", acol)):
            raw = by_side.get(side, {}).get(stat)
            row[col] = float(raw) if raw not in (None, "") else None
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", default="championship")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD inclusive")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD inclusive")
    ap.add_argument("--apply", action="store_true", help="write the CSV (default: preview only)")
    args = ap.parse_args()

    cfg = load_league(args.league)
    code = ESPN_LEAGUE[args.league]
    dates = f"{args.start.replace('-', '')}-{args.end.replace('-', '')}"
    board = fetch(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}"
                  f"/scoreboard?dates={dates}&limit=100")

    rows = []
    for event in board.get("events", []):
        payload = fetch(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}"
                        f"/summary?event={event['id']}")
        row = parse_event(payload)
        if row:
            rows.append(row)
    if not rows:
        print("No completed matches in range.")
        return

    fresh = pd.DataFrame(rows)
    existing = pd.read_csv(cfg.matches_csv, low_memory=False)
    key = ["Date", "HomeTeam", "AwayTeam"]
    held = set(map(tuple, existing[key].astype(str).values))
    fresh["_new"] = [tuple(map(str, t)) not in held for t in fresh[key].values]

    print(f"ESPN completed matches {args.start}..{args.end}: {len(fresh)}")
    for _, r in fresh.iterrows():
        mark = "NEW " if r["_new"] else "have"
        print(f"  {mark} {r.Date} {r.HomeTeam:<20} {r.FTHG:.0f}-{r.FTAG:.0f} "
              f"{r.AwayTeam:<20} ref={r.Referee or '-'}")

    add = fresh[fresh["_new"]].drop(columns="_new")
    if add.empty:
        print("\nNothing to add — matches CSV is already current.")
        return
    if not args.apply:
        print(f"\n{len(add)} row(s) would be added. Re-run with --apply to write.")
        return

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup = cfg.matches_csv.with_suffix(f".backup-{stamp}.csv")
    shutil.copy2(cfg.matches_csv, backup)

    combined = pd.concat([existing, add], ignore_index=True, sort=False)
    combined = combined.sort_values(["Date", "HomeTeam", "AwayTeam"]).reset_index(drop=True)
    combined.to_csv(cfg.matches_csv, index=False)
    print(f"\nBackup   {backup.name}")
    print(f"Added    {len(add)} rows -> {len(existing)} to {len(combined)}")


if __name__ == "__main__":
    main()
