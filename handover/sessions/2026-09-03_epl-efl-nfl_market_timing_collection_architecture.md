# EPL, EFL and NFL market-timing collection architecture

Date: 3 September 2026

## Objective

When The Odds API is reconnected, collect immutable point-in-time odds and information snapshots for EPL, EFL Championship and NFL. The eventual timing models will estimate whether an already-approved production-model selection should be placed now, delayed, split across entry points or given no timing recommendation.

The timing system must not create bets. Each sport retains three separated layers:

1. **Fundamental pricing engine** — produces match probabilities and fair prices without future market information.
2. **Market/timing engine** — forecasts the closing market, expected CLV and remaining life of the current price.
3. **Decision engine** — applies EV, data-quality, exposure, matrix and staking rules.

Normal production engines remain responsible for live bet selection. Player, xG and market challengers remain shadow-only until formally promoted.

## Canonical data flow

```text
The Odds API + official news/weather sources
                 |
                 v
        Immutable raw snapshot store
          |                    |
          |                    +-- raw news documents/events
          +-- raw bookmaker quotes
                 |
                 v
       Identity and quality-control layer
                 |
                 v
       Canonical point-in-time warehouse
          |                    |
          +-- market states    +-- information states
                 |                    |
                 +---------+----------+
                           v
                 feature/event timeline
                           v
          descriptive studies and baselines
                           v
              sport-specific timing shadows
                           v
                BET NOW / WAIT / SPLIT / NONE
```

## Raw odds schema

Every quote must be append-only and retain:

```text
snapshot_id
captured_at_utc
source_published_at_utc       nullable
sport                         EPL | EFL_CHAMPIONSHIP | NFL
season
competition
event_id_api
canonical_match_id
commence_time_utc
home_team_raw
away_team_raw
home_team_id
away_team_id
bookmaker_key
bookmaker_name
bookmaker_last_update_utc
market_key                    h2h | spreads | totals
selection_raw
selection_id                  home | draw | away | over | under
point                         nullable for 1X2
price_decimal
region
source_method
request_id
api_quota_remaining           where returned
ingest_status
```

Never overwrite a quote. Repeated identical observations are retained in raw storage but collapsed in derived analysis using bookmaker update timestamps.

## Canonical market-state table

For every match, market and decision timestamp derive:

- best executable price by selection;
- bookmaker providing that price;
- bookmaker count and quote freshness;
- consensus/no-vig probabilities;
- median and weighted consensus price;
- bookmaker dispersion;
- opening price/line and displacement from open;
- movement over 15 minutes, one hour, six hours and 24 hours;
- acceleration and reversal indicators;
- market leader and follower lag;
- current spread/total line and equivalent-price surface;
- time remaining to kickoff;
- eventual sharp/consensus closing line as the target only.

For soccer 1X2, de-vig all three outcomes together. For NFL spreads and totals, point and price must be modelled jointly. A move from -2.5 to -3 cannot be treated as equivalent to a price-only change at -2.5.

## Collection schedule

Use two modes: scheduled baseline capture and event-driven capture.

### Baseline cadence

| Time to kickoff | Capture cadence |
|---|---:|
| Market open to 7 days | Every 6 hours |
| 7 days to 72 hours | Every 3 hours |
| 72 to 24 hours | Hourly |
| 24 to 6 hours | Every 30 minutes |
| 6 hours to 90 minutes | Every 15 minutes |
| 90 minutes to kickoff | Every 5 minutes if quota permits |
| Final close | One capture inside the final 2–5 minutes |

If API cost is restrictive, preserve fixed research horizons first: opening, 7d, 72h, 48h, 24h, 12h, 6h, 3h, 90m, 60m, 30m, 10m and close.

### Event-driven capture

Trigger an immediate odds pull when any of these arrives:

- confirmed starting line-up or inactive list;
- important injury, suspension or withdrawal;
- official squad announcement;
- material coach press-conference statement;
- quarterback status change;
- major weather forecast change;
- venue or kickoff change;
- rapid price/line movement beyond a configured threshold.

Capture again 5, 15, 30 and 60 minutes after a material event, subject to quota, to measure market reaction speed.

## News and availability schema

```text
event_record_id
published_at_utc
captured_at_utc
canonical_match_id
sport
team_id
player_id                 nullable
event_type
status_before
status_after
position
expected_role
replacement_player_id    nullable
source_level              A | B | C | D
source_name
source_url
raw_text
structured_summary
confidence
expected_impact
confirmed                 boolean
supersedes_event_id       nullable
```

