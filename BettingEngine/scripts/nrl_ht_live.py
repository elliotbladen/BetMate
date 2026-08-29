#!/usr/bin/env python3
"""
scripts/nrl_ht_live.py

NRL halftime live stats scraper — no login, no browser required.
Polls NRL.com during the first half, captures 10/20/30/HT checkpoints,
then runs the pricing model at halftime.

Usage:
    uv run python scripts/nrl_ht_live.py --round 15
    uv run python scripts/nrl_ht_live.py --round 15 --season 2026
    uv run python scripts/nrl_ht_live.py --round 15 --home Warriors --away Sharks
    uv run python scripts/nrl_ht_live.py --round 15 --force   # skip halftime check (testing)
"""

from __future__ import annotations

import argparse
import json
import os
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
SNAPSHOT_SECONDS = (600, 1200, 1800, 2400)

# ── Odds API ─────────────────────────────────────────────────────────────────
ENV_PATH       = _ROOT.parent / ".env.local"
ODDS_EVENTS_URL = "https://api.the-odds-api.com/v4/sports/{sport_key}/events"
ODDS_EVENT_ODDS = "https://api.the-odds-api.com/v4/sports/{sport_key}/events/{event_id}/odds"
ODDS_SPORT_KEY  = "rugbyleague_nrl"
ODDS_LIVE_MARKETS = "h2h,spreads,totals"


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
    # The draw feed can jump directly FirstHalf -> SecondHalf while reporting
    # gameSeconds=0. Treat the first SecondHalf observation as the HT fallback.
    if state.replace(" ", "") == "secondhalf":
        return True
    # Live game that has hit 40 mins
    if game_secs >= FIRST_HALF_END and "live" in state:
        return True
    return False


def is_live(fixture: dict) -> bool:
    state = (fixture.get("matchState") or "").lower()
    return any(token in state for token in ("live", "firsthalf", "first half", "secondhalf", "second half", "halftime", "half time")) or is_halftime(fixture)


def fixture_label(f: dict) -> str:
    h = f.get("homeTeam", {}).get("nickName", "?")
    a = f.get("awayTeam", {}).get("nickName", "?")
    return f"{h} vs {a}"


def match_centre_url(fixture: dict) -> str:
    return NRL_BASE + fixture.get("matchCentreUrl", "").rstrip("/")


def _first_half_cache_path(round_num: int, fixture: dict) -> Path:
    home = fixture.get("homeTeam", {}).get("nickName", "home").lower().replace(" ", "_")
    away = fixture.get("awayTeam", {}).get("nickName", "away").lower().replace(" ", "_")
    return HALFTIME_DIR / f"R{round_num:02d}" / "state" / f"{home}_vs_{away}_latest_first_half.json"


def save_first_half_cache(round_num: int, fixture: dict, data: dict, observed: int) -> None:
    path = _first_half_cache_path(round_num, fixture)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"observed": observed, "data": data}), encoding="utf-8")
    temporary.replace(path)


def load_first_half_cache(round_num: int, fixture: dict) -> tuple[dict | None, int]:
    try:
        payload = json.loads(_first_half_cache_path(round_num, fixture).read_text(encoding="utf-8"))
        return payload.get("data"), int(payload.get("observed") or 0)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None, 0


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


def get_first_stat(groups: list[dict], *titles: str) -> tuple[float, float] | None:
    for title in titles:
        value = get_stat(groups, title)
        if value is not None:
            return value
    return None


def _pair(groups: list[dict], *titles: str) -> tuple[float | None, float | None]:
    value = get_first_stat(groups, *titles)
    return value if value is not None else (None, None)


def count_timeline_events(timeline: list[dict], event_type: str, team_id: int, max_seconds: int = FIRST_HALF_END) -> int:
    """Count timeline events of a given type for a team in the first half."""
    return sum(
        1 for e in timeline
        if str(e.get("type") or "").lower().replace(" ", "") == event_type.lower().replace(" ", "")
        and e.get("teamId") == team_id
        and (e.get("gameSeconds") or 0) <= max_seconds
    )


