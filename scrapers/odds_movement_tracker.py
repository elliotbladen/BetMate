"""
Track odds movements against the Monday opening baseline.

Each run compares the current snapshot (latest.csv) against the Monday
09:00 baseline stored in Supabase (nrl_opening_baseline / afl_opening_baseline).
Movements are pushed to Supabase as odds_movements so Vercel can serve them.

Reads:
  data/odds_snapshots/latest.csv          ← current prices
  Supabase: nrl_opening_baseline          ← Monday 09:00 NRL prices
  Supabase: afl_opening_baseline          ← Monday 09:00 AFL prices

Writes:
  data/odds_movements/YYYY/YYYY-MM-DD.csv ← local archive
  data/odds_movements/latest.csv
  Supabase: odds_movements                ← consumed by Vercel UI
"""
# /// script
# dependencies = ["requests", "tzdata"]
# ///

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests as _requests

ROOT     = Path(__file__).resolve().parents[1]
SNAP_DIR = ROOT / "data" / "odds_snapshots"
MOVE_DIR = ROOT / "data" / "odds_movements"
ENV_PATH = ROOT / ".env.local"
LOCAL_TZ = ZoneInfo("Australia/Sydney")

FIELDNAMES = [
    "detected_date",
    "detected_time",
    "from_snapshot_time",
    "to_snapshot_time",
    "sport",
    "game_id",
    "home_team",
    "away_team",
    "commence_time",
    "bookmaker",
    "market",
    "outcome",
    "point",
    "old_price",
    "new_price",
    "change",
    "change_pct",
    "direction",
]


def _load_env() -> tuple[str, str]:
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    return (
        os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/"),
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
    )


def _side_for_outcome(row: dict) -> str | None:
    outcome = row.get("outcome", "")
    home    = row.get("home_team", "")
    away    = row.get("away_team", "")
    if outcome == home:            return "home"
    if outcome == away:            return "away"
    if outcome.lower() == "over":  return "over"
    if outcome.lower() == "under": return "under"
    return None


def _fetch_baseline(sport: str, url: str, service_key: str) -> dict:
    """Fetch Monday opening baseline from Supabase. Returns prices dict or {}."""
    key = f"{sport.lower()}_opening_baseline"
    try:
        resp = _requests.get(
            f"{url}/rest/v1/betmate_data_store",
            headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
            params={"key": f"eq.{key}", "select": "data"},
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json()
        if rows:
            return rows[0]["data"].get("prices", {})
    except Exception as exc:
        print(f"Could not fetch {key} from Supabase: {exc}")
    return {}


def read_latest_snapshot() -> list[dict]:
    path = SNAP_DIR / "latest.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def detect_movements_vs_baseline(
    current_rows: list[dict],
    baseline: dict,
    sport: str,
    min_pct: float,
) -> list[dict]:
    """Compare current snapshot rows against Monday baseline price map."""
    now           = datetime.now(LOCAL_TZ)
    detected_date = now.strftime("%Y-%m-%d")
    detected_time = now.strftime("%H:%M:%S")
    movements: list[dict] = []

    for row in current_rows:
        if row.get("sport") != sport:
            continue
        side = _side_for_outcome(row)
        if not side:
            continue

        key   = f"{row['game_id']}:{row['market']}:{row['bookmaker']}:{side}"
        entry = baseline.get(key)
        if not entry:
            continue

        old_price = float(entry["price"])
        new_price = float(row["price"])
        if old_price <= 0 or old_price == new_price:
            continue

        change     = new_price - old_price
        change_pct = (change / old_price) * 100
        if abs(change_pct) < min_pct:
            continue

        movements.append({
            "detected_date":      detected_date,
            "detected_time":      detected_time,
            "from_snapshot_time": entry.get("captured_at", "Monday"),
            "to_snapshot_time":   row.get("snapshot_time", detected_time),
            "sport":              sport,
            "game_id":            row["game_id"],
            "home_team":          row["home_team"],
            "away_team":          row["away_team"],
            "commence_time":      row["commence_time"],
            "bookmaker":          row["bookmaker"],
            "market":             row["market"],
            "outcome":            row["outcome"],
            "point":              row.get("point", ""),
            "old_price":          f"{old_price:.4f}",
            "new_price":          f"{new_price:.4f}",
            "change":             f"{change:.4f}",
            "change_pct":         f"{change_pct:.2f}",
            "direction":          "down" if change < 0 else "up",
            "side":               side,
            "key":                key,
        })

    return sorted(movements, key=lambda m: abs(float(m["change_pct"])), reverse=True)


def write_rows(path: Path, rows: list[dict], append: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and path.exists() else "w"
    with path.open(mode, newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        if mode == "w":
            writer.writeheader()
        writer.writerows({k: r.get(k, "") for k in FIELDNAMES} for r in rows)


def _push_movements_to_supabase(movements: list[dict], url: str, service_key: str) -> None:
    movement_map: dict[str, dict] = {}
    for m in movements:
        change_pct = float(m["change_pct"])
        movement_map[m["key"]] = {
            "direction":       m["direction"],
            "changePct":       change_pct,
            "oldPrice":        float(m["old_price"]),
            "newPrice":        float(m["new_price"]),
            "shortenedStrong": m["direction"] == "down" and abs(change_pct) >= 10,
        }

    base    = f"{url}/rest/v1/betmate_data_store"
    headers = {
        "apikey":        service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type":  "application/json",
    }
    try:
        # Always DELETE then INSERT — prevents duplicate rows accumulating
        # (merge-duplicates requires a UNIQUE constraint which we don't have)
        _requests.delete(base, headers=headers, params={"key": "eq.odds_movements"}, timeout=10)
        resp = _requests.post(base, headers=headers,
            data=json.dumps([{"key": "odds_movements", "data": movement_map}]),
            timeout=10)
        resp.raise_for_status()
        print(f"Pushed odds_movements to Supabase ({len(movement_map)} entries)")
    except Exception as exc:
        print(f"Supabase push failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-pct", type=float, default=0.0, help="Minimum change %% to record.")
    args = parser.parse_args()

    url, service_key = _load_env()
    if not url or not service_key:
        print("Supabase env vars not set — cannot fetch baseline or push movements.")
        return

    current_rows = read_latest_snapshot()
    if not current_rows:
        print("No latest.csv found — run odds_snapshot.py first.")
        return

    all_movements: list[dict] = []
    for sport in ("NRL", "AFL"):
        baseline = _fetch_baseline(sport, url, service_key)
        if not baseline:
            print(f"No {sport} baseline in Supabase — skipping (Monday snapshot not yet run?)")
            continue
        movements = detect_movements_vs_baseline(current_rows, baseline, sport, args.min_pct)
        print(f"{sport}: {len(movements)} movements vs Monday baseline")
        all_movements.extend(movements)

    if not all_movements:
        print("No movements detected.")
        # Still push empty map so Vercel clears stale arrows
        _push_movements_to_supabase([], url, service_key)
        return

    # Archive to local CSV
    now          = datetime.now(LOCAL_TZ)
    dated_path   = MOVE_DIR / now.strftime("%Y") / f"{now.strftime('%Y-%m-%d')}.csv"
    latest_path  = MOVE_DIR / "latest.csv"
    write_rows(dated_path, all_movements, append=True)
    write_rows(latest_path, all_movements, append=False)
    print(f"Wrote {dated_path} ({len(all_movements)} rows)")

    _push_movements_to_supabase(all_movements, url, service_key)


if __name__ == "__main__":
    main()
