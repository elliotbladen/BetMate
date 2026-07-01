#!/usr/bin/env python3
"""
Push sanitized Baz context to Supabase.

This publishes summaries for the live app, not BettingEngine internals:
- game model/market lines
- injuries, weather/ref context
- T9 confluence buckets and edge summaries
- round signal summaries

It does not upload code, SQLite databases, model weights, workbooks, configs, or
raw pipeline inputs.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from importlib import util as importlib_util
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


BETMATE_ROOT = Path(os.environ.get("BETMATE_ROOT", Path(__file__).resolve().parent.parent))
BAZ_LOCAL_API = os.environ.get("BAZ_LOCAL_API", "http://127.0.0.1:8765").rstrip("/")
try:
    SYDNEY_TZ = ZoneInfo("Australia/Sydney")
except ZoneInfoNotFoundError:
    SYDNEY_TZ = timezone(timedelta(hours=10))

GAME_FIELDS = {
    "sport",
    "home",
    "away",
    "date",
    "kickoff",
    "venue",
    "model",
    "ml_model",
    "market",
    "ev",
    "referee",
    "ref_bucket",
    "injuries",
    "weather",
    "explanation",
    "confluence",
    "totals_under_watch_0_10",
}

ARCHIVE_DIR = BETMATE_ROOT / "data" / "card_archive"
ODDS_SNAPSHOT_DIR = BETMATE_ROOT / "data" / "odds_snapshots"
ODDS_MOVEMENT_DIR = BETMATE_ROOT / "data" / "odds_movements"
ODDS_ROW_LIMIT = 300
ODDS_ARCHIVE_FIELDS = {
    "snapshot_date",
    "snapshot_time",
    "detected_date",
    "detected_time",
    "from_snapshot_time",
    "to_snapshot_time",
    "sport",
    "game_id",
    "home_team",
    "away_team",
    "commence_time",
    "bookmaker",
    "market",
    "outcome",
    "price",
    "point",
    "old_price",
    "new_price",
    "change",
    "change_pct",
    "direction",
}


def load_env() -> None:
    env_path = BETMATE_ROOT / ".env.local"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def get_json(path: str) -> dict[str, Any]:
    import requests

    resp = requests.get(f"{BAZ_LOCAL_API}{path}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def sanitize_game(game: dict[str, Any]) -> dict[str, Any]:
    clean = {key: game[key] for key in GAME_FIELDS if key in game}
    confluence = clean.get("confluence")
    if isinstance(confluence, dict):
        clean["confluence"] = {
            key: {
                "count": value.get("count", 0),
                "edges": [
                    {
                        "edge_pct": edge.get("edge_pct"),
                        "row": edge.get("row"),
                        "team": edge.get("team"),
                    }
                    for edge in (value.get("edges") or [])[:8]
                    if isinstance(edge, dict)
                ],
            }
            for key, value in confluence.items()
            if isinstance(value, dict)
        }
    return clean


def normalize_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-") or "unknown"


def archive_id_for_game(sport: str, season: Any, round_number: Any, game: dict[str, Any]) -> str:
    game_date = parse_game_date(game)
    date_part = game_date.isoformat() if game_date else "unknown-date"
    return (
        f"{sport.lower()}-{season or 'unknown-season'}-"
        f"r{round_number or 'unknown-round'}-{date_part}-"
        f"{slug(game.get('home'))}-v-{slug(game.get('away'))}"
    )


def csv_archive_paths(directory: Path) -> list[Path]:
    paths: list[Path] = []
    latest = directory / "latest.csv"
    if latest.exists():
        paths.append(latest)
    if directory.exists():
        paths.extend(
            sorted(
                [path for path in directory.glob("*/*.csv") if path.name != "latest.csv"],
                key=lambda path: str(path),
                reverse=True,
            )
        )
    return paths


def row_matches_game(row: dict[str, Any], sport: str, home: str, away: str) -> bool:
    if str(row.get("sport") or "").upper() != sport.upper():
        return False
    row_home = normalize_name(row.get("home_team") or row.get("home"))
    row_away = normalize_name(row.get("away_team") or row.get("away"))
    home_key = normalize_name(home)
    away_key = normalize_name(away)
    return row_home == home_key and row_away == away_key


def sanitize_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key in ODDS_ARCHIVE_FIELDS and value not in (None, "")
    }


def load_matching_csv_rows(directory: Path, sport: str, home: str, away: str) -> tuple[list[dict[str, Any]], str | None]:
    for path in csv_archive_paths(directory):
        rows: list[dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    if row_matches_game(row, sport, home, away):
                        rows.append(sanitize_csv_row(row))
                        if len(rows) >= ODDS_ROW_LIMIT:
                            break
        except OSError as exc:
            print(f"  WARNING: could not read odds archive {path}: {exc}")
            continue
        if rows:
            return rows, str(path.relative_to(BETMATE_ROOT))
    return [], None


def load_existing_archive(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_archive_file(sport: str, season: Any, round_number: Any, cards: list[dict[str, Any]]) -> dict[str, Any]:
    year = str(season or today_aest().year)
    archive_path = ARCHIVE_DIR / year / f"{sport.lower()}_r{round_number or 'unknown'}.json"
    existing = load_existing_archive(archive_path)
    by_id = {
        str(card.get("archive_id")): card
        for card in existing.get("cards", [])
        if isinstance(card, dict) and card.get("archive_id")
    }
    for card in cards:
        by_id[str(card["archive_id"])] = card

    payload = {
        "sport": sport,
        "season": season,
        "round": round_number,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "safety": {
            "public_blob": True,
            "contains_engine_code": False,
            "contains_model_weights": False,
            "contains_raw_database": False,
            "contains_matrix_workbooks": False,
        },
        "cards": sorted(by_id.values(), key=lambda item: str(item.get("archive_id", ""))),
    }
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"  Archived completed cards locally: {archive_path.relative_to(BETMATE_ROOT)} ({len(cards)} updated)")
    return payload


def push_data_store_key(key: str, data: dict[str, Any]) -> None:
    import requests

    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
    svc_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not svc_key:
        raise RuntimeError("NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing")

    payload = [{
        "key": key,
        "data": data,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }]
    resp = requests.post(
        f"{url}/rest/v1/betmate_data_store",
        headers={
            "apikey": svc_key,
            "Authorization": f"Bearer {svc_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        },
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()


def archive_completed_cards(
    sport: str,
    round_ctx: dict[str, Any],
    cutoff: date,
) -> list[dict[str, Any]]:
    completed = [
        game for game in round_ctx.get("games", [])
        if isinstance(game, dict) and not is_active_game(game, cutoff)
    ]
    if not completed:
        return []

    season = round_ctx.get("season")
    round_number = round_ctx.get("round")
    archived_at = datetime.now(timezone.utc).isoformat()
    cards: list[dict[str, Any]] = []

    for game in completed:
        home = str(game.get("home", "")).strip()
        away = str(game.get("away", "")).strip()
        if not home or not away:
            continue
        try:
            detail = get_json(
                f"/context/game?{urlencode({'home': home, 'away': away, 'sport': sport})}"
            )
        except Exception as exc:
            print(f"  WARNING: archive detail unavailable for {home} v {away}: {exc}")
            detail = game

        card = sanitize_game({**game, **detail})
        card["archive_id"] = archive_id_for_game(sport, season, round_number, {**game, **card})
        card["archived_at"] = archived_at
        card["archive_reason"] = "completed_removed_from_weekly_baz_slate"
        card["season"] = season
        card["round"] = round_number

        price_rows, price_source = load_matching_csv_rows(ODDS_SNAPSHOT_DIR, sport, home, away)
        movement_rows, movement_source = load_matching_csv_rows(ODDS_MOVEMENT_DIR, sport, home, away)
        card["bookmaker_prices"] = {
            "source": price_source,
            "rows": price_rows,
        }
        card["odds_movements"] = {
            "source": movement_source,
            "rows": movement_rows,
        }
        cards.append(card)

    if cards:
        archive_payload = save_archive_file(sport, season, round_number, cards)
        archive_key = f"baz_card_archive_{sport.lower()}_{season or 'unknown'}_r{round_number or 'unknown'}"
        push_data_store_key(archive_key, archive_payload)
        push_data_store_key(f"baz_card_archive_{sport.lower()}_latest", archive_payload)
        print(f"  Supabase archive OK: {archive_key} ({len(cards)} cards updated)")
    return cards


def _load_afl_matrix_module() -> Any:
    path = BETMATE_ROOT / "BettingEngine" / "scripts" / "afl_matrix_confluence.py"
    spec = importlib_util.spec_from_file_location("afl_matrix_confluence", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_afl_under_watch() -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Return under edges in the 0-10% band for each current AFL fixture."""
    try:
        amc = _load_afl_matrix_module()
        fixture_path = (
            BETMATE_ROOT
            / "BettingEngine"
            / "outputs"
            / "afl_round_prep"
            / "r17_2026"
            / "fixture_r17_2026.csv"
        )
        games = amc.load_fixture_csv(fixture_path)
        totals = amc.load_xlsx_matrix(BETMATE_ROOT / "BettingEngine" / "outputs" / "afl_team_totals_matrix.xlsx")
        history = amc.load_afl_history(amc.HIST_XLSX)
    except Exception as exc:
        print(f"  WARNING: AFL under-watch unavailable: {exc}")
        return {}

    def kickoff_hour_for_weekday(weekday: int) -> int:
        if weekday in (3, 4):
            return 19
        if weekday == 6:
            return 13
        return 14

    by_game: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for game in games:
        game_date = date.fromisoformat(game["date"])
        weekday = game_date.weekday()
        kickoff_hour = kickoff_hour_for_weekday(weekday)
        home_key = amc.fixture_to_key(game["home_team"])
        away_key = amc.fixture_to_key(game["away_team"])
        home_ctx = amc.get_afl_team_context(history, home_key, game_date)
        away_ctx = amc.get_afl_team_context(history, away_key, game_date)
        edges: list[dict[str, Any]] = []

        for team_key, team_label, role, generic_row, ctx in [
            (home_key, game["home_team"], "home", amc.GENERIC_ROWS["totals"][0], home_ctx),
            (away_key, game["away_team"], "away", amc.GENERIC_ROWS["totals"][1], away_ctx),
        ]:
            row_names = amc.applicable_row_names(
                kickoff_hour,
                weekday,
                game_date,
                role,
                home_key,
                away_key,
                game["venue"],
                ctx["rest_days"],
                ctx["last_result"],
                generic_row,
            )
            seen: set[str] = set()
            for row_name in row_names:
                if row_name in seen:
                    continue
                seen.add(row_name)
                value = totals.get(team_key, {}).get(row_name)
                if not value:
                    continue
                edge_pct, direction = value
                if direction and "unders" in direction.lower() and 0 < edge_pct <= 10:
                    edges.append({
                        "team": team_label,
                        "row": row_name,
                        "edge_pct": edge_pct,
                    })

        by_game[(game["home_team"], game["away_team"])] = sorted(edges, key=lambda item: -item["edge_pct"])

    return by_game


