"""Step 5 deterministic deduplication and quality gates for fitness events."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Iterable

QUALITY_VERSION = "fitness-trials-step5-v1"

_REQUIRED = ("source", "source_event_id", "horse_id", "event_date")


def _payload_hash(row: dict[str, Any]) -> str:
    stable = {k: v for k, v in row.items() if k not in {"created_at", "collected_at"}}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def _valid_date(value: Any) -> bool:
    try:
        date.fromisoformat(str(value))
        return True
    except (TypeError, ValueError):
        return False


def quality_gate(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Return accepted unique rows and quarantined quality failures.

    Duplicates with identical payloads collapse deterministically; conflicting
    payloads for the same source/event/horse are quarantined rather than chosen.
    """
    accepted: dict[tuple[str, str, str], dict[str, Any]] = {}
    quarantined: list[dict[str, Any]] = []
    duplicate_count = 0
    for raw in rows:
        row = dict(raw)
        reasons: list[str] = []
        for field in _REQUIRED:
            if not str(row.get(field) or "").strip():
                reasons.append(f"missing_{field}")
        if row.get("event_type") not in (None, "official_trial", "jumpout", "exhibition_gallop", "trackwork", "race"):
            reasons.append("invalid_event_type")
        if row.get("event_date") and not _valid_date(row["event_date"]):
            reasons.append("invalid_event_date")
        key = (str(row.get("source") or ""), str(row.get("source_event_id") or ""), str(row.get("horse_id") or ""))
        digest = str(row.get("payload_hash") or _payload_hash(row))
        row.update({"payload_hash": digest, "quality_version": QUALITY_VERSION})
        if reasons:
            row.update({"quality_status": "quarantine", "quality_reasons": reasons})
            quarantined.append(row); continue
        previous = accepted.get(key)
        if previous is None:
            accepted[key] = row; continue
        if previous["payload_hash"] == digest:
            duplicate_count += 1
            continue
        conflict = dict(row)
        conflict.update({"quality_status": "quarantine", "quality_reasons": ["conflicting_duplicate_payload"],
                         "existing_payload_hash": previous["payload_hash"]})
        quarantined.append(conflict)
    return {"quality_version": QUALITY_VERSION, "input_rows": len(accepted) + len(quarantined) + duplicate_count,
            "accepted_rows": list(accepted.values()), "quarantined_rows": quarantined,
            "accepted": len(accepted), "quarantined": len(quarantined), "identical_duplicates": duplicate_count}