Source levels:

- **A:** league/team injury reports, official line-ups, clubs, coaches and named players.
- **B:** established reporters and reliable injury/news services.
- **C:** reputable predicted line-ups and analysis.
- **D:** rumours and unverified social discussion.

Only A/B information can directly produce strong availability features. C/D remains stored for research and shadow testing.

## EPL-specific design

Markets:

- 1X2;
- Asian handicap/spread where available;
- totals, initially 2.5 with the full line ladder retained;
- BTTS where available and affordable within API coverage.

Information checkpoints:

- opening market;
- manager press conferences, usually one to two days before kickoff;
- European midweek match completion and recovery updates;
- predicted line-up revisions;
- confirmed XI approximately 60–75 minutes before kickoff;
- final pre-match market.

Important EPL features:

- rotation after Champions League/Europa/Conference League matches;
- confirmed goalkeeper, centre-forward and central-defence changes;
- expected-minutes and replacement-quality deltas from the player shadow;
- congestion, travel and rest imbalance;
- manager changes and formation/role changes;
- weather, especially wind and heavy rain for totals;
- current normal-model EV and matrix score, retained as point-in-time inputs;
- price response before and after confirmed XIs.

The normal EPL model alone creates betting candidates. The player/xG layer and timing model remain comparisons until their promotion gates pass.

## EFL Championship-specific design

Use a separate EFL model rather than pooling blindly with EPL. Championship markets are generally thinner, bookmaker dispersion can be wider, schedules are more congested and reliable team news may arrive later.

Markets:

- 1X2;
- handicap;
- totals, retaining the full available ladder;
- BTTS where available.

Important EFL features:

- Saturday/Tuesday turnaround and minutes played;
- travel distance and consecutive away fixtures;
- squad depth and replacement quality;
- loan-player eligibility and deadline-window changes;
- promoted/relegated/new-cohort uncertainty;
- goalkeeper and striker availability;
- bookmaker coverage count and dispersion;
- whether a price move is consensus-led or caused by one thin book;
- confirmed XI response and market liquidity proxy.

Require stronger data-quality checks in EFL. Do not issue a confident timing decision when only a small number of bookmakers are quoting or when the apparent best price is stale.

## NFL-specific design

Markets:

- moneyline;
- spread, including alternate points if available;
- total;
- retain bookmaker-specific line and price pairs.

Information checkpoints:

- Sunday night/opening line;
- Monday and Tuesday injury aftermath;
- Wednesday, Thursday and Friday practice reports;
- Friday game-status designations;
- Saturday transactions/elevations;
- Sunday morning reports;
- official inactive lists approximately 90 minutes before kickoff;
- final close.

Important NFL features:

- named quarterback status, expected start probability and backup value;
- offensive-line continuity and clustered absences;
- receiver/secondary availability groups;
- practice participation progression: DNP, limited, full;
- travel, rest, short week, bye and time-zone effects;
- dome/outdoor state and point-in-time wind/precipitation/temperature;
- movement across key spread numbers such as 3 and 7;
- movement across important total bands;
- market-leader changes and bookmaker follower lag.

Quarterback information must be explicit and probabilistic. A questionable designation alone is not equivalent to confirmed inactivity. The existing NFL market and player-availability shadows should consume the same canonical point-in-time events.

## Match reports and press conferences

Archive full source references and short structured facts, not unsupported sentiment. Match reports affect future matches only and may contribute:

- injuries sustained;
- restricted return from injury;
- role or formation changes;
- workload and fatigue;
- misleading score/xG context;
- disciplinary incidents;
- coach explanations relevant to the next game.

Press-conference events must retain the actual publication/capture time and language distinguishing confirmed facts from uncertainty. Later clarifications should supersede, not erase, earlier reports.

## Timing-model targets

At each valid decision timestamp create targets for:

- probability current selection price shortens by close;
- probability current selection price drifts by close;
- expected closing no-vig probability;
- expected closing spread/total line and price;
- expected CLV from betting now;
- best future executable price and time it first appears;
- probability the current best price disappears within 15/30/60 minutes;
- value of waiting versus betting now;
- action label: now, wait, split or none.

