#!/usr/bin/env python3
"""Quota-aware, change-only Odds API collector for every BetMate code.

Designed for a cloud cron invoking it every five minutes. Each invocation asks
Supabase which sports are due, fetches only those sports, appends genuine quote
changes/checkpoints, and upserts the small latest-state table.

Live writes require all of:
  ODDS_COLLECTION_LIVE_ENABLED=true
  ODDS_API_KEY
  NEXT_PUBLIC_SUPABASE_URL (or SUPABASE_URL)
  SUPABASE_SERVICE_ROLE_KEY
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
from typing import Iterable

import requests

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "odds_collection_config.json"
ODDS_URL = "https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
UTC = timezone.utc


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def chunks(values: list[dict], size: int = 400) -> Iterable[list[dict]]:
    for start in range(0, len(values), size):
        yield values[start:start + size]


def truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def selection_key(outcome: str, home: str, away: str) -> str | None:
    text = outcome.strip()
    lower = text.lower()
    if text == home:
        return "home"
    if text == away:
        return "away"
    if lower in {"draw", "tie"}:
        return "draw"
    if lower in {"over", "under", "yes", "no"}:
        return lower
    return None


def quote_key(row: dict) -> str:
    identity = "|".join([
        row["sport"], row["api_event_id"], row["bookmaker_key"],
        row["market_key"], row["selection_key"],
    ])
    return hashlib.sha256(identity.encode()).hexdigest()


def fingerprint(line_value, price_decimal) -> str:
    value = f"{'' if line_value is None else float(line_value):}|{float(price_decimal):.6f}"
    return hashlib.sha256(value.encode()).hexdigest()


def flatten(events: list[dict], sport: str, api_sport_key: str,
            captured_at: datetime, region: str) -> list[dict]:
    rows: list[dict] = []
    for event in events:
        commence = parse_time(event.get("commence_time"))
        if not commence:
            continue
        home, away = event.get("home_team", ""), event.get("away_team", "")
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                if market_key not in {"h2h", "spreads", "totals", "btts"}:
                    continue
                for outcome in market.get("outcomes", []):
                    side = selection_key(str(outcome.get("name", "")), home, away)
                    price = outcome.get("price")
                    if side is None or price is None or float(price) < 1.01:
                        continue
                    row = {
                        "sport": sport,
                        "api_sport_key": api_sport_key,
                        "api_event_id": event["id"],
                        "commence_time": iso(commence),
                        "home_team": home,
                        "away_team": away,
                        "bookmaker_key": bookmaker["key"],
                        "bookmaker_title": bookmaker.get("title"),
                        "bookmaker_updated_at": bookmaker.get("last_update"),
                        "market_key": market_key,
                        "selection_key": side,
                        "selection_name": str(outcome.get("name", "")),
                        "line_value": outcome.get("point"),
                        "price_decimal": float(price),
                        "source_region": region,
                        "captured_at": iso(captured_at),
                    }
                    row["quote_key"] = quote_key(row)
                    row["value_fingerprint"] = fingerprint(row["line_value"], row["price_decimal"])
                    rows.append(row)
    return rows


def cadence_minutes(config: dict, nearest_kickoff: datetime | None,
                    now: datetime) -> int:
    remaining = None if nearest_kickoff is None else max(0, int((nearest_kickoff - now).total_seconds() / 60))
    for rule in config["cadence_minutes"]:
        if rule["within_minutes"] is None or (remaining is not None and remaining <= rule["within_minutes"]):
            return int(rule["interval"])
    return 360


def checkpoint_for(minutes_to_kickoff: int, config: dict) -> tuple[str, int] | None:
    if 0 <= minutes_to_kickoff <= int(config["closing_window_minutes"]):
        return "close", 0
    targets = sorted((int(x) for x in config["checkpoints_minutes"]), reverse=True)
    for index, target in enumerate(targets):
        lower = targets[index + 1] if index + 1 < len(targets) else int(config["closing_window_minutes"])
        if lower < minutes_to_kickoff <= target:
            label = f"t_minus_{target}m"
            return label, target
    return None


class Supabase:
    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1"
        self.headers = {
            "apikey": key, "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def get_all(self, table: str, params: dict, page_size: int = 1000) -> list[dict]:
        output: list[dict] = []
        start = 0
        while True:
            headers = {**self.headers, "Range": f"{start}-{start + page_size - 1}"}
            response = requests.get(f"{self.base}/{table}", headers=headers, params=params, timeout=30)
            response.raise_for_status()
            page = response.json()
            output.extend(page)
            if len(page) < page_size:
                return output
            start += page_size

    def insert(self, table: str, rows: list[dict], ignore_duplicates: bool = False) -> None:
        if not rows:
            return
        prefer = "return=minimal"
        if ignore_duplicates:
            prefer += ",resolution=ignore-duplicates"
        for batch in chunks(rows):
            response = requests.post(f"{self.base}/{table}", headers={**self.headers, "Prefer": prefer},
                                     data=json.dumps(batch), timeout=45)
            response.raise_for_status()

    def upsert(self, table: str, rows: list[dict]) -> None:
        if not rows:
            return
        for batch in chunks(rows):
            response = requests.post(
                f"{self.base}/{table}",
                headers={**self.headers, "Prefer": "return=minimal,resolution=merge-duplicates"},
                data=json.dumps(batch), timeout=45,
            )
            response.raise_for_status()


def fetch_odds(api_key: str, api_sport_key: str, config: dict) -> tuple[list[dict], dict]:
    response = requests.get(
        ODDS_URL.format(sport_key=api_sport_key),
        params={"apiKey": api_key, "regions": config["regions"],
                "markets": config["markets"], "oddsFormat": config["odds_format"]},
        timeout=40,
    )
    response.raise_for_status()
    usage = {
        "used": int(response.headers.get("x-requests-used", "0") or 0),
        "remaining": int(response.headers.get("x-requests-remaining", "0") or 0),
        "last": int(response.headers.get("x-requests-last", "1") or 1),
    }
    return response.json(), usage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Ignore remote next_due_at")
    parser.add_argument("--sports", help="Comma-separated sport codes")
    parser.add_argument("--input-json", type=Path, help="Offline Odds API response for one selected sport")
    args = parser.parse_args()

    config = load_config(args.config)
    now = utcnow()
    selected = {x.strip().upper() for x in args.sports.split(",")} if args.sports else set(config["sports"])
    selected &= set(config["sports"])
    live_switch = truthy(os.getenv("ODDS_COLLECTION_LIVE_ENABLED"))
    live = not args.dry_run and live_switch
    if not args.dry_run and not live:
        print("Live collection is disabled. Set ODDS_COLLECTION_LIVE_ENABLED=true or use --dry-run.")
        return 2

    api_key = os.getenv("ODDS_API_KEY", "")
    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not args.input_json and not api_key:
        print("ODDS_API_KEY is required", file=sys.stderr)
        return 2
    if live and (not supabase_url or not service_key):
        print("SUPABASE_URL/NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required", file=sys.stderr)
        return 2

    db = Supabase(supabase_url, service_key) if live else None
    poll_states = {}
    if db:
        poll_states = {row["sport"]: row for row in db.get_all("odds_sport_poll_state", {"select": "*"})}

    run_id = str(uuid.uuid4())
    worker_id = os.getenv("ODDS_WORKER_ID", socket.gethostname())
    mode = "dry_run" if args.dry_run else ("checkpoint" if args.force else "scheduled")
    run = {"run_id": run_id, "started_at": iso(now), "worker_id": worker_id,
           "mode": mode, "status": "running", "sports_requested": sorted(selected)}
    if db:
        db.insert("odds_capture_runs", [run])

    totals = {"events": 0, "quotes": 0, "changes": 0, "requests": 0}
    fetched_sports: list[str] = []
    errors: list[dict] = []
    remaining: int | None = None

    for sport in sorted(selected):
        sport_config = config["sports"][sport]
        if not sport_config.get("enabled", False):
            continue
        state = poll_states.get(sport, {})
        next_due = parse_time(state.get("next_due_at"))
        if not args.force and next_due and now < next_due:
            print(f"{sport}: not due until {iso(next_due)}")
            continue
        try:
            if args.input_json:
                if len(selected) != 1:
                    raise ValueError("--input-json requires exactly one --sports code")
                events = json.loads(args.input_json.read_text(encoding="utf-8"))
                usage = {"last": 0, "remaining": 0}
            else:
                events, usage = fetch_odds(api_key, sport_config["api_key"], config)
            rows = flatten(events, sport, sport_config["api_key"], now, config["regions"])
            totals["requests"] += usage.get("last", 1)
            remaining = usage.get("remaining", remaining)
            totals["events"] += len(events)
            totals["quotes"] += len(rows)
            fetched_sports.append(sport)

            nearest = min((parse_time(e.get("commence_time")) for e in events if parse_time(e.get("commence_time")) and parse_time(e.get("commence_time")) > now), default=None)
            interval = cadence_minutes(config, nearest, now)
            if not db:
                print(f"{sport}: {len(events)} events, {len(rows)} quotes, next interval {interval}m")
                continue

            existing = {row["quote_key"]: row for row in db.get_all(
                "odds_quote_state",
                {"sport": f"eq.{sport}", "select": "quote_key,value_fingerprint,line_value,price_decimal,first_seen_at,last_changed_at"},
            )}
            existing_checkpoints = {
                (row["api_event_id"], row["bookmaker_key"], row["market_key"], row["selection_key"], row["checkpoint_name"])
                for row in db.get_all("odds_market_checkpoints", {"sport": f"eq.{sport}", "commence_time": f"gte.{iso(now - timedelta(hours=1))}",
                                                                  "select": "api_event_id,bookmaker_key,market_key,selection_key,checkpoint_name"})
            }
            changes, checkpoints, states = [], [], []
            for row in rows:
                prior = existing.get(row["quote_key"])
                changed = prior is None or prior["value_fingerprint"] != row["value_fingerprint"]
                minutes = int((parse_time(row["commence_time"]) - now).total_seconds() / 60)
                if changed:
                    if prior is None:
                        kind = "opening"
                    elif prior.get("line_value") != row["line_value"] and float(prior["price_decimal"]) != row["price_decimal"]:
                        kind = "line_and_price"
                    elif prior.get("line_value") != row["line_value"]:
                        kind = "line"
                    else:
                        kind = "price"
                    if 0 <= minutes <= int(config["closing_window_minutes"]):
                        kind = "closing"
                    changes.append({k: v for k, v in row.items() if k not in {"quote_key", "value_fingerprint"}} | {
                        "run_id": run_id, "previous_line_value": prior.get("line_value") if prior else None,
                        "previous_price_decimal": prior.get("price_decimal") if prior else None,
                        "change_kind": kind, "checkpoint_name": None,
                        "minutes_to_kickoff": minutes,
                    })
                checkpoint = checkpoint_for(minutes, config)
                if checkpoint:
                    name, target = checkpoint
                    identity = (row["api_event_id"], row["bookmaker_key"], row["market_key"], row["selection_key"], name)
                    if identity not in existing_checkpoints:
                        checkpoints.append({k: row[k] for k in (
                            "captured_at", "sport", "api_event_id", "commence_time", "home_team", "away_team",
                            "bookmaker_key", "market_key", "selection_key", "selection_name", "line_value",
                            "price_decimal", "bookmaker_updated_at") } | {
                            "run_id": run_id, "checkpoint_name": name,
                            "target_minutes_to_kickoff": target, "actual_minutes_to_kickoff": minutes,
                        })
                first_seen = prior.get("first_seen_at") if prior else row["captured_at"]
                last_changed = row["captured_at"] if changed else prior.get("last_changed_at", row["captured_at"])
                states.append({k: v for k, v in row.items() if k != "captured_at"} | {
                    "first_seen_at": first_seen, "last_seen_at": row["captured_at"],
                    "last_changed_at": last_changed, "updated_at": row["captured_at"],
                })
            db.insert("odds_quote_changes", changes)
            db.insert("odds_market_checkpoints", checkpoints, ignore_duplicates=True)
            db.upsert("odds_quote_state", states)
            totals["changes"] += len(changes)
            db.upsert("odds_sport_poll_state", [{
                "sport": sport, "api_sport_key": sport_config["api_key"], "enabled": True,
                "last_attempt_at": iso(now), "last_success_at": iso(now),
                "next_due_at": iso(now + timedelta(minutes=interval)),
                "nearest_kickoff": iso(nearest) if nearest else None,
                "consecutive_failures": 0, "last_error": None,
                "api_requests_remaining": remaining, "updated_at": iso(now),
            }])
            print(f"{sport}: {len(events)} events, {len(rows)} quotes, {len(changes)} changes, {len(checkpoints)} checkpoints")
        except Exception as exc:
            errors.append({"sport": sport, "error": str(exc)})
            print(f"{sport}: ERROR {exc}", file=sys.stderr)
            if db:
                failures = int(state.get("consecutive_failures", 0)) + 1
                db.upsert("odds_sport_poll_state", [{
                    "sport": sport, "api_sport_key": sport_config["api_key"], "enabled": True,
                    "last_attempt_at": iso(now), "next_due_at": iso(now + timedelta(minutes=15)),
                    "consecutive_failures": failures, "last_error": str(exc)[:1000], "updated_at": iso(now),
                }])

    status = "success" if not errors else ("partial" if fetched_sports else "failed")
    if db:
        response = requests.patch(
            f"{db.base}/odds_capture_runs", headers={**db.headers, "Prefer": "return=minimal"},
            params={"run_id": f"eq.{run_id}"}, data=json.dumps({
                "finished_at": iso(utcnow()), "status": status, "sports_fetched": fetched_sports,
                "api_requests_used": totals["requests"], "api_requests_remaining": remaining,
                "events_seen": totals["events"], "quotes_seen": totals["quotes"],
                "quote_changes_written": totals["changes"], "errors": errors,
            }), timeout=30,
        )
        response.raise_for_status()
    print(json.dumps({"status": status, "sports": fetched_sports, **totals, "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
