# Market engine — activation plan

**Branch:** `feat/market-engine-cloud` · **Written:** 2026-09-11

## Headline: this is ~80% built already. The job is activation, not construction.

`cloud/odds_collector.py` (17KB), its config, Dockerfile, Railway cron config, health
checker and the full Supabase warehouse schema were written on 3 September and never
switched on. The architecture doc is
`handover/sessions/2026-09-03_epl-efl-nfl_market_timing_collection_architecture.md`.

Verified working today: `python3 cloud/odds_collector.py --dry-run --force --sports EPL`
returned 20 events, 2,085 quotes, 6 API requests, next interval 60m.

## What is actually wrong right now

The 10-minute snapshot is running on the laptop (`com.betmate.odds-snapshot-10min`,
`StartInterval 600`) with a second job (`com.betmate.prevent-sleep`) fighting to keep the
Mac awake for it. It is **not working**: 2,037 credits used in 11 days is about **8
cycles a day, not 144**. The machine sleeps and the snapshots are simply missed. The
data being collected for a movement model has large, irregular holes in it — which is
worse than a lower cadence collected reliably.

## The design that already exists, and why it beats flat 10-minute polling

| feature | behaviour |
|---|---|
| **Adaptive cadence** | 5 min inside 90 min of kickoff, 15 min to 6h, 30 min to 24h, 60 min to 3d, 180 min to 7d, else 360 min |
| **Change-only storage** | `odds_quote_state` holds one row per quote identity; `odds_quote_changes` grows only when a price or line actually moves (`value_fingerprint`) |
| **Research checkpoints** | one guaranteed observation at 7d, 3d, 2d, 24h, 12h, 6h, 3h, 90m, 60m, 30m, 10m before kickoff, even if nothing moved — this is the ML feature grid |
| **Cron pattern** | Railway invokes every 5 min; the collector reads remote `next_due_at` and fetches only competitions currently due |
| **Safety** | `ODDS_COLLECTION_LIVE_ENABLED=false` until explicitly flipped |

Flat 10-minute polling is both more expensive and less useful: it over-samples a market
nobody is betting into on a Tuesday and under-samples the final hour, which is where the
money actually flows.

## The binding constraint: API credits

Cost is **regions x markets per fetch**, measured today: `uk` + `h2h` = 1 credit;
`au,uk` + `h2h,spreads,totals` = **6 credits**.

Simulated against real fixture lists over 30 days on the adaptive ladder:

| sport | credits/30d |
|---|---:|
| EPL | 38,670 |
| EFL Championship | 27,330 |
| NRL | 16,638 |
| AFL | 10,830 |
| NFL | 9,138 |
| NBA (preseason only — in season it behaves like EPL) | 720 |
| **total, 6 sports, au+uk, 3 markets** | **~103,000** |

NBA in full season and UCL once active push this toward 150,000-200,000.

| plan | cost | verdict |
|---|---|---|
| 20K (current) | $30/mo | **impossible** — 5x over on day one |
| 100K | $59/mo | works only at single region, and NBA in season likely breaks it |
| **5M** | **$119/mo** | **removes the constraint entirely** — even flat 5-min polling on 8 sports is ~415k |

## DECIDED 2026-09-11: 2-hourly baseline + one close capture per kickoff cluster

Stay on the **existing $30 / 20K plan**. No upgrade needed.

Measured from 8 dense days of the repo's own snapshot archive, h2h movement by time to
kickoff: **60% of all price movement happens more than a day out** as slow drift, which a
slow cadence captures perfectly well. The final two hours are 16.7x more intense per hour
but only 8.8% of the total.

| | fetches/30d | credits | vs 20,000 |
|---|---:|---:|---|
| 2-hourly baseline | 2,160 | 12,960 | fits |
| + one close sweep per distinct kickoff time | 316 | 1,895 | |
| **total** | **2,476** | **~14,900** | **26% spare** |

The close capture exists because a movement model's **target** is the closing price. 25%
of movement lands inside the final six hours, so a last observation up to two hours stale
corrupts the label, not just the features.

**Do not drive the close capture off the cadence ladder.** With staggered kickoffs the
"nearest kickoff" rolls forward all evening and the sport never leaves tight mode —
measured at **86,046 credits/month** against a 20,000 quota. Waking once per kickoff
cluster (`next_due_at()`) costs ~1,900 instead. Hosting on Railway is roughly $5/month.

## Work required

1. **Apply the Supabase migration** — `supabase/migrations/20260903_market_timing_snapshots.sql`.
   Confirmed today: all five tables return 404, so this was never run.
2. **Add NBA** to `cloud/odds_collection_config.json` (`basketball_nba`). UCL is already
   configured; it is `active=false` at the API right now, and the collector already
   handles an empty response cleanly (verified — returns 0 events, 0 rows).
3. **Handle sports going active/inactive** — poll `/v4/sports` and skip inactive keys so
   out-of-season competitions cost nothing.
4. **Create the Railway service** from `cloud/Dockerfile` + `cloud/railway.json`, set the
   variables from `cloud/.env.example`, deploy with the live flag **false**.
5. **Dry-run every sport**, checking team names, soccer draws, commence times, bookmaker
   timestamps, handicap signs and quota headers.
6. **Go live** — flip `ODDS_COLLECTION_LIVE_ENABLED=true`, force one controlled run, then
   `python cloud/collection_health.py` and inspect row counts.
7. **Retire the laptop jobs** — unload `com.betmate.odds-snapshot-10min` and
   `com.betmate.prevent-sleep`. Keep the local CSV snapshot as a fallback for one week,
   then stop it.
8. **Backfill nothing.** Point-in-time data cannot be reconstructed; the record starts the
   day this goes live. That is the strongest argument for doing it this week rather than
   next month.

## What this does NOT do

It collects. It does not model. The ML step — predicting which way a line moves and when
money flows — needs the data first, and the existing architecture doc is explicit that
timing models stay shadow-only until formally promoted, and never create bets.

Realistic timeline to a trustworthy movement model: a **full season per sport**. The
existing market-event tagging pipeline (`scripts/build_market_event_log.py`,
`compute_snapshot_deltas.py`, `tag_odds_movements.py`) currently explains ~10% of moves
and is the thing this feeds.