def count_first_half_conversions(timeline: list[dict], team_id: int, max_seconds: int = FIRST_HALF_END) -> int:
    """Count conversions while excluding penalty goals also labelled `Goal`."""
    tries = sorted(
        float(e.get("gameSeconds") or 0)
        for e in timeline
        if e.get("type") == "Try" and e.get("teamId") == team_id
        and float(e.get("gameSeconds") or 0) <= max_seconds
    )
    goals = sorted(
        float(e.get("gameSeconds") or 0)
        for e in timeline
        if e.get("type") == "Goal" and e.get("teamId") == team_id
        and float(e.get("gameSeconds") or 0) <= max_seconds
    )
    used: set[int] = set()
    conversions = 0
    for try_second in tries:
        for index, goal_second in enumerate(goals):
            if index not in used and 0 < goal_second - try_second <= 150:
                used.add(index)
                conversions += 1
                break
    return conversions


# ── In-game injury & sin-bin extraction ──────────────────────────────────────

_INJURY_KEYWORDS = ("hia", "injur", "no return", "medicab", "concus")
_SINBIN_KEYWORDS = ("sin bin", "sinbin", "sent off", "send off", "sent-off",
                     "send-off", "red card", "on report")


def _extract_ingame_injuries(data: dict, home_id: int, away_id: int, max_seconds: int = FIRST_HALF_END) -> list[dict]:
    """Scan interchange timeline events for HIA / injury flags.

    Returns a list of dicts with player name, position, team side, minute, and
    the raw interchange title so the pricing model can apply T5 impact.
    """
    timeline = data.get("timeline", [])

    # Build player ID → info lookup from both rosters
    players: dict[int, dict] = {}
    for side, team_key in [("home", "homeTeam"), ("away", "awayTeam")]:
        team = data.get(team_key, {})
        team_id = team.get("teamId")
        for p in team.get("players", []):
            pid = p.get("playerId")
            if pid:
                players[pid] = {
                    "name": f"{p.get('firstName', '')} {p.get('lastName', '')}".strip(),
                    "position": p.get("position", "Unknown"),
                    "number": p.get("number"),
                    "side": "home" if team_id == home_id else "away",
                }

    injuries: list[dict] = []
    for event in timeline:
        if event.get("type") != "Interchange":
            continue
        if (event.get("gameSeconds") or 0) > max_seconds:
            continue
        title = (event.get("title") or "").lower()
        if not any(kw in title for kw in _INJURY_KEYWORDS):
            continue

        off_pid = event.get("offPlayerId")
        player = players.get(off_pid, {})
        game_secs = event.get("gameSeconds", 0)
        injuries.append({
            "name": player.get("name", f"PID:{off_pid}"),
            "position": player.get("position", "Unknown"),
            "number": player.get("number"),
            "side": player.get("side", "unknown"),
            "minute": round(game_secs / 60),
            "title": event.get("title", ""),
            "source": "nrl_api",
        })

    return injuries


def _extract_sin_bins(data: dict, home_id: int, away_id: int, max_seconds: int = FIRST_HALF_END) -> list[dict]:
    """Detect sin bin / send-off events from Penalty timeline events.

    Sin bins = 10min down to 12 players. Send-offs = permanent.
    These are NOT injuries but materially affect H2 pricing.
    """
    timeline = data.get("timeline", [])
    players: dict[int, dict] = {}
    for side, team_key in [("home", "homeTeam"), ("away", "awayTeam")]:
        team = data.get(team_key, {})
        team_id = team.get("teamId")
        for p in team.get("players", []):
            pid = p.get("playerId")
            if pid:
                players[pid] = {
                    "name": f"{p.get('firstName', '')} {p.get('lastName', '')}".strip(),
                    "position": p.get("position", "Unknown"),
                    "number": p.get("number"),
                    "side": "home" if team_id == home_id else "away",
                }

    events: list[dict] = []
    for event in timeline:
        if event.get("type") != "Penalty":
            continue
        if (event.get("gameSeconds") or 0) > max_seconds:
            continue
        title = (event.get("title") or "").lower()
        if not any(kw in title for kw in _SINBIN_KEYWORDS):
            continue
        pid = event.get("playerId")
        player = players.get(pid, {})
        game_secs = event.get("gameSeconds", 0)
        is_sendoff = any(kw in title for kw in ("sent off", "send off", "sent-off",
                                                  "send-off", "red card"))
        events.append({
            "name": player.get("name", f"PID:{pid}"),
            "position": player.get("position", "Unknown"),
            "number": player.get("number"),
            "side": player.get("side", "unknown"),
            "minute": round(game_secs / 60),
            "title": event.get("title", ""),
            "type": "send_off" if is_sendoff else "sin_bin",
        })
    return events


