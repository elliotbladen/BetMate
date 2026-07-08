"""
scripts/tag_odds_movements.py

Joins fine-grained odds deltas (compute_snapshot_deltas.py) against the
market-event log (build_market_event_log.py) to attribute each price move
to a likely cause: does an injury/emotional/team-news event for one of the
two teams fall inside the [from_time, to_time] window of the move?

This is deliberately a coarse first pass — a shared time window is not
proof of causation, especially since our snapshot cadence (3x/day) means
windows can span several hours. The point is to start building a labelled
dataset: which moves had a plausible news trigger vs which were
"unexplained" (public/sharp money flow, or a driver we don't scrape).
That labelled set is what a future line-movement model gets trained on.

Reads:
  data/odds_movements/deltas/{season}_deltas.csv
  data/market_events/{season}_events.csv

Writes:
  data/odds_movements/tagged/{season}_tagged.csv

Usage:
  uv run python scripts/tag_odds_movements.py --season 2026
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Only tag moves above this magnitude -- tiny book-to-book noise isn't worth
# attributing a cause to, and dilutes the labelled set with junk.
MIN_CHANGE_PCT = 3.0

# Betting-exchange lay markets (h2h_lay) occasionally tick to placeholder
# prices (e.g. 110.0 = no liquidity) which show up as multi-thousand-percent
# "moves" -- not real market signal. Drop anything beyond this magnitude.
MAX_CHANGE_PCT = 300.0

FIELDNAMES = [
    "sport", "game_id", "home_team", "away_team", "commence_time",
    "bookmaker", "market", "outcome", "point",
    "from_time", "to_time", "old_price", "new_price", "change", "change_pct", "direction",
    "driver_count", "drivers",
]


def nickname(team: str) -> str:
    return team.split()[-1].lower() if team else ""


def load_events(season: int) -> list[dict]:
    path = ROOT / "data" / "market_events" / f"{season}_events.csv"
    if not path.exists():
        return []
    events = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                r["_dt"] = datetime.fromisoformat(r["scraped_at"].replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                continue
            r["_nick"] = nickname(r.get("team", ""))
            events.append(r)
    events.sort(key=lambda e: e["_dt"])
    return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    args = ap.parse_args()

    delta_path = ROOT / "data" / "odds_movements" / "deltas" / f"{args.season}_deltas.csv"
    if not delta_path.exists():
        print(f"No deltas file at {delta_path} -- run compute_snapshot_deltas.py first")
        return

    events = load_events(args.season)
    print(f"Loaded {len(events)} market events")

    tagged = []
    with open(delta_path, newline="", encoding="utf-8") as fh:
        deltas = list(csv.DictReader(fh))
    print(f"Loaded {len(deltas)} deltas")

    n_significant = 0
    n_tagged = 0
    for d in deltas:
        pct = abs(float(d["change_pct"]))
        if pct < MIN_CHANGE_PCT or pct > MAX_CHANGE_PCT:
            continue
        n_significant += 1
        try:
            from_dt = datetime.fromisoformat(d["from_time"])
            to_dt = datetime.fromisoformat(d["to_time"])
        except Exception:
            continue

        home_nick = nickname(d["home_team"])
        away_nick = nickname(d["away_team"])

        matches = [
            e for e in events
            if e["sport"] == d["sport"]
            and from_dt <= e["_dt"] <= to_dt
            and (e["_nick"] in (home_nick, away_nick) or e["_nick"] == "")
        ]

        row = {k: d[k] for k in FIELDNAMES if k in d}
        row["driver_count"] = len(matches)
        row["drivers"] = "; ".join(
            f"{e['event_type']}:{e['team']}:{e.get('player','')}" for e in matches
        ) if matches else "unexplained"
        tagged.append(row)
        if matches:
            n_tagged += 1

    out_dir = ROOT / "data" / "odds_movements" / "tagged"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.season}_tagged.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(tagged)

    print(f"Wrote {len(tagged)} significant moves (>= {MIN_CHANGE_PCT}% change) -> {out_path}")
    print(f"  Tagged with a plausible driver: {n_tagged} ({100*n_tagged/max(n_significant,1):.0f}%)")
    print(f"  Unexplained: {n_significant - n_tagged}")


if __name__ == "__main__":
    main()