def today_aest() -> date:
    return datetime.now(SYDNEY_TZ).date()


def parse_game_date(game: dict[str, Any]) -> date | None:
    raw = str(game.get("date") or game.get("game_date") or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def is_active_game(game: dict[str, Any], cutoff: date) -> bool:
    game_date = parse_game_date(game)
    if game_date is None:
        return True
    return game_date >= cutoff


def pair_key(home: Any, away: Any) -> tuple[str, str]:
    return (str(home or "").strip().lower(), str(away or "").strip().lower())


def filter_signals_to_active_games(signals: dict[str, Any], active_pairs: set[tuple[str, str]]) -> dict[str, Any]:
    filtered = dict(signals)

    def keep_game_row(row: dict[str, Any]) -> bool:
        return pair_key(row.get("home"), row.get("away")) in active_pairs

    for key in ("matrix_signals", "totals_signals", "games_summary"):
        rows = filtered.get(key)
        if isinstance(rows, list):
            filtered[key] = [row for row in rows if isinstance(row, dict) and keep_game_row(row)]

    h2h_rows = filtered.get("h2h_signals")
    if isinstance(h2h_rows, list):
        # H2H rows are selection/opponent based, so keep them unless we can confidently map them.
        filtered["h2h_signals"] = h2h_rows

    return filtered


def build_context(sport: str) -> dict[str, Any]:
    round_ctx = get_json(f"/context/round?{urlencode({'sport': sport})}")
    signals = get_json(f"/signals?{urlencode({'sport': sport})}")
    try:
        clv = get_json("/clv?weeks=4")
    except Exception:
        clv = {}

    cutoff = today_aest()
    archived_cards = archive_completed_cards(sport, round_ctx, cutoff)
    source_games = [
        game for game in round_ctx.get("games", [])
        if isinstance(game, dict) and is_active_game(game, cutoff)
    ]
    stale_count = len(round_ctx.get("games", [])) - len(source_games)

    under_watch = build_afl_under_watch() if sport == "AFL" else {}
    detailed_games: list[dict[str, Any]] = []
    for game in source_games:
        home = str(game.get("home", ""))
        away = str(game.get("away", ""))
        if not home or not away:
            continue
        detail = get_json(
            f"/context/game?{urlencode({'home': home, 'away': away, 'sport': sport})}"
        )
        under_edges = under_watch.get((home, away), [])
        if under_edges:
            detail["totals_under_watch_0_10"] = {
                "count": len(under_edges),
                "edges": under_edges,
            }
        detailed_games.append(sanitize_game(detail))

    active_pairs = {pair_key(game.get("home"), game.get("away")) for game in detailed_games}
    filtered_signals = filter_signals_to_active_games(signals, active_pairs)

    return {
        "sport": round_ctx.get("sport", sport),
        "season": round_ctx.get("season"),
        "round": round_ctx.get("round"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "local_baz_sanitized",
        "safety": {
            "public_blob": True,
            "contains_engine_code": False,
            "contains_model_weights": False,
            "contains_raw_database": False,
            "contains_matrix_workbooks": False,
        },
        "expiry": {
            "cutoff_date_aest": cutoff.isoformat(),
            "stale_games_removed": stale_count,
            "completed_cards_archived": len(archived_cards),
        },
        "round_context": {
            "sport": round_ctx.get("sport", sport),
            "season": round_ctx.get("season"),
            "round": round_ctx.get("round"),
            "generated_at": round_ctx.get("generated_at"),
            "model_summary": round_ctx.get("model_summary", ""),
            "signals": round_ctx.get("signals", []),
            "games": detailed_games,
            "clv_last_4_rounds": clv,
        },
        "signals": filtered_signals,
        "clv": clv,
    }


def push_context(sport: str, context: dict[str, Any]) -> None:
    key = f"baz_context_{sport.lower()}_latest"
    push_data_store_key(key, context)
    print(f"  Supabase push OK: {key} ({len(context['round_context']['games'])} games)")


def main() -> int:
    load_env()
    sports = [arg.upper() for arg in sys.argv[1:]] or ["NRL", "AFL"]
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] push_baz_context.py")
    print(f"  Source: {BAZ_LOCAL_API}")
    for sport in sports:
        if sport not in {"NRL", "AFL"}:
            print(f"  SKIP unsupported sport: {sport}")
            continue
        print(f"  Building {sport} context...")
        context = build_context(sport)
        push_context(sport, context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