def _load_manual_injuries(round_num: int) -> list[dict]:
    """Load manual injury overrides from a drop-file.

    The user can create a file at:
        data/nrl/halfTime/R{round}/manual_injuries.json

    Format: list of dicts with keys: name, position, side (home/away), minute, title
    Example:
        [{"name": "Kalyn Ponga", "position": "Fullback", "side": "home",
          "minute": 25, "title": "Suspected knee injury (manual override)"}]

    This is the backup for when the NRL API doesn't flag an injury that the
    user spots while watching the game or from social media.
    """
    manual_path = HALFTIME_DIR / f"R{round_num:02d}" / "manual_injuries.json"
    if not manual_path.exists():
        return []
    try:
        raw = json.loads(manual_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        result = []
        for entry in raw:
            result.append({
                "name": entry.get("name", "Unknown"),
                "position": entry.get("position", "Unknown"),
                "number": entry.get("number"),
                "side": entry.get("side", "unknown"),
                "minute": entry.get("minute", 0),
                "title": entry.get("title", "Manual override"),
                "source": "manual",
            })
        print(f"  Manual injuries loaded: {len(result)} entries from {manual_path}")
        return result
    except Exception as exc:
        print(f"  WARNING: Failed to read manual injuries: {exc}")
        return []


def extract_halftime_stats(data: dict, season: int, round_num: int, snapshot_second: int = FIRST_HALF_END) -> dict:
    """Extract cumulative first-half stats, preserving unavailable fields as None."""
    home = data.get("homeTeam", {})
    away = data.get("awayTeam", {})
    home_id = home.get("teamId")
    away_id = away.get("teamId")

    home_scoring = home.get("scoring") or {}
    away_scoring = away.get("scoring") or {}

    # HT scores
    def current_score(team: dict, scoring: dict) -> int:
        values = ((scoring.get("halfTimeScore"),) if snapshot_second >= FIRST_HALF_END else ()) + (
            team.get("score"), scoring.get("score"), scoring.get("totalScore"), scoring.get("halfTimeScore")
        )
        for value in values:
            if value not in (None, ""):
                return int(float(value))
        return 0

    home_ht = current_score(home, home_scoring)
    away_ht = current_score(away, away_scoring)

    # Stats groups (at halftime these ARE the first half stats)
    groups = data.get("stats", {}).get("groups", [])

    poss = _pair(groups, "Possession %", "Possession")
    comp = _pair(groups, "Completion Rate", "Completions")
    metres = _pair(groups, "All Run Metres", "Run Metres")
    errors = _pair(groups, "Errors")
    pens = _pair(groups, "Penalties Conceded")

    # Set restarts — may be in stats groups or must be counted from timeline
    set_restarts = get_first_stat(groups, "Set Restarts", "6 Agains", "Six Agains")
    if set_restarts:
        home_restarts = int(set_restarts[0])
        away_restarts = int(set_restarts[1])
    else:
        # Count from timeline (SetRestart events = restarts RECEIVED by that team's opponent)
        timeline = data.get("timeline", [])
        # SetRestart event is conceded BY a team — meaning opponent receives an extra set
        # home_restarts_received = restarts conceded by away team
        away_restart_count = count_timeline_events(timeline, "SetRestart", away_id, snapshot_second)
        home_restart_count = count_timeline_events(timeline, "SetRestart", home_id, snapshot_second)
        # A SetRestart penalises the team that conceded it → the other team gets the restart
        home_restarts = away_restart_count   # restarts received by home = conceded by away
        away_restarts = home_restart_count

    # Tries in first half (from timeline, filtered to first half)
    timeline = data.get("timeline", [])
    home_tries_ht = count_timeline_events(timeline, "Try", home_id, snapshot_second)
    away_tries_ht = count_timeline_events(timeline, "Try", away_id, snapshot_second)

    # NRL labels conversions and penalty goals as `Goal`; only a goal following
    # a same-team try in the normal kick window is a conversion.
    home_conv_ht = count_first_half_conversions(timeline, home_id, snapshot_second)
    away_conv_ht = count_first_half_conversions(timeline, away_id, snapshot_second)

    total_sets = _pair(groups, "Total Sets", "Sets")
    all_runs = _pair(groups, "All Runs", "Runs")
    post_contact = _pair(groups, "Post Contact Metres")
    line_breaks = _pair(groups, "Line Breaks", "Linebreaks")
    tackle_breaks = _pair(groups, "Tackle Breaks")
    play_balls = _pair(groups, "Play The Ball", "Play The Balls")
    ptb_speed = _pair(groups, "Average Play The Ball Speed", "Avg Play The Ball Speed")
    missed_tackles = _pair(groups, "Missed Tackles")
    tackles = _pair(groups, "Tackles Made")
    kick_metres = _pair(groups, "Kick Metres", "Kicking Metres")
    forced_dropouts = _pair(groups, "Forced Drop Outs", "Forced Dropouts")
    line_dropouts = (
        count_timeline_events(timeline, "LineDropout", home_id, snapshot_second),
        count_timeline_events(timeline, "LineDropout", away_id, snapshot_second),
    )
    interchanges = (
        count_timeline_events(timeline, "Interchange", home_id, snapshot_second),
        count_timeline_events(timeline, "Interchange", away_id, snapshot_second),
    )

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
        "snapshot_game_seconds": snapshot_second,
        "snapshot_minute": round(snapshot_second / 60, 1),
        "home_ht_score": home_ht,
        "away_ht_score": away_ht,
        "home_tries": home_tries_ht,
        "away_tries": away_tries_ht,
        "home_conversions_made": home_conv_ht,
        "away_conversions_made": away_conv_ht,
        "home_errors": errors[0],
        "away_errors": errors[1],
        "home_set_restarts_received": home_restarts,
        "away_set_restarts_received": away_restarts,
        "home_run_metres": metres[0], "away_run_metres": metres[1],
        "home_possession_pct": poss[0], "away_possession_pct": poss[1],
        "home_completion_pct": comp[0], "away_completion_pct": comp[1],
        "home_penalties_conceded": pens[0], "away_penalties_conceded": pens[1],
        "home_total_sets": total_sets[0], "away_total_sets": total_sets[1],
        "home_all_runs": all_runs[0], "away_all_runs": all_runs[1],
        "home_post_contact_metres": post_contact[0], "away_post_contact_metres": post_contact[1],
        "home_line_breaks": line_breaks[0], "away_line_breaks": line_breaks[1],
        "home_tackle_breaks": tackle_breaks[0], "away_tackle_breaks": tackle_breaks[1],
        "home_play_the_balls": play_balls[0], "away_play_the_balls": play_balls[1],
        "home_avg_play_the_ball_speed": ptb_speed[0], "away_avg_play_the_ball_speed": ptb_speed[1],
        "home_missed_tackles": missed_tackles[0], "away_missed_tackles": missed_tackles[1],
        "home_tackles_made": tackles[0], "away_tackles_made": tackles[1],
        "home_kick_metres": kick_metres[0], "away_kick_metres": kick_metres[1],
        "home_forced_dropouts": forced_dropouts[0], "away_forced_dropouts": forced_dropouts[1],
        "home_line_dropouts": line_dropouts[0], "away_line_dropouts": line_dropouts[1],
        "home_interchanges_used": interchanges[0], "away_interchanges_used": interchanges[1],
        "home_inside_20_possessions": None,
        "away_inside_20_possessions": None,
        "ingame_injuries": _extract_ingame_injuries(data, home_id, away_id, snapshot_second),
        "sin_bins": _extract_sin_bins(data, home_id, away_id, snapshot_second),
        "manual_injuries": _load_manual_injuries(round_num),
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
    fmt = lambda value, suffix="": "n/a" if value is None else f"{value:.0f}{suffix}"
    print(f"  Possession:    {h} {fmt(stats['home_possession_pct'], '%')} / {a} {fmt(stats['away_possession_pct'], '%')}")
    print(f"  Completion:    {h} {fmt(stats['home_completion_pct'], '%')} / {a} {fmt(stats['away_completion_pct'], '%')}")
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


def save_snapshot(stats: dict, data: dict, checkpoint: int) -> tuple[Path, Path]:
    """Write normalized and raw checkpoint data without overwriting HT files."""
    round_dir = HALFTIME_DIR / f"R{stats['round']:02d}" / "snapshots"
    round_dir.mkdir(parents=True, exist_ok=True)
    home_nick = stats["home_team"].split()[-1].lower()
    away_nick = stats["away_team"].split()[-1].lower()
    stem = f"{stats['game_date']}_{home_nick}_vs_{away_nick}_{checkpoint // 60:02d}m"
    normalized_path = round_dir / f"{stem}_stats.json"
    raw_path = round_dir / f"{stem}_raw.json"
    normalized_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    raw_capture = {
        "collected_at": stats["collected_at"],
        "checkpoint_game_seconds": checkpoint,
        "observed_game_seconds": data.get("gameSeconds"),
        "homeTeam": data.get("homeTeam"),
        "awayTeam": data.get("awayTeam"),
        "stats": data.get("stats"),
        "timeline": data.get("timeline"),
        "interchanges": data.get("interchanges"),
    }
    raw_path.write_text(json.dumps(raw_capture, indent=2), encoding="utf-8")
    print(f"  Snapshot saved → {normalized_path}")
    return normalized_path, raw_path


def snapshot_exists(stats: dict, checkpoint: int) -> bool:
    round_dir = HALFTIME_DIR / f"R{stats['round']:02d}" / "snapshots"
    home_nick = stats["home_team"].split()[-1].lower()
    away_nick = stats["away_team"].split()[-1].lower()
    stem = f"{stats['game_date']}_{home_nick}_vs_{away_nick}_{checkpoint // 60:02d}m"
    return (round_dir / f"{stem}_stats.json").exists()


# ── Halftime odds capture ────────────────────────────────────────────────────

def _load_odds_api_key() -> str:
    key = os.environ.get("ODDS_API_KEY", "")
    if key:
        return key
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ODDS_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def _normalise_team(name: str) -> str:
    """Normalise a team name for matching: lowercase, strip punctuation and hyphens."""
    return name.lower().replace("-", " ").replace(".", "").replace("'", "").strip()


def _nickname(name: str) -> str:
    """Extract the last word as a nickname: 'St. George Illawarra Dragons' → 'dragons'."""
    return _normalise_team(name).split()[-1] if name.strip() else ""


def _teams_match(name_a: str, name_b: str) -> bool:
    a = _normalise_team(name_a)
    b = _normalise_team(name_b)
    if a in b or b in a:
        return True
    # Fallback: nickname match (e.g. "bulldogs" == "bulldogs")
    return _nickname(name_a) == _nickname(name_b)


def _fetch_odds_response(url: str, params: dict, label: str):
    for attempt in range(1, 4):
        try:
            response = requests.get(url, params=params, timeout=(5, 15))
            response.raise_for_status()
            return response
        except Exception as exc:
            print(f"  Odds API {label} attempt {attempt}/3 failed: {exc}")
            if attempt < 3:
                time.sleep(attempt)
    return None


# Event ID cache: once we match a game, store the ID so subsequent snapshots
# skip the /events lookup entirely. Keyed by (home_nickname, away_nickname).
_event_id_cache: dict[tuple[str, str], str] = {}


def fetch_halftime_odds(home_team: str, away_team: str) -> dict:
    """Fetch live full-game H2H, handicap, totals odds from the Odds API at halftime.

    Two API calls on first lookup:
      1. /events — get event list, match by team name (cached after first hit)
      2. /events/{id}/odds?markets=h2h,spreads,totals (live updated during play)
    """
    api_key = _load_odds_api_key()
    if not api_key:
        print("  Odds API: no API key found — skipping odds capture")
        return {}

    cache_key = (_nickname(home_team), _nickname(away_team))
    event_id = _event_id_cache.get(cache_key)

    if event_id:
        print(f"  Odds API: using cached event ID {event_id[:12]}...")
    else:
        # Step 1: find the event ID
        try:
            resp = _fetch_odds_response(
                ODDS_EVENTS_URL.format(sport_key=ODDS_SPORT_KEY),
                {"apiKey": api_key}, "events",
            )
            if resp is None:
                return {}
            events = resp.json()
            remaining = resp.headers.get("x-requests-remaining", "?")
            print(f"  Odds API: {len(events)} events, {remaining} calls remaining")
        except Exception as exc:
            print(f"  Odds API events error: {exc}")
            return {}

        matched = None
        for event in events:
            if (_teams_match(home_team, event.get("home_team", ""))
                    and _teams_match(away_team, event.get("away_team", ""))):
                matched = event
                break

        if not matched:
            # Log all available events so the name mismatch is obvious in logs
            available = [f"{e.get('home_team')} vs {e.get('away_team')}" for e in events]
            print(f"  WARNING: Odds API game not found!")
            print(f"    Searching for: \"{home_team}\" vs \"{away_team}\"")
            print(f"    Available: {available}")
            return {}

        event_id = matched["id"]
        _event_id_cache[cache_key] = event_id
        print(f"  Odds API: matched {matched['home_team']} vs {matched['away_team']} (id={event_id[:12]}...)")

    # Step 2: fetch live full-game markets for this event
    try:
        resp = _fetch_odds_response(
            ODDS_EVENT_ODDS.format(sport_key=ODDS_SPORT_KEY, event_id=event_id),
            {"apiKey": api_key, "regions": "au",
             "markets": ODDS_LIVE_MARKETS, "oddsFormat": "decimal"},
            "event odds",
        )
        if resp is None:
            return {}
        event_data = resp.json()
        remaining = resp.headers.get("x-requests-remaining", "?")
    except Exception as exc:
        print(f"  Odds API event odds error: {exc}")
        return {}

    bookmakers = {}
    for bm in event_data.get("bookmakers", []):
        bm_data = {}
        for market in bm.get("markets", []):
            mkey = market.get("key")
            outcomes = market.get("outcomes", [])
            if mkey == "h2h":
                h2h = {}
                for o in outcomes:
                    if _teams_match(home_team, o.get("name", "")):
                        h2h["home"] = o["price"]
                    elif _teams_match(away_team, o.get("name", "")):
                        h2h["away"] = o["price"]
                    elif o.get("name", "").lower() == "draw":
                        h2h["draw"] = o["price"]
                bm_data["h2h"] = h2h
            elif mkey == "spreads":
                spreads = {}
                for o in outcomes:
                    if _teams_match(home_team, o.get("name", "")):
                        spreads["home_price"] = o["price"]
                        spreads["home_point"] = o.get("point")
                    else:
                        spreads["away_price"] = o["price"]
                        spreads["away_point"] = o.get("point")
                bm_data["spreads"] = spreads
            elif mkey == "totals":
                totals = {}
                for o in outcomes:
                    if o.get("name", "").lower() == "over":
                        totals["over_price"] = o["price"]
                        totals["over_point"] = o.get("point")
                    elif o.get("name", "").lower() == "under":
                        totals["under_price"] = o["price"]
                        totals["under_point"] = o.get("point")
                bm_data["totals"] = totals
        bookmakers[bm.get("key", "unknown")] = bm_data

    print(f"  Odds API: {len(bookmakers)} bookmakers with live full-game odds")
    return {
        "odds_api_game_id": event_id,
        "odds_api_home": matched.get("home_team"),
        "odds_api_away": matched.get("away_team"),
        "commence_time": matched.get("commence_time"),
        "bookmakers": bookmakers,
    }


def save_odds(odds_data: dict, stats: dict, suffix: str = "live") -> Path | None:
    if not odds_data:
        return None
    round_dir = HALFTIME_DIR / f"R{stats['round']:02d}"
    round_dir.mkdir(parents=True, exist_ok=True)
    home_nick = stats["home_team"].split()[-1].lower()
    away_nick = stats["away_team"].split()[-1].lower()
    filename = f"{stats['game_date']}_{home_nick}_vs_{away_nick}_{suffix}_odds.json"
    output = {
        "season": stats["season"],
        "round": stats["round"],
        "game_date": stats["game_date"],
        "home_team": stats["home_team"],
        "away_team": stats["away_team"],
        "source": "the_odds_api",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        **odds_data,
    }
    path = round_dir / filename
    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"  Odds saved → {path}")
    return path


