#!/usr/bin/env python3
"""Fail-fast health check for the cloud odds collector and Supabase storage."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=HERE / "odds_collection_config.json")
    parser.add_argument("--max-stale-minutes", type=int, default=390)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    url = (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")).rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print("Supabase URL and service-role key are required", file=sys.stderr)
        return 2
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    rpc = requests.post(f"{url}/rest/v1/rpc/betmate_market_storage_health", headers=headers, data="{}", timeout=30)
    rpc.raise_for_status()
    storage = rpc.json()
    states = requests.get(f"{url}/rest/v1/odds_sport_poll_state", headers=headers,
                          params={"select": "*", "enabled": "eq.true"}, timeout=30)
    states.raise_for_status()
    now = datetime.now(timezone.utc)
    alerts = []
    database_mb = float(storage["database_mb"])
    if database_mb >= config["database_critical_mb"]:
        alerts.append({"severity": "critical", "type": "database_size", "message": f"Database is {database_mb:.1f} MB"})
    elif database_mb >= config["database_high_mb"]:
        alerts.append({"severity": "warning", "type": "database_size", "message": f"Database is {database_mb:.1f} MB"})
    elif database_mb >= config["database_warning_mb"]:
        alerts.append({"severity": "info", "type": "database_size", "message": f"Database is {database_mb:.1f} MB"})
    for state in states.json():
        last = state.get("last_success_at")
        if not last:
            alerts.append({"severity": "critical", "type": "never_collected", "sport": state["sport"], "message": "No successful capture"})
            continue
        captured = datetime.fromisoformat(last.replace("Z", "+00:00"))
        stale = (now - captured).total_seconds() / 60
        if stale > args.max_stale_minutes:
            alerts.append({"severity": "critical", "type": "stale", "sport": state["sport"], "message": f"Last success {stale:.0f} minutes ago"})
        if int(state.get("consecutive_failures", 0)) >= 3:
            alerts.append({"severity": "critical", "type": "failures", "sport": state["sport"], "message": f"{state['consecutive_failures']} consecutive failures"})
        remaining = state.get("api_requests_remaining")
        if remaining is not None and int(remaining) < 1000:
            alerts.append({"severity": "warning", "type": "quota", "sport": state["sport"], "message": f"Only {remaining} API requests remain"})
    report = {"storage": storage, "poll_states": states.json(), "alerts": alerts}
    print(json.dumps(report, indent=2))
    return 1 if any(a["severity"] == "critical" for a in alerts) else 0


if __name__ == "__main__":
    sys.exit(main())
