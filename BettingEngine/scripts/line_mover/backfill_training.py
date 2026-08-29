#!/usr/bin/env python3
"""
backfill_training.py — Label historical games with which team shortened (open→close).

Reads aussportsbetting xlsx for 2024-2025 (and optionally 2026), labels each game
with the actual shortening direction + totals movement. Outputs a training CSV for
Phase 2 XGBoost model.

Usage:
    python scripts/line_mover/backfill_training.py --sport AFL
    python scripts/line_mover/backfill_training.py --sport NRL
    python scripts/line_mover/backfill_training.py --sport ALL
"""

import argparse
import csv
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
TRAINING_DIR = ROOT / "data" / "line_movement" / "training"
TRAINING_DIR.mkdir(parents=True, exist_ok=True)


def label_games(sport: str) -> list:
    """Read xlsx and label each game with shortening direction."""
    if sport == "AFL":
        xlsx_path = ROOT / "outputs" / "afl_weekly_review" / "historical" / "latest.xlsx"
    else:
        xlsx_path = ROOT / "outputs" / "nrl_weekly_review" / "historical" / "latest.xlsx"

    if not xlsx_path.exists():
        print(f"ERROR: {xlsx_path} not found")
        return []

    df = pd.read_excel(xlsx_path, header=1)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    # 2024+ for training data
    df = df[df["Date"] >= "2024-01-01"]

    rows = []
    for _, row in df.iterrows():
        home = str(row.get("Home Team", "")).strip()
        away = str(row.get("Away Team", "")).strip()
        if not home or not away:
            continue

        try:
            ho = float(row.get("Home Odds Open", 0))
            hc = float(row.get("Home Odds Close", 0))
            ao = float(row.get("Away Odds Open", 0))
            ac = float(row.get("Away Odds Close", 0))
            if ho <= 0 or hc <= 0 or ao <= 0 or ac <= 0:
                continue
        except (TypeError, ValueError):
            continue

        game_date = str(row.get("Date", ""))[:10]
        year = int(game_date[:4]) if len(game_date) >= 4 else 0

        # Determine shortening
        home_shortened = hc < ho and ac >= ao
        away_shortened = ac < ao and hc >= ho

        if home_shortened:
            who_shortened = "HOME"
        elif away_shortened:
            who_shortened = "AWAY"
        else:
            who_shortened = "BOTH_OR_NEITHER"

        # Determine which is favourite (lower odds = fav)
        fav_side = "HOME" if ho < ao else "AWAY"

        # Home margin (from result if available)
        try:
            home_score = float(row.get("Home Score", 0))
            away_score = float(row.get("Away Score", 0))
            result_margin = home_score - away_score
        except (TypeError, ValueError):
            result_margin = 0

        # Totals
        try:
            to_val = float(row.get("Total Score Open", 0))
            tc = float(row.get("Total Score Close", 0))
        except (TypeError, ValueError):
            to_val, tc = 0, 0

        if to_val > 0 and tc > 0:
            if tc < to_val:
                totals_direction = "UNDERS"
            elif tc > to_val:
                totals_direction = "OVERS"
            else:
                totals_direction = "EVEN"
        else:
            totals_direction = "UNKNOWN"

        # ELO gap proxy: implied probability from opening odds
        home_implied = 1.0 / ho if ho > 0 else 0.5
        away_implied = 1.0 / ao if ao > 0 else 0.5
        elo_gap_proxy = (home_implied - away_implied) / (home_implied + away_implied)

        # Movement magnitude
        home_move_pct = ((hc - ho) / ho * 100) if ho > 0 else 0
        away_move_pct = ((ac - ao) / ao * 100) if ao > 0 else 0

        rows.append({
            "sport": sport,
            "date": game_date,
            "season": year,
            "home_team": home,
            "away_team": away,
            "home_odds_open": ho,
            "home_odds_close": hc,
            "away_odds_open": ao,
            "away_odds_close": ac,
            "total_open": to_val,
            "total_close": tc,
            "who_shortened": who_shortened,
            "totals_direction": totals_direction,
            "fav_side": fav_side,
            "elo_gap_proxy": round(elo_gap_proxy, 4),
            "home_move_pct": round(home_move_pct, 2),
            "away_move_pct": round(away_move_pct, 2),
            "result_margin": result_margin,
        })

    return rows


def main():
    parser = argparse.ArgumentParser(description="Backfill training data for line movement model")
    parser.add_argument("--sport", required=True, choices=["NRL", "AFL", "ALL"])
    args = parser.parse_args()

    sports = ["NRL", "AFL"] if args.sport == "ALL" else [args.sport]

    for sport in sports:
        print(f"\nBackfilling {sport}...")
        rows = label_games(sport)
        if not rows:
            print(f"  No data found for {sport}")
            continue

        out_path = TRAINING_DIR / f"{sport.lower()}_training_data.csv"
        fieldnames = list(rows[0].keys())
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        # Stats
        total = len(rows)
        home_ct = sum(1 for r in rows if r["who_shortened"] == "HOME")
        away_ct = sum(1 for r in rows if r["who_shortened"] == "AWAY")
        both_ct = sum(1 for r in rows if r["who_shortened"] == "BOTH_OR_NEITHER")
        fav_shortened = sum(1 for r in rows if r["who_shortened"] == r["fav_side"])

        print(f"  Total games: {total}")
        print(f"  HOME shortened: {home_ct} ({home_ct/total*100:.1f}%)")
        print(f"  AWAY shortened: {away_ct} ({away_ct/total*100:.1f}%)")
        print(f"  BOTH/NEITHER:   {both_ct} ({both_ct/total*100:.1f}%)")
        print(f"  Favourite shortened: {fav_shortened}/{home_ct+away_ct} "
              f"({fav_shortened/(home_ct+away_ct)*100:.1f}% of directional moves)")
        print(f"  Saved: {out_path}")

        # Season breakdown
        by_season = {}
        for r in rows:
            s = r["season"]
            if s not in by_season:
                by_season[s] = {"total": 0, "home": 0, "away": 0}
            by_season[s]["total"] += 1
            if r["who_shortened"] == "HOME":
                by_season[s]["home"] += 1
            elif r["who_shortened"] == "AWAY":
                by_season[s]["away"] += 1

        print(f"\n  Season breakdown:")
        for s in sorted(by_season):
            d = by_season[s]
            print(f"    {s}: {d['total']} games — HOME {d['home']} / AWAY {d['away']}")


if __name__ == "__main__":
    main()
