"""Build the cross-machine RacingEngine SQL seed from the live database."""

from __future__ import annotations

import argparse
import gzip
import os
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "data" / "racing_engine.sqlite"
DEFAULT_OUTPUT = ROOT / "data" / "seed" / "racing_seed.sql.gz"
EXCLUDED_DATA_TABLES = frozenset({"run_performances", "horse_rating_states"})
INSERT_TABLE = re.compile(r'^INSERT INTO\s+["\[]?([^"\]\s]+)["\]]?\s')


def build_seed(database: Path, output: Path) -> None:
    if not database.is_file():
        raise FileNotFoundError(database)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".building")
    if temporary.exists():
        raise FileExistsError(
            f"Temporary seed already exists: {temporary}. Inspect or remove it before retrying."
        )

    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    written = 0
    skipped = {table: 0 for table in EXCLUDED_DATA_TABLES}
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Source database failed integrity check: {integrity}")
        with gzip.open(temporary, "wt", encoding="utf-8", newline="\n") as seed:
            for statement in connection.iterdump():
                match = INSERT_TABLE.match(statement)
                if match and match.group(1) in EXCLUDED_DATA_TABLES:
                    skipped[match.group(1)] += 1
                    continue
                seed.write(statement)
                seed.write("\n")
                written += 1
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        connection.close()

    os.replace(temporary, output)
    print(f"Built {output} ({output.stat().st_size} bytes; {written:,} statements)")
    for table in sorted(skipped):
        print(f"Excluded {table}: {skipped[table]:,} rows")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_seed(args.database.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
