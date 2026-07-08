"""
scripts/compute_snapshot_deltas.py

Computes fine-grained, snapshot-to-snapshot odds movements — every consecutive
pair, not just "now vs Monday's opening baseline" (that's what
odds_movement_tracker.py does, and it's still the right thing for the live UI
arrows). This script exists purely to build a research dataset for line-
movement analysis: for each (sport, game_id, bookmaker, market, outcome)
series, walk through every snapshot in chronological order and record the
delta between each consecutive pair, tagged with the exact time window it
happened in. That window is what tag_odds_movements.py matches against the
market-event log to attribute a move to a cause.

Reads:
  data/odds_snapshots/{season}/*.csv   (raw per-snapshot rows)

Writes:
  data/odds_movements/deltas/{season}_deltas.csv

Usage:
  uv run python scripts/compute_snapshot_deltas.py --season 2026
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDNAMES = [
    "sport", "game_id", "home_team", "away_team", "commence_time",
    "bookmaker", "market", "outcome", "point",
    "from_time", "to_time", "old_price", "new_price", "change", "change_pct", "direction",
]


def load_snapshots(season: int) -> list[dict]:
    snap_dir = ROOT / "data" / "odds_snapshots" / str(season)
    rows = []
    for path in sorted(snap_dir.glob("*.csv")):
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    r["_dt"] = datetime.strptime(
                        f"{r['snapshot_date']} {r['snapshot_time']}", "%Y-%m-%d %H:%M:%S"
                    )
                except Exception:
                    continue
                rows.append(r)
    return rows


def series_key(r: dict) -> tuple:
    return (r["sport"], r["game_id"], r["bookmaker"], r["market"], r["outcome"], r.get("point", ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    args = ap.parse_args()

    rows = load_snapshots(args.season)
    print(f"Loaded {len(rows)} raw snapshot rows")

    series: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        series[series_key(r)].append(r)

    deltas = []
    for key, points in series.items():
        points.sort(key=lambda r: r["_dt"])
        for a, b in zip(points, points[1:]):
            try:
                old_price = float(a["price"])
                new_price = float(b["price"])
            except (ValueError, KeyError):
                continue
            if old_price == 0:
                continue
            change = round(new_price - old_price, 4)
            if change == 0:
                continue
            deltas.append({
                "sport": b["sport"],
                "game_id": b["game_id"],
                "home_team": b["home_team"],
                "away_team": b["away_team"],
                "commence_time": b["commence_time"],
                "bookmaker": b["bookmaker"],
                "market": b["market"],
                "outcome": b["outcome"],
                "point": b.get("point", ""),
                "from_time": a["_dt"].isoformat(),
                "to_time": b["_dt"].isoformat(),
                "old_price": old_price,
                "new_price": new_price,
                "change": change,
                "change_pct": round(100 * change / old_price, 2),
                "direction": "up" if change > 0 else "down",
            })

    deltas.sort(key=lambda d: d["to_time"])

    out_dir = ROOT / "data" / "odds_movements" / "deltas"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.season}_deltas.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(deltas)

    print(f"Wrote {len(deltas)} deltas -> {out_path}")
    print(f"  {len(series)} distinct series, {sum(1 for p in series.values() if len(p) >= 2)} with 2+ snapshots")


if __name__ == "__main__":
    main()
