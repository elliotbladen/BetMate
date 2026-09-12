#!/usr/bin/env python3
"""Send ONE real reminder email to a chosen address, to prove the mail path works.

Why this exists: app/api/cron/tipping-reminder only emails entrants who have not
finished tipping, and only inside the lock window, so it cannot be used to send a
test to yourself on demand. This sends the same message, from the same sender, via
the same Resend endpoint - so a delivered email proves the API key, the verified
betmate.au domain and the DKIM record are all genuinely working.

It does NOT touch tipping_reminders, so it cannot mark a real entrant as already
reminded.

  RESEND_API_KEY must be set in .env.local (it is write-only in Vercel and cannot
  be pulled back out).

  python3 scripts/send_test_reminder_email.py --to you@example.com
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RESEND_ENDPOINT = "https://api.resend.com/emails"


def load_env() -> None:
    env = ROOT / ".env.local"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True, help="address to send the test to")
    ap.add_argument("--name", default="Elliot")
    ap.add_argument("--from-address", default=os.getenv("TIPPING_REMINDER_FROM",
                                                       "BetMate <tips@betmate.au>"))
    args = ap.parse_args()

    load_env()
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        print("RESEND_API_KEY is empty. Get it from resend.com -> API Keys and put it in\n"
              ".env.local as RESEND_API_KEY=... (Vercel keeps secrets write-only, so it\n"
              "cannot be pulled back down from there).", file=sys.stderr)
        return 2

    # Mirrors the real template in app/api/cron/tipping-reminder/route.ts so that a
    # successful delivery tells you something about the actual reminder, not about a
    # different message that happens to use the same provider.
    locks_at = datetime.now(timezone.utc) + timedelta(hours=36)
    locks = locks_at.strftime("%A, %-d %B, %H:%M")
    body = "\n".join([
        f"Hi {args.name},",
        "",
        f"Gameweek 5 locks at the first kickoff — {locks} UK time.",
        "",
        "You have 3 of 10 tips in.",
        "",
        "Anything missing at lock is defaulted to the away side, which is rarely what you want.",
        "",
        "https://betmate.au/tipping",
        "",
        "— This is a TEST send, triggered by hand. It is not a real reminder, and no",
        "  reminder record was written, so nobody has been marked as already nudged.",
    ])

    resp = requests.post(
        RESEND_ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        data=json.dumps({
            "from": args.from_address,
            "to": [args.to],
            "subject": "BetMate: test of the tipping reminder email",
            "text": body,
        }),
        timeout=30,
    )
    if not resp.ok:
        print(f"FAILED {resp.status_code}: {resp.text[:400]}", file=sys.stderr)
        return 1
    print(f"sent to {args.to} from {args.from_address}")
    print(f"resend id: {resp.json().get('id')}")
    print("\nIf it does not arrive, check spam - and if it is in spam, the DKIM record")
    print("is the first thing to look at. It was silently truncated once before.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
