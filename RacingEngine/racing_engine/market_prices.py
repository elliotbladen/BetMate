"""Append-only market snapshots and overround-free probability books."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .performance import utc_now
from .storage import RacingStore


REQUIRED = {"market_source", "source", "race_date", "track_slug", "race_number",
            "runner_number", "captured_at", "price_type", "decimal_odds"}


def import_csv(store: RacingStore, path: Path) -> dict[str, int]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    missing = REQUIRED - set(rows[0] if rows else [])
    if missing: raise ValueError(f"market CSV missing columns: {sorted(missing)}")
    inserted = 0; now = utc_now()
    for row in rows:
        odds = float(row["decimal_odds"])
        if odds <= 1: raise ValueError("decimal_odds must be greater than 1")
        store.connection.execute(
            """INSERT OR IGNORE INTO market_snapshots
               (market_source,source,race_date,track_slug,race_number,runner_number,captured_at,price_type,
                decimal_odds,available_volume,source_event_id,detail_json,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (row["market_source"], row["source"], row["race_date"], row["track_slug"], int(row["race_number"]),
             int(row["runner_number"]), row["captured_at"], row["price_type"], odds,
             float(row["available_volume"]) if row.get("available_volume") else None,
             row.get("source_event_id") or None, json.dumps({"import_file": path.name}, sort_keys=True), now))
        inserted += store.connection.execute("SELECT changes()").fetchone()[0]
    store.connection.commit(); return {"rows_read": len(rows), "rows_inserted": inserted}


def normalized_book(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows: return []
    raw = [1.0 / float(row["decimal_odds"]) for row in rows]; total = sum(raw)
    return [{**row, "raw_implied_probability": value,
             "normalized_probability": value / total, "book_overround": total - 1.0}
            for row, value in zip(rows, raw)]


def coverage(store: RacingStore) -> dict[str, Any]:
    row = store.connection.execute(
        """SELECT count(*) observations,count(DISTINCT race_date||'|'||track_slug||'|'||race_number) races,
                  min(captured_at) first_capture,max(captured_at) last_capture FROM market_snapshots""").fetchone()
    types = {item["price_type"]: item["n"] for item in store.connection.execute(
        "SELECT price_type,count(*) n FROM market_snapshots GROUP BY price_type")}
    return {**dict(row), "by_price_type": types,
            "comparison_status": "READY" if row["races"] else "AWAITING_TIMESTAMPED_MARKET_DATA"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path); parser.add_argument("--database", type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "racing_engine.sqlite")
    args = parser.parse_args(); store = RacingStore(args.database)
    try: result = {"import": import_csv(store, args.csv), "coverage": coverage(store)}
    finally: store.close()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__": main()
