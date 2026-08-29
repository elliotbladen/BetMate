#!/usr/bin/env python3
"""
scripts/afl_ht_live.py

AFL halftime live stats scraper — no login, no browser required.
Polls Squiggle API for AFL games at halftime, extracts quarter scores,
saves JSON, and fires the AFL halftime pricing script.

Squiggle API: https://api.squiggle.com.au/?q=games;year=YYYY;round=RR
  complete=50  → game is at halftime
  timestr      → "Half Time" (or in-quarter like "Q2  3:45")
  hgoals/hbehinds/agoals/abehinds → live cumulative scores

Usage:
    uv run python scripts/afl_ht_live.py --round 14
    uv run python scripts/afl_ht_live.py --round 14 --season 2026
    uv run python scripts/afl_ht_live.py --round 14 --home Melbourne --away Essendon
    uv run python scripts/afl_ht_live.py --round 14 --force   # skip halftime check (testing)
    uv run python scripts/afl_ht_live.py --round 14 --once    # poll once and exit
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

_ROOT = Path(__file__).resolve().parents[1]
HALFTIME_DIR = _ROOT / "data" / "afl" / "halfTime"
PRICING_SCRIPT = _ROOT / "scripts" / "halfTime_price_afl.py"

SQUIGGLE_URL = "https://api.squiggle.com.au/?q=games;year={year};round={round}"
POLL_INTERVAL = 30  # seconds between polls
FIRST_HALF_SNAPSHOT_PCT = ((12.5, "10m"), (25.0, "20m"), (37.5, "30m"))

# ── Odds API ─────────────────────────────────────────────────────────────────
ENV_PATH       = _ROOT.parent / ".env.local"
ODDS_EVENTS_URL = "https://api.the-odds-api.com/v4/sports/{sport_key}/events"
ODDS_EVENT_ODDS = "https://api.the-odds-api.com/v4/sports/{sport_key}/events/{event_id}/odds"
ODDS_SPORT_KEY  = "aussierules_afl"
ODDS_LIVE_MARKETS = "h2h,spreads,totals"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json,*/*",
}

FW_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}
FOOTYWIRE_SCOREBOARD = "https://www.footywire.com/afl/footy/live_scoreboard"
FOOTYWIRE_STATS_URL  = "https://www.footywire.com/afl/footy/live_stats?mid={mid}"
FOX_PLAYER_STATS_URL = "https://www.foxsports.com.au/afl/match-centre/{match_id}/playerstats"
REQUIRED_LIVE_STATS = (
    "home_inside_50s", "away_inside_50s",
    "home_clearances", "away_clearances",
    "home_clangers", "away_clangers",
)


# ── Squiggle API ───────────────────────────────────────────────────────────────

def fetch_games(season: int, round_num: int) -> list[dict]:
    url = SQUIGGLE_URL.format(year=season, round=round_num)
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json().get("games", [])
    except Exception as exc:
        print(f"  Squiggle API error: {exc}")
        return []


def is_halftime(game: dict) -> bool:
    """Detect halftime: complete==50 or timestr contains 'half time'."""
    complete = game.get("complete", 0) or 0
    timestr = (game.get("timestr") or "").lower()
    if "half time" in timestr or "halftime" in timestr:
        return True
    if complete == 50:
        return True
    return False


def is_second_quarter(game: dict) -> bool:
    """True while Squiggle explicitly reports the match in Q2."""
    return (game.get("timestr") or "").strip().lower().startswith("q2")


def crossed_halftime(game: dict, previous: dict | None) -> bool:
    """Detect a missed interval when polling jumps directly from Q2 to Q3."""
    if previous is None or not is_second_quarter(previous):
        return False
    complete = float(game.get("complete", 0) or 0)
    timestr = (game.get("timestr") or "").strip().lower()
    return 50 < complete < 75 or timestr.startswith("q3")


def game_label(g: dict) -> str:
    return f"{g.get('hteam','?')} vs {g.get('ateam','?')}"


def _q2_state_path(season: int, round_num: int) -> Path:
    return HALFTIME_DIR / f"R{round_num:02d}" / "state" / f"{season}_latest_q2.json"


def load_q2_state(season: int, round_num: int) -> dict[str, dict]:
    path = _q2_state_path(season, round_num)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_q2_state(season: int, round_num: int, states: dict[str, dict]) -> None:
    path = _q2_state_path(season, round_num)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(states, indent=2), encoding="utf-8")
    temporary.replace(path)


# ── FootyWire live stats ───────────────────────────────────────────────────────

# Squiggle uses full names, FootyWire uses abbreviations/nicknames.
# Map Squiggle team names to all search terms that might appear on FootyWire.
_FW_SEARCH_TERMS: dict[str, list[str]] = {
    "greater western sydney": ["gws", "giants"],
    "gold coast":             ["suns", "gold coast"],
    "west coast":             ["eagles", "west coast"],
    "north melbourne":        ["kangaroos", "north melbourne"],
    "western bulldogs":       ["bulldogs", "western bulldogs"],
    "port adelaide":          ["power", "port adelaide"],
    "st kilda":               ["saints", "st kilda"],
}


def _fw_terms(team_name: str) -> list[str]:
    """Build a list of search terms for matching a team on FootyWire."""
    terms = [team_name.split()[-1].lower()]
    key = team_name.lower()
    for pattern, aliases in _FW_SEARCH_TERMS.items():
        if pattern in key:
            terms.extend(aliases)
            break
    return list(set(t for t in terms if len(t) >= 3))


def fetch_footywire_mid(home_team: str, away_team: str) -> int | None:
    """
    Find the FootyWire live match ID by scraping the live scoreboard page
    and matching team names against the game we want.
    Returns the mid integer, or None if not found.
    """
    try:
        r = requests.get(FOOTYWIRE_SCOREBOARD, headers=FW_HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as exc:
        print(f"  FootyWire scoreboard error: {exc}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    home_terms = _fw_terms(home_team)
    away_terms = _fw_terms(away_team)

    # Collect all live_stats mids on the page
    all_mids: list[int] = []
    for a in soup.find_all("a", href=True):
        if "live_stats?mid=" not in a["href"]:
            continue
        try:
            all_mids.append(int(a["href"].split("mid=")[-1]))
        except ValueError:
            continue

    if not all_mids:
        return None

    # Search full page text (the link's parent container is often too narrow)
    page_text = soup.get_text(" ", strip=True).lower()

    # Try matching against each mid's surrounding table
    for a in soup.find_all("a", href=True):
        if "live_stats?mid=" not in a["href"]:
            continue
        try:
            mid = int(a["href"].split("mid=")[-1])
        except ValueError:
            continue
        # Search up to the broadest table container
        container = a.find_parent("table")
        if container is None:
            container = a.find_parent("div")
        if container is None:
            continue
        text = container.get_text(" ", strip=True).lower()
        home_ok = any(t in text for t in home_terms)
        away_ok = any(t in text for t in away_terms)
        if home_ok and away_ok:
            return mid

    # Fallback: if only one game is live and at least one team matches the page,
    # it's unambiguous — use it.
    if len(all_mids) == 1:
        home_ok = any(t in page_text for t in home_terms)
        away_ok = any(t in page_text for t in away_terms)
        if home_ok or away_ok:
            return all_mids[0]

    return None


def parse_footywire_stats_html(html: str) -> dict:
    """Parse selected team totals from FootyWire's Head-to-Head table."""
    soup = BeautifulSoup(html, "html.parser")
    result: dict = {}
    fields = {
        "Inside 50s": ("home_inside_50s", "away_inside_50s"),
        "Clearances": ("home_clearances", "away_clearances"),
        "Clangers": ("home_clangers", "away_clangers"),
    }

    for label, (home_key, away_key) in fields.items():
        label_cell = soup.find(
            "td",
            class_="statdata",
            string=lambda value: value is not None and value.strip() == label,
        )
        if label_cell is None:
            continue
        row = label_cell.find_parent("tr")
        cells = row.find_all("td", class_="statdata") if row else []
        if len(cells) != 3:
            continue
        try:
            result[home_key] = int(cells[0].get_text(strip=True))
            result[away_key] = int(cells[2].get_text(strip=True))
        except (TypeError, ValueError):
            continue

    return result


