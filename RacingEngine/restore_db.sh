#!/usr/bin/env bash
# Cross-platform wrapper for the safe, streaming Python restore.
#
# Fresh database:
#   ./restore_db.sh
#
# Existing database (a backup is mandatory):
#   ./restore_db.sh --backup data/backups/racing_engine_before_restore.sqlite

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/restore_db.py" "$@"
