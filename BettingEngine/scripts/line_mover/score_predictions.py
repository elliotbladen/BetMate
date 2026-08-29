#!/usr/bin/env python3
"""
score_predictions.py — Score line movement predictions against actual open→close movements.

Run after closing lines are available (typically Tuesday for the previous week's games).
Reads predictions from data/line_movement/predictions/ and actual movements from
the aussportsbetting xlsx.

Usage:
    python scripts/line_mover/score_predictions.py --sport AFL --round 23 --season 2026
    python scripts/line_mover/score_predictions.py --sport NRL --round 24 --season 2026
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "line_movement"
PREDICTIONS_DIR = DATA_DIR / "predictions"
RESULTS_DIR = DATA_DIR / "results"
ACCURACY_DIR = DATA_DIR / "accuracy"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
ACCURACY_DIR.mkdir(parents=True, exist_ok=True)


def load_actual_movements(sport: str, season: int, rnd: int) -> list:
    """Load actual open→close movements from aussportsbetting xlsx for a specific round."""
    if sport == "AFL":
        xlsx_path = ROOT / "outputs" / "afl_weekly_review" / "historical" / "latest.xlsx"
    else:
        xlsx_path = ROOT / "outputs" / "nrl_weekly_review" / "historical" / "latest.xlsx"

    if not xlsx_path.exists():
        print(f"ERROR: {xlsx_path} not found")
        return []

    df = pd.read_excel(xlsx_path, header=1)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Filter to approximate round dates (within season)
    df = df[df["Date"].dt.year == season]

    actuals = []
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

        # Totals
        try:
            to_val = float(row.get("Total Score Open", 0))
            tc = float(row.get("Total Score Close", 0))
        except (TypeError, ValueError):
            to_val, tc = 0, 0

        home_shortened = hc < ho and ac >= ao
        away_shortened = ac < ao and hc >= ho

        if home_shortened:
            who_shortened = "HOME"
        elif away_shortened:
            who_shortened = "AWAY"
        else:
            who_shortened = "BOTH_OR_NEITHER"

        if to_val > 0 and tc > 0:
            if tc < to_val:
                totals_actual = "UNDERS"
            elif tc > to_val:
                totals_actual = "OVERS"
            else:
                totals_actual = "EVEN"
        else:
            totals_actual = "UNKNOWN"

        actuals.append({
            "home_team": home,
            "away_team": away,
            "home_open": ho, "home_close": hc,
            "away_open": ao, "away_close": ac,
            "total_open": to_val, "total_close": tc,
            "who_shortened": who_shortened,
            "totals_actual": totals_actual,
            "date": str(row.get("Date", ""))[:10],
        })

    return actuals


def match_prediction_to_actual(pred: dict, actuals: list) -> dict | None:
    """Match a prediction to its actual result by team name fuzzy matching."""
    pred_home = pred["home_team"].split()[-1].lower()
    pred_away = pred["away_team"].split()[-1].lower()

    for actual in actuals:
        act_home = actual["home_team"].split()[-1].lower()
        act_away = actual["away_team"].split()[-1].lower()

        if (pred_home in act_home or act_home in pred_home) and \
           (pred_away in act_away or act_away in pred_away):
            return actual

        # Try reversed (sometimes home/away swaps in different datasets)
        if (pred_home in act_away or act_away in pred_home) and \
           (pred_away in act_home or act_home in pred_away):
            return actual

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", required=True, choices=["NRL", "AFL"])
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--season", type=int, default=2026)
    args = parser.parse_args()

    sport = args.sport
    rnd = args.round
    season = args.season

    # Load predictions
    pred_path = None
    for f in sorted(PREDICTIONS_DIR.glob(f"{sport.lower()}_r{rnd}_*.json")):
        pred_path = f
    if not pred_path:
        pred_path = PREDICTIONS_DIR / f"{sport.lower()}_latest.json"
    if not pred_path.exists():
        print(f"ERROR: No predictions found for {sport} R{rnd}")
        sys.exit(1)

    with open(pred_path) as f:
        pred_data = json.load(f)

    predictions = pred_data.get("predictions", [])
    if not predictions:
        print("ERROR: No predictions in file")
        sys.exit(1)

    # Load actuals
    actuals = load_actual_movements(sport, season, rnd)
    if not actuals:
        print(f"WARNING: No actual movements found for {sport} R{rnd} {season}")
        print("The aussportsbetting xlsx may not have this round's data yet.")
        sys.exit(1)

    # Score each prediction
    results = []
    correct = 0
    total = 0
    totals_correct = 0
    totals_total = 0

    print(f"\n{'='*80}")
    print(f"  SCORING — {sport} R{rnd} {season}")
    print(f"{'='*80}\n")

    print(f"{'Game':<40} {'Predicted':<15} {'Actual':<15} {'Result':>8}  {'Totals':>15}")
    print("-" * 95)

    for pred in predictions:
        actual = match_prediction_to_actual(pred, actuals)
        if not actual:
            print(f"  {pred['home_team'].split()[-1]} vs {pred['away_team'].split()[-1]:<30} "
                  f"{'NO MATCH':<15}")
            continue

        pred_dir = pred["direction"]
        act_dir = actual["who_shortened"]

        if act_dir == "BOTH_OR_NEITHER":
            hit = "PUSH"
        elif pred_dir == act_dir:
            hit = "HIT"
            correct += 1
        else:
            hit = "MISS"

        total += 1

        # Totals scoring
        pred_tot = pred.get("totals_prediction", "EVEN")
        act_tot = actual.get("totals_actual", "UNKNOWN")
        if act_tot == "UNKNOWN" or pred_tot == "EVEN":
            tot_hit = "-"
        elif pred_tot == act_tot:
            tot_hit = "HIT"
            totals_correct += 1
            totals_total += 1
        else:
            tot_hit = "MISS"
            totals_total += 1

        game_label = f"{pred['home_team'].split()[-1]} vs {pred['away_team'].split()[-1]}"
        print(f"  {game_label:<38} {pred_dir:<15} {act_dir:<15} {hit:>8}  {pred_tot:>7}→{act_tot:<7} {tot_hit}")

        results.append({
            "home_team": pred["home_team"],
            "away_team": pred["away_team"],
            "predicted_direction": pred_dir,
            "predicted_team": pred["prediction"],
            "confidence": pred["confidence"],
            "actual_direction": act_dir,
            "hit": hit,
            "totals_predicted": pred_tot,
            "totals_actual": act_tot,
            "totals_hit": tot_hit,
            "home_odds_open": actual["home_open"],
            "home_odds_close": actual["home_close"],
            "away_odds_open": actual["away_open"],
            "away_odds_close": actual["away_close"],
        })

    # Summary
    pct = (correct / total * 100) if total > 0 else 0
    tot_pct = (totals_correct / totals_total * 100) if totals_total > 0 else 0

    print(f"\n{'='*80}")
    print(f"  SHORTENING: {correct}/{total} correct ({pct:.1f}%)  |  Target: 66%")
    print(f"  TOTALS:     {totals_correct}/{totals_total} correct ({tot_pct:.1f}%)")
    print(f"{'='*80}\n")

    # Save results
    output = {
        "sport": sport, "season": season, "round": rnd,
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "shortening_correct": correct, "shortening_total": total,
        "shortening_pct": round(pct, 1),
        "totals_correct": totals_correct, "totals_total": totals_total,
        "totals_pct": round(tot_pct, 1),
        "results": results,
    }

    date_str = datetime.now().strftime("%Y-%m-%d")
    out_path = RESULTS_DIR / f"{sport.lower()}_r{rnd}_{date_str}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    # Update running accuracy
    update_running_accuracy(sport, rnd, correct, total, totals_correct, totals_total)

    print(f"Results saved: {out_path}")


def update_running_accuracy(sport: str, rnd: int, correct: int, total: int,
                            tot_correct: int, tot_total: int):
    """Append to running accuracy CSV."""
    csv_path = ACCURACY_DIR / f"{sport.lower()}_accuracy_2026.csv"
    write_header = not csv_path.exists()

    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["round", "date", "correct", "total", "pct",
                             "tot_correct", "tot_total", "tot_pct",
                             "running_correct", "running_total", "running_pct"])

        # Read existing for running totals
        running_correct = correct
        running_total = total
        if csv_path.exists():
            with open(csv_path) as rf:
                reader = csv.DictReader(rf)
                for row in reader:
                    try:
                        running_correct = int(row.get("running_correct", 0)) + correct
                        running_total = int(row.get("running_total", 0)) + total
                    except (ValueError, TypeError):
                        pass

        running_pct = (running_correct / running_total * 100) if running_total > 0 else 0
        pct = (correct / total * 100) if total > 0 else 0
        tot_pct = (tot_correct / tot_total * 100) if tot_total > 0 else 0

        writer.writerow([
            rnd, datetime.now().strftime("%Y-%m-%d"),
            correct, total, f"{pct:.1f}",
            tot_correct, tot_total, f"{tot_pct:.1f}",
            running_correct, running_total, f"{running_pct:.1f}",
        ])


if __name__ == "__main__":
    main()