def parse_fox_team_stats_html(html: str) -> dict:
    """Aggregate Fox's live player feed into the required team totals."""
    marker = "window.fisoBoot['core-match-centre']['"
    marker_pos = html.find(marker)
    assignment_pos = html.find("]=", marker_pos)
    script_end = html.find("</script>", assignment_pos)
    if marker_pos < 0 or assignment_pos < 0 or script_end < 0:
        return {}

    try:
        payload = json.loads(html[assignment_pos + 2:script_end].rstrip().rstrip(";"))
        widgets = payload["hydration"]["page"]["content"]["widgets"]
        widget_key = next(key for key in widgets if "playerStats" in key)
        player_stats = widgets[widget_key]["playerStats$"]
    except (json.JSONDecodeError, KeyError, StopIteration, TypeError):
        return {}

    result: dict = {}
    field_map = {
        "inside_fifty": "inside_50s",
        "clearances": "clearances",
        # Fox calls clangers/errors `errors`; verified against FootyWire totals.
        "errors": "clangers",
    }
    for side, fox_team in (("home", "team_A"), ("away", "team_B")):
        try:
            players = player_stats[fox_team]["players"]
        except (KeyError, TypeError):
            return {}
        for fox_field, output_field in field_map.items():
            values = [(player.get("stats") or {}).get(fox_field) for player in players]
            if not values or all(value is None for value in values):
                continue
            result[f"{side}_{output_field}"] = sum(int(value or 0) for value in values)
    return result


