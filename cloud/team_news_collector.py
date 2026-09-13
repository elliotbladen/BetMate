#!/usr/bin/env python3
"""Snapshot injuries and team sheets for EPL, EFL, UCL and NFL, into Supabase.

Designed for a cloud cron invoking it every five minutes, exactly like
odds_collector.py, and it deliberately reuses that module's Supabase client so the
two share one set of hard-won behaviours: stable paged reads, on_conflict inserts
that genuinely ignore duplicates, and errors that carry PostgREST's body.

WHEN IT CAPTURES, and why those times and not others:

  T-72h / T-48h / T-24h   injuries. The owner wants the 1/2/3 days out picture, and
                          the unavailable list is populated that far ahead even
                          though the XI is not.

  T-80m and T-70m         football team sheets. Premier League, EFL and UEFA all
                          require submission 75 MINUTES before kick-off (the Premier
                          League moved from 60 to align with UEFA). Capturing either
                          side of that line is what turns a team sheet into a
                          measurable event: the before shot is the market's guess,
                          the after shot is the fact.

  T-95m and T-85m         NFL inactives. The league mandates release exactly 90
                          MINUTES before kickoff, standardised across all 32 clubs -
                          a harder deadline than football's, so a tighter bracket.

⚠️ THE TWO-SIDED BRACKET IS THE POINT. One snapshot after publication tells you who
   is out. Two, straddling the deadline, tell you what the market did WHEN IT FOUND
   OUT - which is the entire reason this data is being collected.

⚠️ RATINGS ARE STAMPED AT CAPTURE TIME AND NEVER RECOMPUTED. Each absence carries
   the player's star rating AS IT STOOD THAT DAY, read from the newest dated file in
   data/player_importance. A player who breaks out in March must not retroactively
   become a star in an October injury being studied.

Live writes require ODDS_COLLECTION_LIVE_ENABLED=true plus Supabase credentials -
the same switch as the odds collector, so one flag controls all cloud collection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "sources"))

from odds_collector import Supabase, truthy, iso, utcnow          # noqa: E402
import fotmob                                                      # noqa: E402

UTC = timezone.utc

# Minutes before kickoff at which a capture is wanted, per code.
WINDOWS = {
    "football": [72 * 60, 48 * 60, 24 * 60, 80, 70],
    "NFL": [72 * 60, 48 * 60, 24 * 60, 95, 85],
}
# How close to a target counts as hitting it. Five minutes matches the cron period;
# anything tighter and a window is missed entirely on a slow cycle.
TOLERANCE_MINUTES = 5

RATING_DIR = Path("data/player_importance")


def window_name(minutes: int) -> str:
    if minutes >= 60:
        return f"t_minus_{minutes // 60}h"
    return f"t_minus_{minutes}m"


def due_window(minutes_to_kickoff: int, code_kind: str) -> str | None:
    for target in WINDOWS[code_kind]:
        if abs(minutes_to_kickoff - target) <= TOLERANCE_MINUTES:
            return window_name(target)
    return None


def load_ratings() -> tuple[dict[str, dict], str | None]:
    """Newest dated rating file -> {lowercased player name: row}.

    Matched on name because the rating source (FotMob squads) and the capture source
    share ids for football but not for NFL, and a name match that occasionally misses
    is better than a rating silently attached to the wrong player.
    """
    if not RATING_DIR.exists():
        return {}, None
    files = sorted(RATING_DIR.glob("football_stars_all_*.json")) or \
            sorted(RATING_DIR.glob("football_stars_*.json"))
    nfl = sorted(RATING_DIR.glob("nfl_importance_*.json"))
    out: dict[str, dict] = {}
    newest = None
    for path in (files[-1:] + nfl[-1:]):
        newest = max(newest or path.name, path.name)
        for row in json.loads(path.read_text(encoding="utf-8")):
            name = (row.get("player") or "").strip().lower()
            if name:
                out[name] = row
    return out, newest


def fingerprint(*parts) -> str:
    return hashlib.sha256("|".join("" if p is None else str(p) for p in parts)
                          .encode()).hexdigest()


def collect_football(db: Supabase | None, run_id: str, ratings: dict) -> dict:
    now = utcnow()
    sheets, absences = [], []
    fixtures = fotmob.upcoming(days_ahead=4)
    for fixture in fixtures:
        kickoff = fixture.get("kickoff_utc")
        if not kickoff:
            continue
        ko = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
        minutes = int((ko - now).total_seconds() / 60)
        window = due_window(minutes, "football")
        if not window:
            continue
        for sheet in fotmob.team_sheets(fixture):
            starters = [{"id": p.source_player_id, "name": p.name,
                         "shirt": p.shirt_number, "pos": p.position}
                        for p in sheet.starters]
            sheets.append({
                "run_id": run_id, "captured_at": iso(now), "code": sheet.code,
                "source": "fotmob", "source_match_id": sheet.source_match_id,
                "kickoff_utc": sheet.kickoff_utc, "minutes_to_kickoff": minutes,
                "home_team": sheet.home_team, "away_team": sheet.away_team,
                "side": sheet.side, "team_name": sheet.team_name,
                "lineup_type": sheet.lineup_type, "formation": sheet.formation,
                "starters": starters,
                "value_fingerprint": fingerprint(sheet.lineup_type, sheet.formation,
                                                 *[p.source_player_id for p in sheet.starters]),
            })
            for absence in sheet.unavailable:
                rating = ratings.get((absence.name or "").strip().lower()) or {}
                absences.append({
                    "run_id": run_id, "captured_at": iso(now), "code": sheet.code,
                    "source": "fotmob", "source_match_id": sheet.source_match_id,
                    "kickoff_utc": sheet.kickoff_utc, "minutes_to_kickoff": minutes,
                    "team_name": sheet.team_name, "player_name": absence.name,
                    "source_player_id": absence.source_player_id,
                    "position": rating.get("position_group"),
                    "reason_type": absence.reason_type,
                    "reason_detail": absence.reason_detail,
                    "expected_return_raw": absence.expected_return,
                    # Stamped as it stands TODAY, never recomputed later.
                    "star_rating": rating.get("stars"),
                    "rating_as_of": rating.get("rated_on"),
                    "value_fingerprint": fingerprint(absence.reason_type,
                                                     absence.expected_return, window),
                })
    return {"sheets": sheets, "absences": absences, "fixtures": len(fixtures)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="capture every upcoming fixture, ignoring the windows")
    args = parser.parse_args()

    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    live = not args.dry_run and truthy(os.getenv("ODDS_COLLECTION_LIVE_ENABLED"))
    worker = os.getenv("TEAM_NEWS_WORKER_ID", socket.gethostname())

    ratings, rating_file = load_ratings()
    print(f"team-news collector start worker={worker} live={live} "
          f"ratings={len(ratings)} from {rating_file or 'NONE'}")

    if args.force:
        for code_kind in WINDOWS:
            WINDOWS[code_kind] = list(range(0, 4 * 24 * 60, 5))

    db = Supabase(url, key) if (live and url and key) else None
    run_id = str(uuid.uuid4())
    if db:
        db.insert("team_news_capture_runs", [{
            "run_id": run_id, "started_at": iso(utcnow()), "worker_id": worker,
            "status": "running", "codes_requested": ["EPL", "EFL", "UCL"],
        }])

    result = collect_football(db, run_id, ratings)
    sheets, absences = result["sheets"], result["absences"]
    print(f"  {result['fixtures']} fixtures scanned -> {len(sheets)} team sheets, "
          f"{len(absences)} availability rows")
    for s in sheets[:6]:
        print(f"    {s['code']:<4} T-{s['minutes_to_kickoff']:>5}m {s['lineup_type']:<14} "
              f"{s['team_name']}")
    rated = sum(1 for a in absences if a.get("star_rating"))
    if absences:
        print(f"    {rated}/{len(absences)} absences matched to a star rating")

    if db:
        db.insert("team_sheet_observations", sheets, ignore_duplicates=True,
                  on_conflict="source_match_id,side,value_fingerprint")
        db.insert("player_availability_observations", absences, ignore_duplicates=True,
                  on_conflict="code,team_name,player_name,source_match_id,value_fingerprint")
        status = "success" if (sheets or absences) else "skipped"
        import requests
        requests.patch(f"{db.base}/team_news_capture_runs",
                       headers={**db.headers, "Prefer": "return=minimal"},
                       params={"run_id": f"eq.{run_id}"},
                       data=json.dumps({"finished_at": iso(utcnow()), "status": status,
                                        "codes_fetched": ["EPL", "EFL", "UCL"],
                                        "fixtures_seen": result["fixtures"],
                                        "sheets_written": len(sheets),
                                        "availability_written": len(absences)}),
                       timeout=30)
    # Always exit 0: this runs as a cron, and a non-zero exit makes the platform
    # restart and eventually stop scheduling it. One sport's failure must not take
    # the scheduler down - the lesson from the odds collector's 11-hour outage.
    return 0


if __name__ == "__main__":
    sys.exit(main())
