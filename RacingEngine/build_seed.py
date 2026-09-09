"""Build the cross-machine RacingEngine SQL seed from the live database."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "data" / "racing_engine.sqlite"
DEFAULT_OUTPUT = ROOT / "data" / "seed" / "racing_seed.sql.gz"
MANIFEST_NAME = "seed_manifest.json"

# Tables whose content proves how current the seed is. Compared on restore and
# on sync-start so a stale seed cannot pass unnoticed.
WATERMARK_SQL = {
    "race_results_max_date": "SELECT MAX(race_date) FROM race_results",
    "race_results_rows":     "SELECT COUNT(*) FROM race_results",
    "runner_results_rows":   "SELECT COUNT(*) FROM runner_results",
    "sectionals_rows":       "SELECT COUNT(*) FROM canonical_sectionals",
}


def watermark(connection) -> dict:
    out = {}
    for key, sql in WATERMARK_SQL.items():
        try:
            out[key] = connection.execute(sql).fetchone()[0]
        except sqlite3.Error:
            out[key] = None
    return out


def write_manifest(connection, output: Path) -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip() or None
    except Exception:
        commit = None
    data = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": commit,
        "seed_bytes": output.stat().st_size,
        "excluded_tables": sorted(EXCLUDED_DATA_TABLES),
        **watermark(connection),
    }
    (output.parent / MANIFEST_NAME).write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data
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

    check = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        data = write_manifest(check, output)
    finally:
        check.close()
    def _n(v): return f"{v:,}" if isinstance(v, int) else "n/a"
    print(f"Manifest: results to {data['race_results_max_date'] or 'n/a'}, "
          f"{_n(data['race_results_rows'])} races, {_n(data['sectionals_rows'])} sectionals")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_seed(args.database.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
