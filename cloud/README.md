# BetMate cloud market collector

This directory is the always-online collection foundation for AFL, NRL, EPL,
EFL Championship, NFL and UCL. A cloud cron invokes the collector every five
minutes; the collector itself uses remote `next_due_at` state to fetch only the
competitions currently due.

## Safety state

Live collection is disabled unless `ODDS_COLLECTION_LIVE_ENABLED=true`. The
configuration is ready, but no Odds API or Supabase traffic occurs by default.

## Before activation

1. Apply `supabase/migrations/20260903_market_timing_snapshots.sql` in Supabase.
2. Create a Railway service from the repository using `cloud/Dockerfile` and
   `cloud/railway.json`.
3. Add the variables from `cloud/.env.example` as private service variables.
4. Keep `ODDS_COLLECTION_LIVE_ENABLED=false` for the first deployment.
5. Install dependencies locally or in the container: `pip install -r cloud/requirements.txt`.
6. Validate each sport with a dry run:

```powershell
python cloud/odds_collector.py --dry-run --force --sports AFL
python cloud/odds_collector.py --dry-run --force --sports NRL
python cloud/odds_collector.py --dry-run --force --sports EPL
python cloud/odds_collector.py --dry-run --force --sports EFL
python cloud/odds_collector.py --dry-run --force --sports NFL
python cloud/odds_collector.py --dry-run --force --sports UCL
```

7. Confirm team names, soccer draws, commence times, bookmaker timestamps,
   decimal odds, handicap signs, total points and quota response headers.
8. Set `ODDS_COLLECTION_LIVE_ENABLED=true` and force one controlled live run.
9. Run `python cloud/collection_health.py` and inspect Supabase row counts.
10. Allow the five-minute cron to take over.

## Storage behaviour

- `odds_quote_state` holds one current row per quote identity and does not grow
  with repeated captures.
- `odds_quote_changes` grows only when a price or line changes.
- `odds_market_checkpoints` preserves one observation per configured research
  horizon even if the quote was unchanged.
- `market_news_events` deduplicates source events by content hash.
- Raw secrets never enter snapshot rows or logs.

## Quota behaviour

The worker polls each competition according to the nearest known kickoff:

- more than 7 days: six-hourly;
- 3–7 days: three-hourly;
- 1–3 days: hourly;
- 6–24 hours: every 30 minutes;
- 90 minutes–6 hours: every 15 minutes;
- inside 90 minutes: every five minutes.

Every run records API requests used/remaining. Collection health warns below
1,000 remaining requests. Cadence can be reduced in
`cloud/odds_collection_config.json` without changing code.

## News intake

Source-specific injury, press-conference, team-list, weather and match-report
collectors should emit the canonical schema accepted by:

```powershell
python cloud/news_event_ingest.py --input event.json --dry-run
```

Level A/B events may later become strong availability features. Level C/D
events are archived for research/shadow use only.

## Health and storage thresholds

`collection_health.py` returns non-zero on critical failures. Database warnings
are configured at 300 MB, 400 MB and 450 MB to stay below Supabase Free's
500 MB limit. Railway can alert on a failed cron execution.

## Recovery

The warehouse is append-only for historical changes and checkpoints. At season
end, export those tables to compressed Parquet before any retention operation.
Never delete a season until its archive has been verified and checksummed.

## Automated Sydney/Melbourne tempo worker

Race-day tempo collection is a separate Railway cron so an Odds API failure
cannot stop racing sectionals. It discovers Saturday metro meetings, freezes V0
race context, polls only around the meeting window, imports official sectionals
and writes append-only V1/V2/etc shadow snapshots to Supabase.

Files:

- migration: `supabase/migrations/20260903_race_day_tempo.sql`;
- worker: `cloud/race_day_tempo_worker.py`;
- deployment: `cloud/Dockerfile.tempo` and `cloud/railway.tempo.json`;
- config: `cloud/tempo_collection_config.json`;
- frozen pars/context: `cloud/tempo_model_bundle.json`.

Activation:

1. Apply `20260903_race_day_tempo.sql` in the Supabase SQL editor.
2. Create a second Railway service using `cloud/Dockerfile.tempo` and the
   five-minute schedule in `cloud/railway.tempo.json`.
3. Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` as private variables.
4. Set `TEMPO_COLLECTION_LIVE_ENABLED=false` for the first deployment.
5. Run `python cloud/race_day_tempo_worker.py --date YYYY-MM-DD --dry-run`.
6. Confirm meeting/race identities and source availability.
7. Set `TEMPO_COLLECTION_LIVE_ENABLED=true`.

Melbourne uses the authorised public Racing.com form request and waits for
runner timing fields. Sydney polls the official ATC Swiss Timing PDF and treats
an unavailable/incomplete document as pending, never as an empty result.

The worker holds early tempo and four-way probabilities at V0 while the model
is amber. Only capped middle/late shadow scores update. Horse prices are
hard-disabled both in config and every stored snapshot.
