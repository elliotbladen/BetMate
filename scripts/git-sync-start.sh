#!/usr/bin/env bash
# git-sync-start.sh — run FIRST THING when starting work on this machine (macOS/Linux).
# Mirror of git-sync-start.ps1. Same protocol, same guarantees.
#
#   1. Refuses to pull over uncommitted work
#   2. Fetches and reports position
#   3. Pulls --ff-only — never auto-merges diverged histories
#   4. Checks the RacingEngine seed against the local DB (the 18.5GB DB never
#      travels through git; only the ~52MB seed does)
#
# Usage:  ./scripts/git-sync-start.sh
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

echo "=== BetMate sync-start ==="

dirty=$(git status --porcelain | grep -v '^??' || true)
if [ -n "$dirty" ]; then
  echo
  echo "STOP: uncommitted changes on this machine:"
  echo "$dirty" | sed 's/^/  /'
  echo
  echo "Commit them first (git-sync-end.sh), then re-run."
  echo "Do NOT pull over uncommitted work — that is how the July 8 mess happened."
  exit 1
fi

git fetch origin
ahead=$(git rev-list --count origin/main..main)
behind=$(git rev-list --count main..origin/main)
echo "Local is $ahead ahead / $behind behind origin/main"

if [ "$behind" -gt 0 ]; then
  if ! git pull --ff-only origin main; then
    echo
    echo "PULL REFUSED — histories have diverged (both machines committed)."
    echo "Do not force anything. Open a Claude session and say:"
    echo '  "git sync-start says the machines have diverged, reconcile it"'
    exit 1
  fi
fi

echo
PY=$(command -v python3 || command -v python)
"$PY" scripts/racing_seed_status.py
if [ $? -eq 1 ]; then
  echo
  echo "Racing DB is behind the seed. Restore it before any racing work."
fi

echo
echo "Up to date. Safe to work."
