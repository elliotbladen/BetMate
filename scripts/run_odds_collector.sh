#!/bin/bash
# MANUAL / EMERGENCY USE ONLY. Railway owns the collection schedule.
#
# Do NOT put this on a launchd timer. Railway runs cloud/odds_collector.py on a
# */5 cron against the same Supabase tables, and a second scheduler would double the
# credit spend and race it for the poll state. Use this only to force a cycle by hand
# when Railway is down, the way betmate-local-firstrun was run on 2026-09-11.
#
# The collector is cadence-gated: it asks Supabase which sports are due and skips the
# rest, so a cycle with nothing due costs 0 credits (the /events fixture check is
# free). Never replace that with a fixed-interval fetch loop - that is what drained
# the quota to 4 credits remaining on 2026-09-11.
set -uo pipefail

ROOT="/Users/elliotbladen/BetMate"
LOG_DIR="$ROOT/logs/odds_collector"
mkdir -p "$LOG_DIR"

# 288 cycles a day appends forever otherwise; the legacy snapshot log reached 1.8MB.
for f in "$LOG_DIR/launchd.out.log" "$LOG_DIR/launchd.err.log"; do
  if [ -f "$f" ] && [ "$(wc -c < "$f")" -gt 5242880 ]; then
    mv "$f" "$f.1"
  fi
done

cd "$ROOT" || exit 1

if [ ! -f "$ROOT/.env.local" ]; then
  echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') FATAL .env.local missing" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1091
. "$ROOT/.env.local"
set +a

export ODDS_COLLECTION_LIVE_ENABLED=true
export ODDS_WORKER_ID="${ODDS_WORKER_ID:-betmate-mac-1}"

echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') --- collector cycle start (worker=$ODDS_WORKER_ID)"
/usr/local/bin/python3 "$ROOT/cloud/odds_collector.py" "$@"
status=$?
echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') --- collector cycle end rc=$status"
exit $status
