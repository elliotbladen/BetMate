"""Conservative, auditable horse identity registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .storage import RacingStore, utc_now


ROOT = Path(__file__).resolve().parents[1]
IDENTITY_VERSION = "horse-identity-v1.0"
NAMESPACE = uuid.UUID("19f52716-ef0c-4ee3-8398-d0e95ed9f931")
COUNTRY_SUFFIX = re.compile(r"\s*\((AUS|NZ|IRE|GB|FR|USA|JPN|SAF|ARG|BRZ|GER|ITY)\)\s*$", re.I)
RNSW_LAYOUT_SUFFIX = re.compile(r"\s+\d{1,2}\s+\d{2,3}(?:\.\d+)?\s*$")


def clean_name(source: str, source_name: str) -> tuple[str, list[str]]:
    value = re.sub(r"\s+", " ", source_name).strip()
    changes: list[str] = []
    if source == "rnsw-authorised" and RNSW_LAYOUT_SUFFIX.search(value):
        value = RNSW_LAYOUT_SUFFIX.sub("", value).strip()
        changes.append("removed_rnsw_position_time_layout_suffix")
    if COUNTRY_SUFFIX.search(value):
        value = COUNTRY_SUFFIX.sub("", value).strip()
        changes.append("removed_registered_country_suffix")
    return value, changes


def identity_key(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", ascii_value)


def durable_id(key: str) -> str:
    return "hrs_" + uuid.uuid5(NAMESPACE, key).hex


def _canonical(observations: list[dict[str, Any]]) -> str:
    # Prefer a clean mixed-case Racing.com spelling, then the most common clean
    # spelling. Country suffixes and PDF debris have already been removed.
    candidates = [row["cleaned_name"] for row in observations if row["source"].startswith("racing-com")]
    if not candidates:
        candidates = [row["cleaned_name"] for row in observations]
    counts = Counter(candidates)
    chosen = sorted(counts, key=lambda value: (-counts[value], value.lower(), value))[0]
    return chosen.title() if chosen.isupper() else chosen


def build_registry(store: RacingStore) -> dict[str, Any]:
    rows = store.connection.execute(
        """SELECT source,race_date,track_slug,race_number,runner_number,runner_name
             FROM runner_results ORDER BY race_date,track_slug,race_number,runner_number,source""").fetchall()
    observations: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    for row in rows:
        cleaned, changes = clean_name(row["source"], row["runner_name"])
        key = identity_key(cleaned)
        observation = {**dict(row), "cleaned_name": cleaned, "identity_key": key, "changes": changes}
        observations.append(observation)
        if len(key) < 3:
            reviews.append({**observation, "reason": "empty_or_too_short_identity_key"})
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        if len(row["identity_key"]) >= 3:
            grouped[row["identity_key"]].append(row)
    now = utc_now()
    created = linked = 0
    for key, group in grouped.items():
        horse_id = durable_id(key)
        canonical = _canonical(group)
        existing = store.connection.execute("SELECT horse_id FROM horses WHERE identity_key=?", (key,)).fetchone()
        store.connection.execute(
            """INSERT INTO horses (horse_id,canonical_name,identity_key,identity_status,detail_json,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?) ON CONFLICT(identity_key) DO UPDATE SET canonical_name=excluded.canonical_name,
                 identity_status=excluded.identity_status,detail_json=excluded.detail_json,updated_at=excluded.updated_at
               WHERE horses.identity_status != 'reviewed'""",
            (horse_id, canonical, key, "automatic", json.dumps({"identity_version": IDENTITY_VERSION,
             "observations": len(group), "sources": sorted({row["source"] for row in group})}, sort_keys=True), now, now))
        created += int(existing is None)
        for row in group:
            method = "exact_clean_name" if not row["changes"] else "+".join(row["changes"])
            detail = {"identity_version": IDENTITY_VERSION, "identity_key": key, "transformations": row["changes"]}
            store.connection.execute(
                """INSERT INTO runner_horse_links
                   (source,race_date,track_slug,race_number,runner_number,horse_id,source_horse_name,
                    cleaned_horse_name,link_method,confidence,review_status,detail_json,linked_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(source,race_date,track_slug,race_number,runner_number)
                   DO UPDATE SET horse_id=excluded.horse_id,source_horse_name=excluded.source_horse_name,
                     cleaned_horse_name=excluded.cleaned_horse_name,link_method=excluded.link_method,
                     confidence=excluded.confidence,review_status=excluded.review_status,
                     detail_json=excluded.detail_json,linked_at=excluded.linked_at
                   WHERE runner_horse_links.review_status != 'reviewed'""",
                (row["source"], row["race_date"], row["track_slug"], row["race_number"], row["runner_number"],
                 horse_id, row["runner_name"], row["cleaned_name"], method, 1.0, "automatic",
                 json.dumps(detail, sort_keys=True), now))
            store.connection.execute(
                """INSERT INTO horse_aliases (source,source_horse_name,horse_key,canonical_name,review_status,detail_json,updated_at)
                   VALUES (?,?,?,?,?,?,?) ON CONFLICT(source,source_horse_name) DO UPDATE SET
                     horse_key=excluded.horse_key,canonical_name=excluded.canonical_name,
                     review_status=excluded.review_status,detail_json=excluded.detail_json,updated_at=excluded.updated_at
                   WHERE horse_aliases.review_status != 'reviewed'""",
                (row["source"], row["runner_name"], horse_id, canonical, "automatic", json.dumps(detail, sort_keys=True), now))
            linked += 1
    for row in reviews:
        review_key = hashlib.sha256(f"{row['source']}\0{row['runner_name']}".encode()).hexdigest()
        store.connection.execute(
            """INSERT INTO horse_identity_reviews
               (review_key,source,source_horse_name,proposed_identity_key,reason,status,detail_json,created_at)
               VALUES (?,?,?,?,?,'open',?,?) ON CONFLICT(review_key) DO UPDATE SET
                 proposed_identity_key=excluded.proposed_identity_key,reason=excluded.reason,detail_json=excluded.detail_json""",
            (review_key, row["source"], row["runner_name"], row["identity_key"], row["reason"],
             json.dumps({"identity_version": IDENTITY_VERSION}, sort_keys=True), now))
    store.connection.commit()
    transformed = Counter(change for row in observations for change in row["changes"])
    cross_source = sum(len({row["source"] for row in group}) > 1 for group in grouped.values())
    return {"identity_version": IDENTITY_VERSION, "runner_rows": len(rows), "linked_rows": linked,
            "horses": len(grouped), "new_horses": created, "open_reviews": len(reviews),
            "cross_source_horses": cross_source, "transformations": dict(sorted(transformed.items()))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    store = RacingStore(args.database)
    try:
        report = build_registry(store)
    finally:
        store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
