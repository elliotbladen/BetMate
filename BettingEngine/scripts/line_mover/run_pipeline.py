#!/usr/bin/env python3
"""
run_pipeline.py — Orchestrate the full line movement prediction pipeline.

Runs all steps in order:
1. Scrape ladder positions
2. Scrape team lists (ins/outs)
3. Run predictions
4. (Optional) Score previous round's predictions

Usage:
    # Full pipeline for AFL (run Thursday ~6:25pm after team lists)
    python scripts/line_mover/run_pipeline.py --sport AFL --round 23 --season 2026

    # Full pipeline for NRL (run Tuesday ~4:05pm after team lists)
    python scripts/line_mover/run_pipeline.py --sport NRL --round 24 --season 2026

    # Score previous round
    python scripts/line_mover/run_pipeline.py --sport AFL --round 22 --season 2026 --score-only

    # Skip team list scraping (if already done)
    python scripts/line_mover/run_pipeline.py --sport AFL --round 23 --season 2026 --skip-scrape
"""

import argparse
import csv
import glob
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent


def detect_round(sport: str, season: int) -> int:
    """Auto-detect current round from fixture files or DB."""
    if sport == "AFL":
        # Find highest round with a fixture CSV
        prep_dir = ROOT / "outputs" / "afl_round_prep"
        rounds = []
        for d in prep_dir.glob(f"r*_{season}"):
            name = d.name
            try:
                r = int(name.split("_")[0][1:])
                rounds.append(r)
            except ValueError:
                continue
        if rounds:
            latest = max(rounds)
            fixture = prep_dir / f"r{latest}_{season}" / f"fixture_r{latest}_{season}.csv"
            try:
                dates = [date.fromisoformat(row["date"]) for row in csv.DictReader(fixture.open())]
                if dates and max(dates) < date.today():
                    return latest + 1
            except (OSError, ValueError, KeyError):
                pass
            return latest
    else:
        # NRL: choose the first round that has not started. MAX(round) points
        # at a future fixture and caused team lists for the current week to be
        # paired with the following round.
        try:
            import sqlite3
            db_path = ROOT / "data" / "model.db"
            if db_path.exists():
                conn = sqlite3.connect(db_path)
                row = conn.execute("""
                    SELECT round_number
                    FROM matches
                    WHERE season = ? AND sport = 'NRL'
                      AND date(match_date) >= date('now', 'localtime')
                    ORDER BY date(match_date), round_number
                    LIMIT 1
                """, (season,)).fetchone()
                conn.close()
                if row and row[0]:
                    return row[0]
        except Exception:
            pass
    return 0


def run_step(name: str, cmd: list) -> bool:
    """Run a pipeline step, return True if successful."""
    print(f"\n{'='*60}")
    print(f"  STEP: {name}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"\n  WARNING: {name} exited with code {result.returncode}")
        return False
    return True


def require_nonempty_team_lists(sport: str, expected_round: int) -> bool:
    """Reject a nominally successful scrape that produced no usable changes."""
    path = ROOT / "data" / "line_movement" / "team_lists" / f"{sport.lower()}_latest.json"
    try:
        import json
        payload = json.loads(path.read_text(encoding="utf-8"))
        scraped_round = int(payload.get("round") or 0)
        teams = payload.get("teams") or {}
        changed = {
            team: entry for team, entry in teams.items()
            if entry.get("ins") or entry.get("outs")
        }
    except (OSError, ValueError, TypeError):
        changed = {}
    if not changed:
        print(f"\n  WARNING: {sport} team-list scrape produced no ins/outs")
        return False
    if scraped_round and scraped_round != expected_round:
        print(f"\n  WARNING: {sport} source is Round {scraped_round}, expected Round {expected_round}")
        return False
    print(f"\n  Validated team-list changes for {len(changed)} {sport} teams")
    return True


def main():
    parser = argparse.ArgumentParser(description="Run the line movement prediction pipeline")
    parser.add_argument("--sport", required=True, choices=["NRL", "AFL"])
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--score-only", action="store_true",
                        help="Only score a previous round's predictions (no new predictions)")
    parser.add_argument("--skip-scrape", action="store_true",
                        help="Skip team list and ladder scraping")
    parser.add_argument("--score-prev", action="store_true",
                        help="Also score previous round before predicting")
    parser.add_argument("--stage", choices=("monday", "confirmation"), default="confirmation")
    args = parser.parse_args()

    python = sys.executable
    sport = args.sport
    rnd = args.round
    season = args.season

    if rnd == 0:
        rnd = detect_round(sport, season)
        if rnd == 0:
            print(f"ERROR: Could not auto-detect round for {sport} {season}")
            sys.exit(1)
        print(f"Auto-detected round: {rnd}")

    print(f"\n{'#'*60}")
    print(f"  LINE MOVEMENT PIPELINE — {sport} R{rnd} {season}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    if args.score_only:
        run_step(
            f"Score {sport} R{rnd} predictions",
            [python, str(SCRIPT_DIR / "score_predictions.py"),
             "--sport", sport, "--round", str(rnd), "--season", str(season)]
        )
        return

    # Score previous round if requested
    if args.score_prev and rnd > 1:
        run_step(
            f"Score {sport} R{rnd - 1} predictions",
            [python, str(SCRIPT_DIR / "score_predictions.py"),
             "--sport", sport, "--round", str(rnd - 1), "--season", str(season)]
        )

    if args.stage == "monday":
        if not run_step(
            f"Build {sport} projected availability",
            [python, str(SCRIPT_DIR / "forecast_availability.py"), "--sport", sport,
             "--round", str(rnd), "--season", str(season)],
        ):
            sys.exit(1)
    elif not args.skip_scrape:
        # Step 1: Scrape ladder
        run_step(
            f"Scrape {sport} ladder",
            [python, str(SCRIPT_DIR / "scrape_ladder.py"), "--sport", sport, "--season", str(season)]
        )

        # Step 2: Scrape team lists
        team_lists_ok = run_step(
            f"Scrape {sport} team lists",
            [python, str(SCRIPT_DIR / "scrape_team_lists.py"), "--sport", sport,
             "--expected-round", str(rnd)]
        )
        if team_lists_ok:
            team_lists_ok = require_nonempty_team_lists(sport, rnd)

        if not team_lists_ok:
            print("\n  Refusing to publish a movement prediction without valid team-list changes")
            sys.exit(1)

    # Step 3: Run predictions
    ok = run_step(
        f"Predict {sport} R{rnd} line movements",
        [python, str(SCRIPT_DIR / "predict_movement.py"),
         "--sport", sport, "--round", str(rnd), "--season", str(season)]
         + (["--stage", "monday"] if args.stage == "monday" else [])
    )

    print(f"\n{'#'*60}")
    if ok and (args.stage == "monday" or args.skip_scrape or team_lists_ok):
        print(f"  PIPELINE COMPLETE — {sport} R{rnd}")
    else:
        print(f"  PIPELINE FINISHED WITH WARNINGS — {sport} R{rnd}")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}\n")
    if not ok or (args.stage != "monday" and not args.skip_scrape and not team_lists_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
