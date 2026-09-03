#!/usr/bin/env python3
"""Validate and append timestamped market-news events to Supabase.

Accepts one JSON object or a JSON array from --input. Source-specific scrapers
can target this stable intake format without receiving database credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

SPORTS = {"AFL", "NRL", "EPL", "EFL", "NFL", "UCL"}
LEVELS = {"A", "B", "C", "D"}


def normalize(record: dict) -> dict:
    required = ("published_at", "sport", "event_type", "source_level", "source_name", "source_url")
    missing = [key for key in required if not record.get(key)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    sport = str(record["sport"]).upper()
    level = str(record["source_level"]).upper()
    if sport not in SPORTS:
        raise ValueError(f"Unsupported sport {sport}")
    if level not in LEVELS:
        raise ValueError(f"Invalid source_level {level}")
    published = datetime.fromisoformat(str(record["published_at"]).replace("Z", "+00:00"))
    if published.tzinfo is None:
        raise ValueError("published_at must include a timezone")
    captured = record.get("captured_at") or datetime.now(timezone.utc).isoformat()
    stable = "|".join([sport, str(record["source_url"]), str(record["event_type"]),
                       str(record.get("team_name", "")), str(record.get("player_name", "")),
                       published.astimezone(timezone.utc).isoformat(), str(record.get("raw_text", ""))])
    allowed = {
        "published_at", "captured_at", "sport", "api_event_id", "canonical_match_id",
        "team_name", "player_name", "event_type", "status_before", "status_after",
        "position", "expected_role", "replacement_player", "source_level", "source_name",
        "source_url", "raw_text", "structured_summary", "confidence", "expected_impact",
        "confirmed", "supersedes_event_id",
    }
    output = {key: value for key, value in record.items() if key in allowed}
    output.update({"sport": sport, "source_level": level, "published_at": published.astimezone(timezone.utc).isoformat(),
                   "captured_at": captured, "confirmed": bool(record.get("confirmed", level == "A")),
                   "content_hash": hashlib.sha256(stable.encode()).hexdigest()})
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    records = payload if isinstance(payload, list) else [payload]
    normalized = [normalize(record) for record in records]
    if args.dry_run:
        print(json.dumps(normalized, indent=2))
        return 0
    if os.getenv("ODDS_COLLECTION_LIVE_ENABLED", "").lower() != "true":
        print("Live ingestion disabled; set ODDS_COLLECTION_LIVE_ENABLED=true", file=sys.stderr)
        return 2
    url = (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")).rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print("Supabase URL and service-role key are required", file=sys.stderr)
        return 2
    response = requests.post(
        f"{url}/rest/v1/market_news_events",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Prefer": "return=minimal,resolution=ignore-duplicates"},
        data=json.dumps(normalized), timeout=30,
    )
    response.raise_for_status()
    print(f"Accepted {len(normalized)} event(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
