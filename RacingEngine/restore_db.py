"""Safely restore the cross-machine RacingEngine SQLite seed.

The SQL dump is streamed statement by statement into a temporary database so
the restore works with Python alone and does not hold the full dump in memory.
The live database is replaced only after SQLite's integrity check succeeds.
"""

from __future__ import annotations

import argparse
import gzip
import re
import shutil
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_SEED = ROOT / "data" / "seed" / "racing_seed.sql.gz"
DEFAULT_DB = ROOT / "data" / "racing_engine.sqlite"


def restore(seed: Path, database: Path, backup: Path | None) -> None:
    if not seed.is_file():
        raise FileNotFoundError(f"Seed file not found: {seed}")

    database.parent.mkdir(parents=True, exist_ok=True)
    temporary = database.with_suffix(database.suffix + ".restoring")
    if temporary.exists():
        raise FileExistsError(
            f"Temporary restore already exists: {temporary}. "
            "Inspect or remove it before retrying."
        )

    if database.exists():
        if backup is None:
            raise FileExistsError(
                f"Database already exists: {database}. Pass --backup PATH to "
                "preserve it before replacement."
            )
        if backup.exists():
            raise FileExistsError(f"Refusing to overwrite backup: {backup}")
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(database, backup)
        print(f"Backed up existing database to {backup}", flush=True)

    connection = sqlite3.connect(temporary)
    statement_lines: list[str] = []
    statement_count = 0
    try:
        with gzip.open(seed, "rt", encoding="utf-8", newline="") as sql_file:
            for line in sql_file:
                stripped = line.strip()
                if not statement_lines and (
                    not stripped
                    or stripped.startswith("--")
                    or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", stripped)
                ):
                    # The seed generator emitted an informational list of table
                    # names after its "-- Table:" header. SQLite's CLI ignores
                    # equivalent dot-command output; it is not executable SQL.
                    continue
                statement_lines.append(line)
                statement = "".join(statement_lines)
                if not sqlite3.complete_statement(statement):
                    continue
                connection.execute(statement)
                statement_lines.clear()
                statement_count += 1
                if statement_count % 100_000 == 0:
                    print(f"Executed {statement_count:,} statements", flush=True)

        if statement_lines and "".join(statement_lines).strip():
            raise ValueError("SQL dump ended with an incomplete statement")

        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Restored database failed integrity check: {integrity}")
    except Exception:
        connection.close()
        temporary.unlink(missing_ok=True)
        raise
    else:
        connection.close()

    temporary.replace(database)
    print(
        f"Restored {database} from {seed} "
        f"({statement_count:,} SQL statements; integrity_check={integrity})",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--backup",
        type=Path,
        help="Required when the destination database already exists.",
    )
    args = parser.parse_args()
    restore(args.seed.resolve(), args.database.resolve(), args.backup and args.backup.resolve())


if __name__ == "__main__":
    main()