def run_pricing(stats_path: Path) -> None:
    cmd = [sys.executable, str(PRICING_SCRIPT), "--file", str(stats_path), "--save"]
    try:
        subprocess.run(cmd, timeout=120, check=False)
    except subprocess.TimeoutExpired:
        print("  NRL pricing timed out after 120s; live polling will continue")


def touch_heartbeat(path: str | None) -> None:
    if path:
        heartbeat = Path(path)
        heartbeat.parent.mkdir(parents=True, exist_ok=True)
        heartbeat.touch()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="NRL halftime live stats scraper")
    p.add_argument("--round",  type=int, required=True)
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--home",   type=str, default=None, help="Filter to this home team nick")
    p.add_argument("--away",   type=str, default=None, help="Filter to this away team nick")
    p.add_argument("--force",  action="store_true", help="Skip halftime check (for testing on completed games)")
    p.add_argument("--once",   action="store_true", help="Poll once and exit (don't loop)")
    p.add_argument("--no-snapshot-odds", action="store_true", help="Do not spend Odds API calls at 10/20/30m")
    p.add_argument("--heartbeat", type=str, default=None, help=argparse.SUPPRESS)
    args = p.parse_args()

    print(f"\nNRL Halftime Scraper — R{args.round} {args.season}")
    print(f"Polling every {POLL_INTERVAL}s. Ctrl+C to stop.\n")

    processed: set[tuple[str, int]] = set()

    while True:
        touch_heartbeat(args.heartbeat)
        fixtures = fetch_fixtures(args.season, args.round)
        touch_heartbeat(args.heartbeat)

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

        active_fixtures = [f for f in fixtures if is_live(f) or args.force]

        if not active_fixtures:
            states = [(fixture_label(f), f.get("matchState", "?"), f.get("gameSeconds", 0)) for f in fixtures]
            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] No halftime games yet. States: {states}")
        else:
            for fixture in active_fixtures:
                label = fixture_label(fixture)
                mc_url = match_centre_url(fixture)
                data = fetch_match_data(mc_url)
                if not data:
                    continue
                observed = int(float(data.get("gameSeconds") or fixture.get("gameSeconds") or 0))
                if not observed:
                    observed = int(max((float(e.get("gameSeconds") or 0) for e in data.get("timeline", [])), default=0))
                state = (fixture.get("matchState") or "").lower().replace(" ", "")
                if state == "firsthalf" and 0 < observed < FIRST_HALF_END:
                    save_first_half_cache(args.round, fixture, data, observed)

                at_halftime = is_halftime(fixture) or observed >= FIRST_HALF_END or args.force
                if at_halftime:
                    observed = max(observed, FIRST_HALF_END)

                capture_data = data
                capture_observed = observed
                capture_quality = "exact_halftime"
                # NRL team-stat groups are cumulative. If a polling gap crosses
                # HT, current SecondHalf data is contaminated by Q3 play. Use
                # the last disk-persisted FirstHalf payload instead and label it.
                if state == "secondhalf":
                    cached_data, cached_observed = load_first_half_cache(args.round, fixture)
                    if cached_data is not None:
                        capture_data = cached_data
                        capture_observed = cached_observed
                        capture_quality = "late_first_half_fallback"

                due = [second for second in SNAPSHOT_SECONDS if observed >= second]
                if not due:
                    continue
                # Capture only the newest due checkpoint. Backfilling earlier
                # checkpoints with later data would silently corrupt training.
                checkpoint = max(due)
                key = (label, checkpoint)
                if key in processed:
                    continue

                print(f"\n{'='*55}")
                print(f"  {checkpoint // 60}-MIN SNAPSHOT: {label} (observed {observed}s)")
                print(f"{'='*55}")
                stats = extract_halftime_stats(
                    capture_data, args.season, args.round,
                    min(capture_observed, FIRST_HALF_END),
                )
                stats["checkpoint_game_seconds"] = checkpoint
                stats["checkpoint_lag_seconds"] = abs(capture_observed - checkpoint)
                stats["capture_quality"] = capture_quality
                if snapshot_exists(stats, checkpoint):
                    processed.add(key)
                    continue
                print_stats(stats)
                save_snapshot(stats, capture_data, checkpoint)

                if checkpoint < FIRST_HALF_END and not args.no_snapshot_odds:
                    odds = fetch_halftime_odds(stats["home_team"], stats["away_team"])
                    save_odds(odds, stats, f"{checkpoint // 60:02d}m")

                if checkpoint == FIRST_HALF_END:
                    stats_path = save_stats(stats)
                    if capture_quality != "exact_halftime":
                        print(
                            "\n  Late first-half fallback saved; odds and pricing "
                            "blocked because this is not an exact HT capture"
                        )
                    else:
                        print("\n  Fetching halftime odds...")
                        odds = fetch_halftime_odds(stats["home_team"], stats["away_team"])
                        save_odds(odds, stats)
                        print("\n  Running pricing model...")
                        run_pricing(stats_path)

                processed.add(key)

        if args.once:
            break

        touch_heartbeat(args.heartbeat)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