Action labels must account for minimum economically meaningful movement and realistic execution, not merely any one-tick fluctuation.

## Backtesting and leakage controls

- Split chronologically and group all rows from a match into the same fold.
- Train EPL, EFL and NFL separately at first.
- Fit transforms, bookmaker weights and thresholds using training data only.
- Never use closing values, later snapshots, confirmed line-ups or later news as features at earlier timestamps.
- Use the bookmaker's own `last_update` to avoid treating stale repeated API responses as new information.
- Evaluate fixed historical decision horizons to avoid choosing hindsight-perfect entry times.
- Preserve delisted markets and missing quotes; disappearance is informative and must not be silently forward-filled through close.

Primary metrics are expected-price/line error, direction Brier/log loss, calibration, realised CLV and price-disappearance accuracy. ROI is reported secondarily.

Baselines:

- always bet immediately;
- always wait until close;
- fixed sport/market entry time;
- current consensus predicts close;
- simple movement continuation/reversion;
- EPL/EFL confirmed-XI rule;
- NFL injury-report and inactive-list rules.

## Promotion gates

1. **Data gate:** high match linkage, valid timestamps, adequate bookmaker count and reliable close.
2. **Backtest gate:** chronological improvement over simple timing baselines.
3. **Calibration gate:** predicted movement probabilities calibrate on unseen matches.
4. **CLV gate:** positive expected and realised CLV after realistic quote availability.
5. **Prospective shadow gate:** frozen model succeeds across an adequate live sample.
6. **Limited deployment:** timing advice only; no selection or stake creation.

NFL, EPL and EFL are promoted independently by market. A successful EPL 1X2 timing model does not validate EFL totals or NFL spreads.

## Odds API reconnection checklist

1. Restore the server-side `ODDS_API_KEY`; never expose it to the browser.
2. Verify sport keys: `soccer_epl`, `soccer_efl_champ` and the configured NFL key.
3. Run one dry capture and preserve the raw response.
4. Confirm event IDs, commence times, team aliases and bookmaker timestamps.
5. Confirm required regions/bookmakers and markets are returned.
6. Validate decimal odds and spread/total sign conventions.
7. Test quota accounting and per-request cost.
8. Insert snapshots idempotently into raw append-only storage.
9. Confirm opening and closing snapshots are explicitly marked by derived logic.
10. Turn on freshness, missing-sport, bookmaker-collapse and quota alerts.
11. Start baseline schedules, then activate event-driven captures.
12. Produce a daily coverage report by sport, match and market.

## Minimum daily health report

For each sport report:

- upcoming matches expected versus linked;
- most recent successful capture;
- snapshots per match/market;
- bookmaker count and change from prior capture;
- null or invalid prices/points;
- unmatched teams/events;
- events missing kickoff times;
- stale bookmaker quote rate;
- API requests consumed and remaining;
- whether a final closing capture was secured.

## Initial implementation order after reconnection

1. Connect and validate EPL/EFL/NFL raw capture.
2. Add canonical identities and append-only storage.
3. Add quota-aware baseline scheduling and monitoring.
4. Add official line-up/inactive and injury event capture.
5. Add press-conference, weather and match-report archives.
6. Build fixed-horizon market states and closing targets.
7. Run descriptive movement reports and simple timing baselines.
8. Accumulate a meaningful independent-match sample.
9. Train separate shadow timing models.
10. Review for promotion only after chronological and prospective gates pass.

## Current status

The shared cloud collection foundation was implemented on 3 September 2026 for AFL, NRL, EPL, EFL, NFL and UCL:

- `supabase/migrations/20260903_market_timing_snapshots.sql`
- `cloud/odds_collector.py`
- `cloud/collection_health.py`
- `cloud/news_event_ingest.py`
- `cloud/odds_collection_config.json`
- `cloud/Dockerfile`
- `cloud/railway.json`
- `cloud/README.md`

It includes change-only quote history, latest-state upserts, fixed checkpoints, soccer draws, adaptive cadence, quota recording, health/storage thresholds and canonical news intake. Six focused collector tests pass.

Live collection remains hard-disabled through `ODDS_COLLECTION_LIVE_ENABLED=false` until The Odds API is reconnected, the migration is applied and controlled dry/live validation succeeds. Automated source-specific news scraping is not yet enabled; the durable intake/schema is ready for those connectors. No timing model may influence bets until data-quality and shadow gates have passed.
