# Cloud race-day tempo automation

Date: 3 September 2026
Build status: architecture/code complete; external deployment not activated

## Delivered

- Supabase migration: `supabase/migrations/20260903_race_day_tempo.sql`
- Railway worker: `cloud/race_day_tempo_worker.py`
- Dedicated image/config: `cloud/Dockerfile.tempo`, `cloud/railway.tempo.json`
- Source/cadence policy: `cloud/tempo_collection_config.json`
- Frozen model data: `cloud/tempo_model_bundle.json`
- Reproducible exporter: `racing_engine/expected_tempo_cloud_bundle.py`
- Cloud tests: `tests/test_cloud_tempo_worker.py`

The worker automatically discovers Saturday Sydney and Melbourne metro cards
from the official Racing.com meeting calendar. Melbourne runner timing is read
from the already-authorised public form request. Sydney uses the official ATC
Swiss Timing PDF parser. It runs every five minutes in Railway but polls the
sectional sources only from 90 minutes before Race 1 through 120 minutes after
the last scheduled race.

Supabase preserves meetings, race/V0 state, every source poll, immutable race
observations and append-only tempo snapshots. Payload and snapshot hashes make
retries idempotent. Different going receives zero live evidence weight.

## Safety state

The deployed bundle is `expected-tempo-cloud-bundle-v1` with 74 V0 context
cells and 330 physical par cells. The engine is amber: early scores and
probabilities stay at V0; only capped middle/late values update in shadow.
`horse_price_integration=false` is enforced in config, bundle and database.

## External activation still required

This workspace has no `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY`, and no
Railway control connection. Therefore the migration has not been applied and
the service has not been deployed. Follow `cloud/README.md`; begin disabled,
run a Sydney/Melbourne dry check, then enable collection. Saturday's Sydney
run is also the required prospective test of ATC PDF publication latency.
