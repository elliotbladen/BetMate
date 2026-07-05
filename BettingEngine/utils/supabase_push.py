"""
Push data to the BetMate Supabase betmate_data_store table.

Requires in environment:
  NEXT_PUBLIC_SUPABASE_URL  — e.g. https://xyz.supabase.co
  SUPABASE_SERVICE_ROLE_KEY — service role key (bypasses RLS)

If either var is missing the push is silently skipped so local dev without
Supabase credentials is unaffected.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

log = logging.getLogger(__name__)

TABLE = "betmate_data_store"


def push(key: str, data: dict | list) -> bool:
    """Upsert data into betmate_data_store[key]. Returns True on success."""
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not url or not service_key:
        log.debug("Supabase env vars not set — skipping push for key=%s", key)
        return False

    try:
        import requests  # noqa: PLC0415

        payload = [{"key": key, "data": data, "updated_at": datetime.now(timezone.utc).isoformat()}]
        resp = requests.post(
            f"{url}/rest/v1/{TABLE}",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            data=json.dumps(payload),
            timeout=10,
        )
        resp.raise_for_status()
        log.info("Supabase push OK — key=%s (%d bytes)", key, len(resp.content))
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("Supabase push failed for key=%s: %s", key, exc)
        return False


def load_env(env_path: str | None = None) -> None:
    """Load .env.local from BetMate root into os.environ (for Task Scheduler)."""
    from pathlib import Path
    candidates = [
        Path(env_path) if env_path else None,
        Path(__file__).parent.parent.parent / ".env.local",
    ]
    for p in candidates:
        if p and p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
            return
