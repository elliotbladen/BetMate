#!/usr/bin/env bash
# Restore racing_engine.sqlite from the seed SQL dump.
# Run this after a fresh git pull if the database is empty/missing.
#
# Usage:  ./restore_db.sh
#
# What it does:
#   1. Decompresses data/seed/racing_seed.sql.gz
#   2. Loads schema + core data into data/racing_engine.sqlite
#   3. Cleans up the decompressed file
#
# Excluded tables (must be regenerated via the ratings pipeline):
#   - run_performances  (14M rows, ~12GB)
#   - horse_rating_states (7.1M rows, ~6GB)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SEED="$SCRIPT_DIR/data/seed/racing_seed.sql.gz"
DB="$SCRIPT_DIR/data/racing_engine.sqlite"

if [ ! -f "$SEED" ]; then
    echo "ERROR: Seed file not found at $SEED"
    echo "Make sure you have pulled the repo with Git LFS:"
    echo "  git lfs pull"
    exit 1
fi

if [ -f "$DB" ]; then
    echo "WARNING: $DB already exists."
    read -p "Overwrite? (y/N) " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Aborted."
        exit 0
    fi
    rm "$DB"
fi

echo "Decompressing seed..."
gunzip -k "$SEED"
SQL="${SEED%.gz}"

echo "Loading into $DB..."
sqlite3 "$DB" < "$SQL"

echo "Cleaning up..."
rm "$SQL"

HORSES=$(sqlite3 "$DB" "SELECT count(*) FROM horses;")
RESULTS=$(sqlite3 "$DB" "SELECT count(*) FROM runner_results;")
echo ""
echo "Done! Database restored:"
echo "  Horses:         $HORSES"
echo "  Runner results: $RESULTS"
echo ""
echo "NOTE: run_performances and horse_rating_states are empty."
echo "Regenerate them by running the ratings pipeline."
