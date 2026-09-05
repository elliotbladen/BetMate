#!/usr/bin/env python3
"""Local append-only prospective tempo test for a single race day."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from race_day_tempo_worker import CONFIG, HERE, discover, fetch_card, load_json, process_meeting


def utc_stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--venues", default="randwick,sportsbet-sandown-hillside")
    parser.add_argument("--poll-seconds", type=int, default=75)
    parser.add_argument("--output", required=True)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--max-polls", type=int, default=0)
    args = parser.parse_args()

    wanted = {value.strip() for value in args.venues.split(",") if value.strip()}
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    config = load_json(CONFIG)
    bundle = load_json(HERE / config["model_bundle"])

    polls = 0
    while True:
        now = datetime.now(timezone.utc)
        payload = {"captured_at": utc_stamp(), "date": args.date, "meetings": [], "errors": []}
        for meeting in discover(args.date, config):
            if meeting["track_slug"] not in wanted:
                continue
            try:
                card = fetch_card(meeting["source_meeting_id"])
                payload["meetings"].append(
                    process_meeting(None, meeting, card, bundle, config, now, True, poll_sectionals=True)
                )
            except Exception as exc:
                payload["errors"].append({"meeting": meeting["track_slug"], "error": str(exc)})
        with output.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        latest = output.with_name(output.stem + "_latest.json")
        latest.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"captured_at": payload["captured_at"], "meetings": len(payload["meetings"]),
                          "errors": payload["errors"]}), flush=True)
        polls += 1
        if args.once or (args.max_polls and polls >= args.max_polls):
            return 1 if payload["errors"] else 0
        time.sleep(max(30, args.poll_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
