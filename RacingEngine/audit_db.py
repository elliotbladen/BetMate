"""Print a deterministic post-restore audit of the RacingEngine database."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "data" / "racing_engine.sqlite"
CORE_TABLES = (
    "meetings",
    "races",
    "runners",
    "horses",
    "runner_results",
    "runner_sectionals",
    "steward_reports",
    "steward_events",
    "canonical_sectionals",
    "v2_clean_races",
    "v2_clean_runner_results",
    "v2_run_performances",
    "run_performances",
    "horse_rating_states",
)
DATED_TABLES = {
    "runner_results": (
        "runner_results rr",
        "rr.race_date",
    ),
    "v2_clean_runner_results": (
        "v2_clean_runner_results rr JOIN v2_clean_races r ON r.race_id = rr.race_id",
        "r.race_date",
    ),
    "v2_run_performances": (
        "v2_run_performances p JOIN v2_clean_races r ON r.race_id = p.race_id",
        "r.race_date",
    ),
    "run_performances": (
        "run_performances p",
        "p.race_date",
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    database = args.database.resolve()
    if not database.is_file():
        raise FileNotFoundError(database)

    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        print(f"database: {database}")
        print(f"size_bytes: {database.stat().st_size}")
        print(f"integrity_check: {connection.execute('PRAGMA integrity_check').fetchone()[0]}")
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        print(f"foreign_key_violations: {len(violations)}")
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        print(f"tables: {len(table_names)}")
        print("core_counts:")
        for table in CORE_TABLES:
            if table not in table_names:
                print(f"  {table}: MISSING")
            else:
                count = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                print(f"  {table}: {count}")

        print("rating_date_coverage:")
        for table, (from_clause, date_column) in DATED_TABLES.items():
            if table not in table_names:
                print(f"  {table}: MISSING")
                continue
            minimum, maximum = connection.execute(
                f"SELECT MIN({date_column}), MAX({date_column}) FROM {from_clause}"
            ).fetchone()
            latest_count = (
                connection.execute(
                    f"SELECT COUNT(*) FROM {from_clause} WHERE {date_column} = ?",
                    (maximum,),
                ).fetchone()[0]
                if maximum is not None
                else 0
            )
            print(f"  {table}: {minimum} to {maximum} (latest rows: {latest_count})")

        if {"v2_run_performances", "v2_clean_races"}.issubset(table_names):
            latest_v2_date = connection.execute(
                "SELECT MAX(r.race_date) FROM v2_run_performances p "
                "JOIN v2_clean_races r ON r.race_id = p.race_id"
            ).fetchone()[0]
            print(f"latest_v2_top_performances ({latest_v2_date}):")
            for horse, rating, track, race_number in connection.execute(
                "SELECT p.horse_name, p.performance_rating, r.track_slug, r.race_number "
                "FROM v2_run_performances p JOIN v2_clean_races r ON r.race_id = p.race_id "
                "WHERE r.race_date = ? ORDER BY p.performance_rating DESC LIMIT 10",
                (latest_v2_date,),
            ):
                print(f"  {horse}: {rating:.3f} ({track} R{race_number})")

        if "runner_results" in table_names:
            date_range = connection.execute(
                "SELECT MIN(race_date), MAX(race_date) FROM runner_results"
            ).fetchone()
            print(f"result_date_range: {date_range[0]} to {date_range[1]}")
            print("results_by_source:")
            for source, count in connection.execute(
                "SELECT source, COUNT(*) FROM runner_results "
                "GROUP BY source ORDER BY source"
            ):
                print(f"  {source}: {count}")

        if "meetings" in table_names:
            print("meetings_by_state:")
            for state, count in connection.execute(
                "SELECT state, COUNT(*) FROM meetings GROUP BY state ORDER BY state"
            ):
                print(f"  {state}: {count}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