def _save_raw_provider_response(source: str, identifier: str, html: str) -> None:
    """Retain compressed source HTML so parser failures can be replayed later."""
    raw_dir = HALFTIME_DIR / "raw" / datetime.now().strftime("%Y-%m-%d")
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%H%M%S")
    path = raw_dir / f"{source}_{identifier}_{stamp}.html.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(html)


def fetch_fox_team_stats(match_id: str | None) -> dict:
    """Fetch required live team totals from Fox Sports as a provider backup."""
    if not match_id:
        return {}
    response = None
    for attempt in range(1, 4):
        try:
            response = requests.get(
                FOX_PLAYER_STATS_URL.format(match_id=match_id),
                headers=FW_HEADERS,
                timeout=15,
            )
            response.raise_for_status()
            break
        except Exception as exc:
            print(f"  Fox Sports team stats attempt {attempt}/3 failed: {exc}")
            response = None
            if attempt < 3:
                time.sleep(attempt)
    if response is None:
        return {}
    _save_raw_provider_response("fox", match_id, response.text)
    return parse_fox_team_stats_html(response.text)


def fetch_footywire_stats(mid: int) -> dict:
    """
    Scrape the Head-to-Head stats table from a FootyWire live stats page.
    Returns dict with home/away inside 50s, clearances, clangers.
    Returns empty dict on any failure — caller falls back gracefully.
    """
    r = None
    for attempt in range(1, 4):
        try:
            r = requests.get(FOOTYWIRE_STATS_URL.format(mid=mid), headers=FW_HEADERS, timeout=15)
            r.raise_for_status()
            break
        except Exception as exc:
            print(f"  FootyWire stats attempt {attempt}/3 failed: {exc}")
            r = None
            if attempt < 3:
                time.sleep(attempt)
    if r is None:
        return {}

    _save_raw_provider_response("footywire", str(mid), r.text)
    return parse_footywire_stats_html(r.text)


def _complete_live_stats(values: dict) -> bool:
    return all(key in values for key in REQUIRED_LIVE_STATS)


