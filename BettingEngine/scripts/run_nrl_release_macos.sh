#!/bin/zsh
# Full NRL release for macOS: price, export, publish matrices, then publish Baz.
# launchd calls this wrapper on Monday and Thursday; do not call prepare_round.py
# directly for a production release.

set -euo pipefail

ROOT="/Users/elliotbladen/BetMate/BettingEngine"
BETMATE_ROOT="/Users/elliotbladen/BetMate"
PYTHON_BIN="/usr/local/bin/python3"
UV_BIN="/usr/local/bin/uv"

cd "$ROOT"
export BETMATE_ROOT
export PYTHONUTF8=1

"$PYTHON_BIN" scripts/prepare_round.py --season 2026 --round 0

ROUND=$("$PYTHON_BIN" -c "import json; from pathlib import Path; print(json.loads((Path('$BETMATE_ROOT') / 'data/nrl/fixture/processed/latest-fixture.json').read_text())['round'])")
"$PYTHON_BIN" scripts/export_round_csv.py --season 2026 --round "$ROUND"
"$PYTHON_BIN" scripts/push_matrices_to_supabase.py

# The context publisher imports Baz's FastAPI module, so run it in uv's
# isolated dependency environment. A failure here fails the release by design.
"$UV_BIN" run --with requests --with fastapi --with uvicorn \
  python scripts/publish_current_baz_context.py NRL
