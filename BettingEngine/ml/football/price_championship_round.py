#!/usr/bin/env python3
"""Price the current Championship card and report the player shadow honestly."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ml.football.price_match import price_match

ROOT = Path(__file__).resolve().parents[2]
ODDS = ROOT.parent / "data" / "odds_snapshots" / "latest.csv"
OUT = ROOT / "outputs" / "football" / "championship"
DB = ROOT / "ml" / "football" / "data" / "championship" / "player_layer" / "availability.sqlite"
MODEL = ROOT / "ml" / "football" / "data" / "championship" / "player_layer" / "player_shadow.joblib"

TEAM_MAP = {
    "Wolverhampton Wanderers": "Wolves", "Blackburn Rovers": "Blackburn",
    "Bolton Wanderers": "Bolton", "Preston North End": "Preston",
    "Charlton Athletic": "Charlton", "Lincoln City": "Lincoln",
    "Norwich City": "Norwich", "West Bromwich Albion": "West Brom",
    "Queens Park Rangers": "QPR", "Stoke City": "Stoke", "Swansea City": "Swansea",
    "Sheffield United": "Sheffield United", "Birmingham City": "Birmingham",
    "West Ham United": "West Ham", "Cardiff City": "Cardiff", "Wrexham AFC": "Wrexham",
}


def best_prices(rows: pd.DataFrame, home: str, away: str) -> dict:
    h2h = rows[rows.market.eq("h2h")]
    totals = rows[rows.market.eq("totals")]
    def best(frame, outcome):
        vals = frame.loc[frame.outcome.eq(outcome), "price"]
        return float(vals.max()) if len(vals) else 0.0
    return {"home": best(h2h, home), "draw": best(h2h, "Draw"), "away": best(h2h, away),
            "over25": best(totals[totals.point.eq(2.5)], "Over")}


def player_shadow_status(home: str, away: str) -> dict:
    counts = {"updates": 0, "snapshots": 0, "appearances": 0}
    if DB.exists():
        with sqlite3.connect(DB) as conn:
            counts["updates"] = conn.execute("SELECT count(*) FROM availability_updates").fetchone()[0]
            counts["snapshots"] = conn.execute("SELECT count(*) FROM match_snapshots").fetchone()[0]
            counts["appearances"] = conn.execute("SELECT count(*) FROM observed_appearances").fetchone()[0]
    reasons = []
    if not MODEL.exists(): reasons.append("no_trained_player_model")
    if counts["updates"] == 0: reasons.append("no_timestamped_availability_updates")
    if counts["appearances"] == 0: reasons.append("no_historical_lineup_minutes")
    return {"status": "ABSTAIN" if reasons else "READY", "reasons": reasons, "counts": counts,
            "home": home, "away": away, "model_path": str(MODEL)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now().date().isoformat())
    ap.add_argument("--matchweek", type=int, default=1)
    ap.add_argument("--all-upcoming", action="store_true")
    args = ap.parse_args()
    raw = pd.read_csv(ODDS)
    raw = raw[raw.sport.astype(str).str.upper().eq("CHAMPIONSHIP")].copy()
    raw["commence_time"] = pd.to_datetime(raw.commence_time, utc=True)
    cutoff = pd.Timestamp(args.date, tz="UTC")
    end = cutoff + pd.Timedelta(days=7 if args.all_upcoming else 1)
    raw = raw[(raw.commence_time >= cutoff) & (raw.commence_time < end)]
    rows = []
    for (_, home_full, away_full, kickoff), game in raw.groupby(["game_id", "home_team", "away_team", "commence_time"]):
        home, away = TEAM_MAP.get(home_full, home_full), TEAM_MAP.get(away_full, away_full)
        market = best_prices(game, home_full, away_full)
        with contextlib.redirect_stdout(io.StringIO()):
            normal = price_match(home, away, as_of=datetime.fromisoformat(args.date), league="championship",
                                 matchweek=args.matchweek, mkt_home=market["home"], mkt_draw=market["draw"],
                                 mkt_away=market["away"], mkt_over25=market["over25"])
        rows.append({"kickoff": kickoff.isoformat(), "normal": normal,
                     "player_shadow": player_shadow_status(home, away), "market": market})
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "league": "championship",
               "matchweek": args.matchweek, "games": rows}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"round_price_{args.date}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved {path}")
    for row in rows:
        n, s = row["normal"], row["player_shadow"]
        print(f"{n['home']} v {n['away']}: normal {n['fair_home']:.2f}/{n['fair_draw']:.2f}/{n['fair_away']:.2f}; player shadow {s['status']}")


if __name__ == "__main__":
    main()