def enrich_with_live_stats(stats: dict) -> dict:
    """
    Auto-find FootyWire match ID and scrape live team stats.
    Enriches stats dict in-place. Prints what was found.
    """
    home = stats["home_team"]
    away = stats["away_team"]

    print(f"  Fetching FootyWire live stats for {home} vs {away}...")
    mid = fetch_footywire_mid(home, away)
    fw_stats: dict = {}
    if mid is None:
        print("  FootyWire: match not found on live scoreboard")
    else:
        print(f"  FootyWire: found mid={mid}")
        fw_stats = fetch_footywire_stats(mid)
        if not _complete_live_stats(fw_stats):
            print("  FootyWire: required stats incomplete — activating backup")

    fox_match_id = stats.get("fox_match_id")
    print(f"  Fetching Fox Sports backup stats ({fox_match_id or 'no match ID'})...")
    fox_stats = fetch_fox_team_stats(fox_match_id)
    if not _complete_live_stats(fox_stats):
        print("  Fox Sports: required stats incomplete")

    sources = []
    if _complete_live_stats(fw_stats):
        sources.append("footywire")
    if _complete_live_stats(fox_stats):
        sources.append("foxsports")

    if not sources:
        stats["live_stats_status"] = "MISSING_REQUIRED_STATS"
        stats["live_stats_sources"] = []
        print("  !!! LIVE STATS ALERT: both FootyWire and Fox Sports failed")
        return stats

    # FootyWire remains primary. Fox independently fills any missing fields and
    # acts as an exact-value cross-check whenever both feeds are healthy.
    selected = dict(fox_stats)
    selected.update(fw_stats)
    stats.update(selected)
    stats["live_stats_source"] = "footywire" if _complete_live_stats(fw_stats) else "foxsports"
    stats["live_stats_sources"] = sources
    stats["live_stats_status"] = "complete"
    if mid is not None:
        stats["footywire_mid"] = mid

    disagreements = {
        key: {"footywire": fw_stats[key], "foxsports": fox_stats[key]}
        for key in REQUIRED_LIVE_STATS
        if key in fw_stats and key in fox_stats and fw_stats[key] != fox_stats[key]
    }
    stats["live_stats_crosscheck"] = "match" if len(sources) == 2 and not disagreements else (
        "disagreement" if disagreements else "single_source"
    )
    if disagreements:
        stats["live_stats_disagreements"] = disagreements
        print(f"  !!! LIVE STATS ALERT: provider disagreement: {disagreements}")

    home_i50 = selected.get("home_inside_50s", "?")
    away_i50 = selected.get("away_inside_50s", "?")
    home_clr = selected.get("home_clearances", "?")
    away_clr = selected.get("away_clearances", "?")
    home_clg = selected.get("home_clangers", "?")
    away_clg = selected.get("away_clangers", "?")
    print(f"  I50: {home} {home_i50} / {away} {away_i50}")
    print(f"  Clearances: {home} {home_clr} / {away} {away_clr}")
    print(f"  Clangers: {home} {home_clg} / {away} {away_clg}")

    return stats


# ── Stats extraction ───────────────────────────────────────────────────────────

def extract_halftime_stats(game: dict, season: int, round_num: int) -> dict:
    home_team = game.get("hteam", "Home")
    away_team = game.get("ateam", "Away")

    home_goals    = int(game.get("hgoals") or 0)
    home_behinds  = int(game.get("hbehinds") or 0)
    away_goals    = int(game.get("agoals") or 0)
    away_behinds  = int(game.get("abehinds") or 0)

    home_ht_score = home_goals * 6 + home_behinds
    away_ht_score = away_goals * 6 + away_behinds

    # Date: Squiggle 'date' is local time in format "2026-06-13 13:15:00"
    date_raw = game.get("date", "")
    try:
        game_date = date_raw[:10]
    except Exception:
        game_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    venue = game.get("venue", "")

    stats = {
        "season":         season,
        "round":          round_num,
        "game_date":      game_date,
        "home_team":      home_team,
        "away_team":      away_team,
        "venue":          venue,
        "source":         "squiggle_api",
        "collected_at":   datetime.now(timezone.utc).isoformat(),
        "home_ht_score":  home_ht_score,
        "away_ht_score":  away_ht_score,
        "home_goals":     home_goals,
        "home_behinds":   home_behinds,
        "away_goals":     away_goals,
        "away_behinds":   away_behinds,
        "squiggle_id":    game.get("id"),
        "round_game_num": game.get("_round_game_num"),
        "fox_match_id":   game.get("fox_match_id"),
        "timestr":        game.get("timestr", ""),
        "notes":          "",
    }
    return stats


def print_stats(stats: dict) -> None:
    h = stats["home_team"]
    a = stats["away_team"]
    print(f"\n  {'─'*52}")
    print(f"  HT Score:  {h} {stats['home_goals']}.{stats['home_behinds']} ({stats['home_ht_score']}) "
          f"– {a} {stats['away_goals']}.{stats['away_behinds']} ({stats['away_ht_score']})")
    print(f"  Venue:     {stats['venue']}")
    print(f"  {'─'*52}")


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


