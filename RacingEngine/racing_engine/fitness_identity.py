"""Conservative durable identity linking for ingested fitness/trial rows."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Iterable

from .horse_identity import clean_name, identity_key
from .storage import RacingStore, utc_now

IDENTITY_VERSION = "fitness-trials-step4-v1"


def _candidates(store: RacingStore) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for row in store.connection.execute("SELECT horse_id, identity_key, canonical_name FROM horses"):
        out[row["identity_key"]].add(row["horse_id"])
        out[identity_key(row["canonical_name"])].add(row["horse_id"])
    for row in store.connection.execute("""SELECT a.horse_key, a.canonical_name, a.source_horse_name
            FROM horse_aliases a JOIN horses h ON h.horse_id=a.horse_key"""):
        out[identity_key(row["source_horse_name"])].add(row["horse_key"])
        out[identity_key(row["canonical_name"])].add(row["horse_key"])
    return out


def _provider_ids(store: RacingStore) -> dict[tuple[str, str], set[str]]:
    """Read optional provider IDs stored in horse detail JSON without guessing."""
    result: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in store.connection.execute("SELECT horse_id, detail_json FROM horses"):
        try:
            detail = json.loads(row["detail_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if not isinstance(detail, dict):
            continue
        for provider, key in (("racing_australia", "source_horse_id"), ("racing_com", "source_horse_id"), ("racing_nsw", "source_horse_id")):
            value = detail.get(provider, {}).get(key) if isinstance(detail.get(provider), dict) else None
            if value:
                result[(provider, str(value))].add(row["horse_id"])
    if store.connection.execute("SELECT 1 FROM sqlite_master WHERE name='trial_provider_profiles'").fetchone():
        for row in store.connection.execute('SELECT source_horse_id,horse_id FROM trial_provider_profiles'):
            result[('racing_com',row['source_horse_id'])].add(row['horse_id'])
    return result


def link_rows(store: RacingStore, rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Link rows and return linked/quarantined records; never auto-merges ambiguity."""
    names = _candidates(store)
    provider_ids = _provider_ids(store)
    available = {}
    for record in store.connection.execute("SELECT horse_id, detail_json FROM horses"):
        try:
            detail = json.loads(record["detail_json"] or "{}")
            profile = detail.get("racing_nsw", {}) if isinstance(detail, dict) else {}
            if isinstance(profile, dict) and profile.get("observed_at"):
                available[("racing_nsw",record["horse_id"])] = profile["observed_at"]
        except (ValueError, TypeError):
            continue
    if store.connection.execute("SELECT 1 FROM sqlite_master WHERE name='trial_provider_profiles'").fetchone():
        for record in store.connection.execute("SELECT horse_id,observed_at FROM trial_provider_profiles"):
            available[("racing_com",record["horse_id"])]=record["observed_at"]
    linked: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        source = str(row.get("source") or "unknown")
        source_name = str(row.get("horse_name") or row.get("source_horse_name") or "").strip()
        provider = str(row.get("provider") or source)
        source_id = row.get("source_horse_id") or row.get("provider_horse_id")
        provider_candidates = provider_ids.get((provider, str(source_id)), set()) if source_id else set()
        if len(provider_candidates) > 1:
            row.update({"identity_method": "ambiguous", "identity_confidence": 0.0,
                        "review_status": "quarantine", "quarantine_reason": "duplicate_provider_identity",
                        "candidate_horse_ids": sorted(provider_candidates)})
            quarantined.append(row)
            continue
        horse_id = next(iter(provider_candidates)) if provider_candidates else None
        method = "provider_id" if horse_id else None
        confidence = 1.0 if horse_id else 0.0
        cleaned, transformations = clean_name(source, source_name)
        key = identity_key(cleaned)
        name_candidates = names.get(key, set())
        if horse_id and name_candidates and horse_id not in name_candidates:
            row.update({"identity_method": "conflict", "identity_confidence": 0.0,
                        "review_status": "quarantine", "quarantine_reason": "provider_name_disagreement",
                        "candidate_horse_ids": sorted(name_candidates | provider_candidates)})
            quarantined.append(row)
            continue
        if not horse_id:
            candidates = names.get(key, set())
            if len(candidates) == 1:
                horse_id = next(iter(candidates)); method = "exact_identity_key"; confidence = 0.99
            elif len(candidates) > 1:
                row.update({"identity_method": "ambiguous", "identity_confidence": 0.0,
                            "review_status": "quarantine", "quarantine_reason": "multiple_horse_candidates",
                            "candidate_horse_ids": sorted(candidates), "cleaned_horse_name": cleaned})
                quarantined.append(row); continue
        if not horse_id:
            row.update({"identity_method": "unresolved", "identity_confidence": 0.0,
                        "review_status": "quarantine", "quarantine_reason": "no_registry_match",
                        "candidate_horse_ids": [], "cleaned_horse_name": cleaned})
            quarantined.append(row); continue
        if method == "provider_id" and (provider,horse_id) in available and row.get("effective_at"):
            # Resolving an old source today cannot make the identity available yesterday.
            row["effective_at"] = max((row["effective_at"], available[(provider,horse_id)]), key=datetime.fromisoformat)
        row.update({"horse_id": horse_id, "cleaned_horse_name": cleaned, "identity_method": method,
                    "identity_confidence": confidence, "review_status": "automatic",
                    "identity_version": IDENTITY_VERSION, "transformations": transformations})
        linked.append(row)
    return {"identity_version": IDENTITY_VERSION, "input_rows": len(linked) + len(quarantined),
            "linked_rows": linked, "quarantined_rows": quarantined,
            "linked": len(linked), "quarantined": len(quarantined)}


def persist_quarantine(store: RacingStore, rows: Iterable[dict[str, Any]], *, commit: bool = True) -> int:
    """Persist only unresolved/ambiguous rows for human review."""
    now = utc_now(); count = 0
    for row in rows:
        source = str(row.get("source") or "unknown")
        event_id = str(row.get("source_event_id") or row.get("event_id") or "")
        horse_name = str(row.get("horse_name") or row.get("source_horse_name") or "")
        evidence = {k: v for k, v in row.items() if k not in {"created_at", "collected_at", "effective_at", "raw_payload_hash"}}
        review_key = hashlib.sha256(json.dumps(evidence, sort_keys=True, default=str).encode()).hexdigest()
        cursor = store.connection.execute("""INSERT INTO fitness_identity_quarantine
          (review_key,source,source_event_id,source_horse_name,event_date,candidate_horse_ids_json,
           reason,source_url,raw_json,parser_version,created_at)
          VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(review_key) DO NOTHING""",
          (review_key, source, event_id, horse_name, row.get("event_date"),
           json.dumps(row.get("candidate_horse_ids", []), sort_keys=True),
           row.get("quarantine_reason", "unknown"), row.get("source_url"),
           json.dumps(row, sort_keys=True, default=str), row.get("parser_version", IDENTITY_VERSION), now))
        count += cursor.rowcount
    if commit:
        store.connection.commit()
    return count
