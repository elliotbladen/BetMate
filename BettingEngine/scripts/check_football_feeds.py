#!/usr/bin/env python3
"""Report which football model inputs are actually fresh — by content, not mtime.

Every input the pricer reads is checked for the latest date INSIDE the file.
File modification time is deliberately ignored: a checkout, a copy or a rewrite
touches mtime without adding a single row, and a feed that silently stopped
updating keeps a recent mtime forever. The only honest question is "what is the
newest event this file knows about".

Written 2026-09-14 after GW7 was priced with a pressing feed 4 weeks stale, a
referee table a full season behind, and a new-team prior file that had never
existed — none of which produced a warning anywhere in the run.

Usage:
    python scripts/check_football_feeds.py --league championship
    python scripts/check_football_feeds.py --league championship --json

Exit code is 1 if any feed is STALE or MISSING, so this can gate a pricing run.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.football.league_config import load_league  # noqa: E402


@dataclass
class Feed:
    name: str
    rel_path: str
    date_col: str | None
    max_age_days: int
    feeds: str                 # what in the model consumes it
    breaks: str                # what goes wrong when it is stale
    season_col: str | None = None


FEEDS: dict[str, list[Feed]] = {
    "championship": [
        Feed("matches", "matches/championship_matches.csv", "Date", 10,
             "D-C ratings + Elo (the whole spine)",
             "ratings miss a round; rest-days wrong for every club"),
        Feed("ppda (T2)", "style/ppda_dated.csv", "date", 21,
             "T2 pressing matchup",
             "T2 fires on a stale pressing figure; get_ppda has no recency guard"),
        Feed("clubelo (T8)", "clubelo/season_ratings.csv", None, 400,
             "T8 prior for clubs new to the division",
             "falls back to the hardcoded new_team_elo_priors guess",
             season_col="season"),
        Feed("referees (T6)", "refs/refs_matches.csv", "Date", 400,
             "T6 referee goals/cards profile",
             "referee tendencies are built from an out-of-date sample"),
        Feed("player stats", "player_layer/player_match_stats_espn_2026.csv", "kickoff", 14,
             "shadow model starting XI",
             "shadow prices run on old teamsheets"),
    ],
}


def current_season(today: datetime) -> str:
    year = today.year if today.month >= 7 else today.year - 1
    return f"{year}/{str(year + 1)[-2:]}"


def check(feed: Feed, data_dir: Path, today: datetime) -> dict:
    path = data_dir / feed.rel_path
    row = {"feed": feed.name, "path": feed.rel_path, "feeds": feed.feeds,
           "breaks": feed.breaks, "latest": None, "age_days": None,
           "rows": None, "status": "OK", "detail": ""}
    if not path.exists():
        row["status"] = "MISSING"
        row["detail"] = "file does not exist"
        return row
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as exc:                                   # noqa: BLE001
        row["status"] = "UNREADABLE"
        row["detail"] = str(exc)[:120]
        return row
    row["rows"] = len(df)
    if df.empty:
        row["status"] = "MISSING"
        row["detail"] = "file is empty"
        return row

    if feed.season_col and feed.season_col in df.columns:
        seasons = sorted(str(s) for s in df[feed.season_col].dropna().unique())
        want = current_season(today)
        row["detail"] = f"seasons {seasons[-2:]}"
        if want not in seasons:
            row["status"] = "STALE"
            row["detail"] = f"no {want} rows (has {seasons[-2:]})"
        return row

    if not feed.date_col or feed.date_col not in df.columns:
        row["status"] = "UNREADABLE"
        row["detail"] = f"no '{feed.date_col}' column; cannot date this feed"
        return row

    dates = pd.to_datetime(df[feed.date_col], errors="coerce", format="mixed", utc=True)
    if not dates.notna().any():
        row["status"] = "UNREADABLE"
        row["detail"] = f"'{feed.date_col}' parsed to no valid dates"
        return row
    latest = dates.max().tz_convert(None) if dates.max().tzinfo else dates.max()
    age = (today - latest.to_pydatetime().replace(tzinfo=None)).days
    row["latest"] = latest.date().isoformat()
    row["age_days"] = age
    if age > feed.max_age_days:
        row["status"] = "STALE"
        row["detail"] = f"{age}d old, limit {feed.max_age_days}d"
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", default="championship", choices=sorted(FEEDS))
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument("--as-of", default=None, help="override today (YYYY-MM-DD), for testing")
    args = ap.parse_args()

    today = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now()
    cfg = load_league(args.league)
    rows = [check(f, cfg.data_dir, today) for f in FEEDS[args.league]]
    bad = [r for r in rows if r["status"] != "OK"]

    if args.json:
        print(json.dumps({"league": args.league, "as_of": today.date().isoformat(),
                          "feeds": rows, "failing": len(bad)}, indent=2))
        return 1 if bad else 0

    print(f"\nFeed health — {cfg.name}, as of {today.date()}")
    print("=" * 78)
    print(f"{'feed':<16}{'status':<11}{'latest':<12}{'age':>6}  {'rows':>7}  detail")
    print("-" * 78)
    for r in rows:
        age = f"{r['age_days']}d" if r["age_days"] is not None else "-"
        print(f"{r['feed']:<16}{r['status']:<11}{str(r['latest'] or '-'):<12}"
              f"{age:>6}  {str(r['rows'] or '-'):>7}  {r['detail']}")
    if bad:
        print("\nWhat this costs:")
        for r in bad:
            print(f"  [{r['status']}] {r['feed']} -> {r['feeds']}")
            print(f"        {r['breaks']}")
        print(f"\n{len(bad)} of {len(rows)} feeds are not fresh.")
    else:
        print("\nAll feeds fresh.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