def save_snapshot(stats: dict, raw_game: dict, label: str) -> tuple[Path, Path, bool]:
    """Save normalized and raw append-only first-half calibration snapshots."""
    round_dir = HALFTIME_DIR / f"R{stats['round']:02d}" / "snapshots"
    round_dir.mkdir(parents=True, exist_ok=True)
    home_nick = stats["home_team"].split()[-1].lower()
    away_nick = stats["away_team"].split()[-1].lower()
    stem = f"{stats['game_date']}_{home_nick}_vs_{away_nick}_{label}"
    normalized = round_dir / f"{stem}_stats.json"
    raw = round_dir / f"{stem}_raw.json"
    created = not normalized.exists()
    replace_incomplete = False
    if not created:
        try:
            previous = json.loads(normalized.read_text(encoding="utf-8"))
            replace_incomplete = (
                previous.get("live_stats_status") != "complete"
                and stats.get("live_stats_status") == "complete"
            )
        except (OSError, json.JSONDecodeError):
            replace_incomplete = True
    if created or replace_incomplete:
        normalized.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    if not raw.exists():
        raw.write_text(json.dumps({"collected_at": stats["collected_at"], "game": raw_game}, indent=2), encoding="utf-8")
    action = "repaired" if replace_incomplete else "saved"
    print(f"  Snapshot {action} → {normalized}")
    return normalized, raw, created


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
    """Extract the last word as a nickname: 'Adelaide Crows' → 'crows'."""
    return _normalise_team(name).split()[-1] if name.strip() else ""


def _teams_match(name_a: str, name_b: str) -> bool:
    a = _normalise_team(name_a)
    b = _normalise_team(name_b)
    if a in b or b in a:
        return True
    # Fallback: nickname match
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


# Event ID cache: once matched, skip /events on subsequent snapshots.
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
    if not PRICING_SCRIPT.exists():
        print(f"  (AFL pricing script not yet built at {PRICING_SCRIPT} — skipping)")
        return
    cmd = [sys.executable, str(PRICING_SCRIPT), "--file", str(stats_path), "--save"]
    try:
        subprocess.run(cmd, timeout=120, check=False)
    except subprocess.TimeoutExpired:
        print("  AFL pricing timed out after 120s; live polling will continue")


