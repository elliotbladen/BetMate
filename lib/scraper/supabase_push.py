"""
lib/scraper/supabase_push.py

Shared helper: upsert a JSON payload into the betmate_data_store Supabase table.
Called by scrapers after writing their local JSON file.

Requires in environment (loaded from .env.local by Task Scheduler wrappers):
  NEXT_PUBLIC_SUPABASE_URL   — e.g. https://xyz.supabase.co
  SUPABASE_SERVICE_ROLE_KEY  — service role key (bypasses RLS for writes)

If either var is missing, the push is silently skipped so local dev is unaffected.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

log = logging.getLogger(__name__)

BETMATE_DATA_STORE = "betmate_data_store"


def push(key: str, data: dict | list) -> bool:
    """Upsert data into betmate_data_store[key]. Returns True on success."""
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not url or not service_key:
        log.debug("Supabase env vars not set — skipping remote push for key=%s", key)
        return False

    try:
        import requests  # noqa: PLC0415

        endpoint = f"{url}/rest/v1/{BETMATE_DATA_STORE}"
        payload = [{
            "key": key,
            "data": data,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }]
        resp = requests.post(
            endpoint,
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
