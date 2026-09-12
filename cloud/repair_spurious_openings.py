#!/usr/bin/env python3
"""Repair quote changes mislabelled as 'opening' by the unstable-paging bug.

THE BUG (fixed in odds_collector.py on 2026-09-12). Supabase.get_all() paged with
Range offsets and no ORDER BY. Range offsets without a stable sort are not stable,
so rows were silently skipped between pages. The collector's "what do I already
know about this quote" map therefore came back incomplete for every sport over the
1000-row page size, and a missed quote_key read as `prior is None` - which the
collector records as change_kind='opening'.

WHY IT MATTERS. A quote opens exactly once. 'opening' is the reference price this
project measures CLV against, so a false opening is not cosmetic - it silently
replaces a real price move, and it loses the previous_* values that make the move
measurable. Nothing consumes odds_quote_changes yet, which is precisely why this
is worth repairing now rather than after a model is fitted on it.

WHAT THIS DOES, per (sport, event, bookmaker, market, selection) series ordered by
quote_change_id:
  - the FIRST row keeps change_kind='opening'. It is the genuine one.
  - a later row labelled 'opening' whose values DIFFER from the preceding row was a
    real move: reclassify to line / price / line_and_price and backfill
    previous_line_value and previous_price_decimal from that preceding row.
  - a later row labelled 'opening' whose values are IDENTICAL to the preceding row
    records nothing at all - the collector only writes on change - so it is deleted.

Dry run by default. Pass --apply to write.

  python3 cloud/repair_spurious_openings.py            # report only
  python3 cloud/repair_spurious_openings.py --apply
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

import requests
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from odds_collector import Supabase, chunks  # noqa: E402

SPORTS = ("AFL", "NRL", "EPL", "EFL", "NFL", "UCL", "NBA")
SERIES = ("api_event_id", "bookmaker_key", "market_key", "selection_key")
FIELDS = ("quote_change_id,api_event_id,bookmaker_key,market_key,selection_key,"
          "line_value,price_decimal,change_kind,previous_line_value,previous_price_decimal,captured_at")


def same(a, b) -> bool:
    """Compare a line/price pair the way the collector's fingerprint does."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return float(a) == float(b)


def classify(prev: dict, row: dict) -> str:
    line_changed = not same(prev.get("line_value"), row.get("line_value"))
    price_changed = not same(prev.get("price_decimal"), row.get("price_decimal"))
    if line_changed and price_changed:
        return "line_and_price"
    if line_changed:
        return "line"
    return "price"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the repair (default is a dry run)")
    ap.add_argument("--backup-dir", default="data/market_repair_backups",
                    help="where to write the pre-change snapshot (always written with --apply)")
    args = ap.parse_args()

    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required", file=sys.stderr)
        return 2
    db = Supabase(url, key)

    # Every row this run touches is written out BEFORE anything changes. The delete
    # is otherwise irreversible, and a repair you cannot undo is a worse bug than
    # the one it fixes.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path(args.backup_dir)
    backup: dict[str, list] = {}

    total_fix, total_del = 0, 0
    for sport in SPORTS:
        rows = db.get_all("odds_quote_changes", {"sport": f"eq.{sport}", "select": FIELDS},
                          order="quote_change_id")
        series = collections.defaultdict(list)
        for row in rows:
            series[tuple(row[k] for k in SERIES)].append(row)

        to_fix, to_delete = [], []
        for _, hist in series.items():
            hist.sort(key=lambda r: r["quote_change_id"])
            for i, row in enumerate(hist):
                if i == 0 or row["change_kind"] != "opening":
                    continue
                prev = hist[i - 1]
                if same(prev["line_value"], row["line_value"]) and \
                   same(prev["price_decimal"], row["price_decimal"]):
                    to_delete.append(row["quote_change_id"])
                else:
                    to_fix.append({
                        "quote_change_id": row["quote_change_id"],
                        "change_kind": classify(prev, row),
                        "previous_line_value": prev["line_value"],
                        "previous_price_decimal": prev["price_decimal"],
                    })

        print(f"{sport:4}  rows={len(rows):6}  series={len(series):6}  "
              f"reclassify={len(to_fix):5}  delete={len(to_delete):5}")
        total_fix += len(to_fix)
        total_del += len(to_delete)

        if args.apply:
            by_id = {r["quote_change_id"]: r for r in rows}
            backup[sport] = {
                "reclassified": [by_id[r["quote_change_id"]] for r in to_fix],
                "deleted": [by_id[i] for i in to_delete],
            }
            backup_dir.mkdir(parents=True, exist_ok=True)
            path = backup_dir / f"quote_changes_repair_{stamp}.json"
            path.write_text(json.dumps(backup, indent=2, default=str), encoding="utf-8")

            for row in to_fix:
                qid = row.pop("quote_change_id")
                resp = requests.patch(
                    f"{db.base}/odds_quote_changes",
                    headers={**db.headers, "Prefer": "return=minimal"},
                    params={"quote_change_id": f"eq.{qid}"},
                    data=json.dumps(row), timeout=30,
                )
                db._check(resp)
            for batch in chunks([{"id": i} for i in to_delete], 100):
                ids = ",".join(str(b["id"]) for b in batch)
                resp = requests.delete(
                    f"{db.base}/odds_quote_changes",
                    headers={**db.headers, "Prefer": "return=minimal"},
                    params={"quote_change_id": f"in.({ids})"}, timeout=30,
                )
                db._check(resp)

    verb = "repaired" if args.apply else "WOULD repair (dry run — pass --apply)"
    print(f"\n{verb}: {total_fix} reclassified, {total_del} deleted")
    if args.apply:
        print(f"pre-change snapshot: {backup_dir / f'quote_changes_repair_{stamp}.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