def touch_heartbeat(path: str | None) -> None:
    if path:
        heartbeat = Path(path)
        heartbeat.parent.mkdir(parents=True, exist_ok=True)
        heartbeat.touch()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="AFL halftime live stats scraper (Squiggle API)")
    p.add_argument("--round",  type=int, required=True)
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--home",   type=str, default=None, help="Filter to home team name (partial match)")
    p.add_argument("--away",   type=str, default=None, help="Filter to away team name (partial match)")
    p.add_argument("--force",  action="store_true", help="Skip halftime check (for testing on completed games)")
    p.add_argument("--once",   action="store_true", help="Poll once and exit")
    p.add_argument("--heartbeat", type=str, default=None, help=argparse.SUPPRESS)
    args = p.parse_args()

    print(f"\nAFL Halftime Scraper — R{args.round} {args.season}")
    print(f"Polling every {POLL_INTERVAL}s. Ctrl+C to stop.\n")

    processed = set()
    snapshot_processed: set[tuple[str, str]] = set()
    # Persist this across poller/watchdog restarts. Without it, a restart or
    # machine wake between Q2 and Q3 loses the only uncontaminated fallback.
    last_q2: dict[str, dict] = load_q2_state(args.season, args.round)

    while True:
        touch_heartbeat(args.heartbeat)
        games = fetch_games(args.season, args.round)
        touch_heartbeat(args.heartbeat)
        # Fox match-centre IDs use chronological game number within the round.
        for game_num, game in enumerate(sorted(games, key=lambda g: str(g.get("date", ""))), start=1):
            game["_round_game_num"] = game_num
            game["fox_match_id"] = f"AFL{args.season}{args.round:02d}{game_num:02d}"

        # Optional team filter
        if args.home or args.away:
            filtered = []
            for g in games:
                h = g.get("hteam", "").lower()
                a = g.get("ateam", "").lower()
                if args.home and args.home.lower() not in h:
                    continue
                if args.away and args.away.lower() not in a:
                    continue
                filtered.append(g)
            games = filtered

        # First-half forward-calibration snapshots. Squiggle `complete` is the
        # fraction of regulation elapsed, so 12.5/25/37.5 correspond to nominal
        # 10/20/30 game minutes. Never backfill an earlier checkpoint with later
        # data: only the newest crossed checkpoint is recorded.
        for game in games:
            label = game_label(game)
            complete = float(game.get("complete", 0) or 0)
            active_first_half = 0 < complete < 50 and (
                (game.get("timestr") or "").strip().lower().startswith(("q1", "q2"))
                or complete in (25.0,)
            )
            due = [(pct, name) for pct, name in FIRST_HALF_SNAPSHOT_PCT if complete >= pct]
            if not active_first_half or not due:
                continue
            _, checkpoint_name = max(due)
            key = (label, checkpoint_name)
            if key in snapshot_processed:
                continue
            stats = extract_halftime_stats(game, args.season, args.round)
            stats["snapshot_label"] = checkpoint_name
            stats["snapshot_complete_pct"] = complete
            enrich_with_live_stats(stats)
            _, _, created = save_snapshot(stats, game, checkpoint_name)
            if created:
                odds = fetch_halftime_odds(stats["home_team"], stats["away_team"])
                save_odds(odds, stats, checkpoint_name)
            snapshot_processed.add(key)

        halftime_games: list[tuple[dict, bool]] = []
        for game in games:
            label = game_label(game)
            if label in processed:
                continue
            if is_halftime(game) or args.force:
                halftime_games.append((game, False))
            elif crossed_halftime(game, last_q2.get(label)):
                # Never use cumulative Q3 scores as halftime scores. Preserve
                # the latest known Q2 snapshot and clearly mark its limitations.
                halftime_games.append((last_q2[label], True))

            if is_second_quarter(game):
                last_q2[label] = dict(game)

        if last_q2:
            save_q2_state(args.season, args.round, last_q2)

        if not halftime_games:
            states = [(game_label(g), g.get("timestr", "?"), g.get("complete", 0)) for g in games]
            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] No halftime games yet. States: {states}")
        else:
            for game, late_fallback in halftime_games:
                label = game_label(game)
                print(f"\n{'='*56}")
                print(f"  HALFTIME DETECTED: {label}")
                print(f"  timestr={game.get('timestr')}  complete={game.get('complete')}")
                print(f"{'='*56}")

                stats = extract_halftime_stats(game, args.season, args.round)
                stats["capture_quality"] = "late_q2_fallback" if late_fallback else "exact_halftime"
                if late_fallback:
                    stats["notes"] = (
                        "Exact halftime state was missed; scores are from the last observed "
                        "Q2 snapshot. Do not use as an exact halftime training row."
                    )
                    print("  WARNING: feed crossed halftime; saving last Q2 snapshot as fallback")
                print_stats(stats)

                if late_fallback:
                    print("  Live stats skipped: they would already include Q3 activity")
                else:
                    enrich_with_live_stats(stats)

                stats_path = save_stats(stats)
                if not late_fallback:
                    save_snapshot(stats, game, "ht")

                if not late_fallback and stats.get("live_stats_status") != "complete":
                    print(
                        "\n  !!! PRICING BLOCKED: required live stats are missing; "
                        "the next poll will retry both providers"
                    )
                    continue

                if late_fallback:
                    print("\n  Odds skipped: post-halftime prices are not a valid HT snapshot")
                else:
                    print("\n  Fetching halftime odds...")
                    odds = fetch_halftime_odds(stats["home_team"], stats["away_team"])
                    save_odds(odds, stats)

                processed.add(label)

                if late_fallback:
                    print("\n  Pricing skipped: fallback snapshot is not exact halftime data")
                else:
                    print("\n  Running AFL pricing model...")
                    run_pricing(stats_path)

        if args.once:
            break

        touch_heartbeat(args.heartbeat)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
