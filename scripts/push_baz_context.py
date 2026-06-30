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

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


BETMATE_ROOT = Path(os.environ.get("BETMATE_ROOT", Path(__file__).resolve().parent.parent))
BAZ_LOCAL_API = os.environ.get("BAZ_LOCAL_API", "http://127.0.0.1:8765").rstrip("/")

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


def build_context(sport: str) -> dict[str, Any]:
    round_ctx = get_json(f"/context/round?{urlencode({'sport': sport})}")
    signals = get_json(f"/signals?{urlencode({'sport': sport})}")
    try:
        clv = get_json("/clv?weeks=4")
    except Exception:
        clv = {}

    detailed_games: list[dict[str, Any]] = []
    for game in round_ctx.get("games", []):
        home = str(game.get("home", ""))
        away = str(game.get("away", ""))
        if not home or not away:
            continue
        detail = get_json(
            f"/context/game?{urlencode({'home': home, 'away': away, 'sport': sport})}"
        )
        detailed_games.append(sanitize_game(detail))

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
        "signals": signals,
        "clv": clv,
    }


def push_context(sport: str, context: dict[str, Any]) -> None:
    import requests

    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
    svc_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not svc_key:
        raise RuntimeError("NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing")

    key = f"baz_context_{sport.lower()}_latest"
    payload = [{
        "key": key,
        "data": context,
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
