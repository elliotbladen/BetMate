#!/usr/bin/env bash
# git-sync-end.sh — run LAST THING before leaving this machine (macOS/Linux).
# Mirror of git-sync-end.ps1.
#
# Commits everything and pushes. Also rebuilds the RacingEngine seed when this
# machine holds racing data the seed does not — the 18.5GB DB never travels, the
# ~52MB seed does, and it is useless if it is not rebuilt after racing work.
#
# Usage:  ./scripts/git-sync-end.sh "what happened"
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

if [ $# -lt 1 ]; then echo "Usage: ./scripts/git-sync-end.sh \"what happened\""; exit 1; fi
MESSAGE="$1"

echo "=== BetMate sync-end ==="

PY=$(command -v python3 || command -v python)
"$PY" scripts/racing_seed_status.py
if [ $? -eq 2 ]; then
  echo
  echo "Rebuilding RacingEngine seed so the racing data travels..."
  if ! "$PY" RacingEngine/build_seed.py; then
    echo "Seed rebuild FAILED — fix before pushing, or the other machine gets stale data."
    exit 1
  fi
fi
echo

if [ -z "$(git status --porcelain)" ]; then
  echo "Nothing to commit."
else
  git add -A
  if ! git commit -m "$MESSAGE"; then echo "Commit failed — fix and re-run."; exit 1; fi
fi

if ! git push origin main; then
  echo
  echo "PUSH REJECTED — origin has commits this machine does not."
  echo "The other machine pushed since you started. Run git-sync-start.sh"
  echo "to fast-forward (your commit is safe locally), then push again."
  exit 1
fi

echo "Pushed. Safe to switch machines."
