"""CLI for manually recording auditable EPL/Championship availability evidence.

Examples:
  python -m ml.football.player_layer.player_tracker init --league epl
  python -m ml.football.player_layer.player_tracker update --league epl --team Arsenal --player "Bukayo Saka" --position W --status doubtful --start-probability .55 --expected-minutes 50 --source-type official_club --source-url https://... --note "Manager: late test"
  python -m ml.football.player_layer.player_tracker snapshot --league epl --home Arsenal --away Chelsea --kickoff-at 2026-08-22T19:00:00+01:00 --cutoff-at 2026-08-21T17:00:00+01:00 --stage early
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .availability import AvailabilityStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Football player availability tracker")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    roster = sub.add_parser("import-roster")
    update = sub.add_parser("update")
    snap = sub.add_parser("snapshot")
    appearance = sub.add_parser("record-appearance")
    for command in (init, roster, update, snap, appearance):
        command.add_argument("--league", required=True, choices=("epl", "championship"))
    roster.add_argument("--csv", required=True, help="CSV columns: team,player_name,position")
    update.add_argument("--team", required=True); update.add_argument("--player", required=True)
    update.add_argument("--position", required=True); update.add_argument("--status", required=True)
    update.add_argument("--start-probability", type=float, required=True)
    update.add_argument("--expected-minutes", type=float, required=True)
    update.add_argument("--source-type", required=True); update.add_argument("--source-url")
    update.add_argument("--note", default=""); update.add_argument("--event-time"); update.add_argument("--recorded-at")
    snap.add_argument("--home", required=True); snap.add_argument("--away", required=True)
    snap.add_argument("--kickoff-at", required=True); snap.add_argument("--cutoff-at", required=True)
    snap.add_argument("--stage", required=True, choices=("early", "final"))
    snap.add_argument("--confirmed-home", default="", help="Comma-separated official home starters (final only)")
    snap.add_argument("--confirmed-away", default="", help="Comma-separated official away starters (final only)")
    appearance.add_argument("--home", required=True); appearance.add_argument("--away", required=True)
    appearance.add_argument("--kickoff-at", required=True); appearance.add_argument("--team", required=True)
    appearance.add_argument("--player", required=True); appearance.add_argument("--position", required=True)
    appearance.add_argument("--started", action="store_true")
    appearance.add_argument("--minutes-played", type=float, required=True)
    appearance.add_argument("--position-played")
    return parser


def main() -> None:
    args = _parser().parse_args()
    store = AvailabilityStore.for_league(args.league)
    if args.command == "init":
        store.initialise(); print(f"Initialised {store.path}"); return
    if args.command == "import-roster":
        with Path(args.csv).open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        required = {"team", "player_name", "position"}
        if not rows or not required.issubset(rows[0]):
            raise ValueError("roster CSV needs columns: team,player_name,position")
        for row in rows:
            store.add_player(row["team"], row["player_name"], row["position"])
        print(f"Imported {len(rows)} roster rows into {store.path}"); return
    if args.command == "update":
        update_id = store.record_update(team=args.team, player_name=args.player, position=args.position,
            status=args.status, start_probability=args.start_probability, expected_minutes=args.expected_minutes,
            source_type=args.source_type, source_url=args.source_url, note=args.note,
            event_time=args.event_time, recorded_at=args.recorded_at)
        print(f"Recorded availability update {update_id}"); return
    if args.command == "record-appearance":
        store.record_appearance(home_team=args.home, away_team=args.away, kickoff_at=args.kickoff_at,
            team=args.team, player_name=args.player, position=args.position, started=args.started,
            minutes_played=args.minutes_played, position_played=args.position_played)
        print(f"Recorded observed appearance for {args.player}"); return
    snapshot_id = store.create_snapshot(home_team=args.home, away_team=args.away, kickoff_at=args.kickoff_at,
        stage=args.stage, cutoff_at=args.cutoff_at,
        confirmed_home=[p.strip() for p in args.confirmed_home.split(",") if p.strip()],
        confirmed_away=[p.strip() for p in args.confirmed_away.split(",") if p.strip()])
    print(f"Created {args.stage} snapshot {snapshot_id}")


if __name__ == "__main__":
    main()
