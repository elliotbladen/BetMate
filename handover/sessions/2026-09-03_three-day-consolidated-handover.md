# BetMate three-day consolidated handover

Period: 1–3 September 2026

## Executive summary

The last three days moved BetMate forward in four major areas. First, the EPL
and Championship process was turned into a repeatable saved-bet and whole-model
CLV/ROI review workflow, while the normal production model remained separate
from player and xG shadows. Second, Champions League modelling advanced from an
architecture proposal into a substantial sourced, tested modelling stack for
the new 36-team format. Third, AFL/NRL finals were priced with Monte Carlo,
staking and Tier 2 rules were tightened, and the next-season market-timing
research direction was frozen. Fourth, the racing engine gained a corrected
young-horse achieved-run shadow and a complete Expected Tempo shadow system,
including cloud-ready Sydney/Melbourne race-day collection architecture.

The meaningful workspace is now on GitHub `main`. The two final commits were:

- `b7d5552` — automated Expected Tempo engine and cloud architecture.
- `35758b0` — complete BetMate modelling-workspace sync, including 230 UCL
  files and all other meaningful local work.

Temporary downloads, local databases, caches and environment secrets were not
committed. An Odds API key found in documentation was redacted from the latest
tree. Because it existed in earlier Git history, rotate that key before using
The Odds API again.

## 1. EPL and EFL Championship

Results and Football-Data opening/closing prices were imported and used to
grade the saved Week 1/Week 2 selections. Reports now separate EPL from the
Championship, separate gameweeks, and distinguish actual saved bets from the
larger set of all model predictions. Both ROI and CLV are retained; opening
edge, closing edge, price CLV and realised result must not be conflated.

The all-model archive is under
`BettingEngine/outputs/results/all model results/`. Saved-bet and player-shadow
reports are under `BettingEngine/outputs/results/`. The Week 2 player-shadow
diagnostic showed encouraging 1X2 CLV in both competitions, but totals were
mixed or poor and the sample is only one round. Player shadow therefore remains
a comparison layer, not the production betting engine.

Week 3 EPL and the next Championship card were priced with injuries added.
Normal-model bets were saved using the agreed minimum 10% EV rule. Matrix
confluence can increase a qualifying bet to 1.5 units only when the matrix is at
least net +6; matrix strength cannot rescue a bet below 10% EV. The normal
engine owns selections. The player-shadow engine remains separate and is used
only for comparison until formal validation.

Important operating rule: short-run ROI can be brutal even with positive CLV,
but positive CLV is not a guarantee that ROI will automatically turn positive.
Continue judging calibration and closing-price performance across a much
larger frozen prospective sample.

## 2. Champions League

The UCL build now reflects the modern UEFA format: 36 clubs, a single league
phase, coefficient-pot draw constraints, unequal schedules, top-eight/top-24
qualification states, two-leg knockout ties without away goals, and a neutral
final. It shares general football infrastructure but retains UCL-specific
competition logic and validation.

Delivered components include:

- frozen rules and data contracts;
- canonical club identity and alias auditing;
- cross-league attack/defence strength with league and UEFA-prior shrinkage;
- league-phase draw validation and table simulation;
- aggregate-score knockout and qualification simulation;
- stage, rest, travel, player and suspension context contracts;
- 1X2, totals and tournament market contracts;
- chronological walk-forward and format-aware backtests;
- sourced openfootball match history and newer SofaScore/FotMob xG/stat data;
- market import/mapping work for available historical 1X2 and total prices;
- separate xG-only and corner-enhanced Under/Over 2.5 challengers;
- player-shadow architecture matching the EPL/EFL separation principle.

The source archive includes 1,997 UCL main-competition matches from 2011/12 to
2025/26, with 189 matches in each of the first two modern-format seasons.
The two-season totals archive has 378 matches; normalized SofaScore statistics
cover 342. The 2025/26 corner-enhanced totals test covered 186 games and showed
Brier 0.21538 versus 0.21258 for market-only. Its small 5% edge subset returned
+7.31% paper ROI over 64 bets, but that is insufficient for promotion.

UCL 1X2 and U/O 2.5 remain separate predictive markets. Corners remain a
totals challenger. Player shadow remains shadow-only and currently lacks a
timestamped UCL player-event backfill. Static bookmaker archives labelled
`unverified_static_close` must remain unverified until genuine timestamps are
available. Do not merge 1X2 and totals into one bet model and do not promote a
challenger from a small profitable subset.

All 35 UCL unit tests passed after repairing the test draw fixture so it
correctly contained all 144 modern league-phase fixtures.

## 3. AFL and NRL

The late-August AFL/NRL market review compared model preferences against both
opening and closing AusSportsBetting markets. NRL preferred H2H sides won 6/8;
flat opening-price return was +0.76 units and mean price CLV was +6.1%. Applying
the proposed 10% opening-EV gate left six qualifiers: five positive-CLV bets,
mean CLV +8.4%, five winners and +1.51 units. This is encouraging but represents
one round, not proof.

The review reinforces the user’s season diagnosis: NRL H2H may have been
materially better under disciplined selection and flat/rule-based staking.
Multis, marginal bets and inconsistent staking obscured the underlying model.
Next season must keep H2H, handicap and totals reports separate and test the
10% EV rule over the whole archive. NRL totals remain a recalibration priority.

AFL’s useful ML H2H signal remains, but H2H probability and rules-based margin
were internally inconsistent in the wildcard review. AFL still needs the
planned NFL/EPL-style partial rebuild: preserve useful ML and contextual
features, repair probability/margin coherence, and rebuild weak totals logic.

Finals pricing was produced with Monte Carlo. The NRL Tier 2 matchup adjustment
was corrected to a hard maximum of three points; stale six-point behaviour is
not authorised. Saved finals bets and simulations are under
`BettingEngine/outputs/bets/`, `BettingEngine/outputs/monte_carlo/` and
`BettingEngine/results/`. AFL matrix review found no sufficient confluence for
the three saved selections, so they remained at normal stakes.

## 4. Market-timing and cloud collection

Historical AFL/NRL odds snapshots are sufficient for a pilot descriptive and
timing backtest, but the dense raw database archive still needs to be recovered
or exported from the machine that collected it. The correct ML question is not
“who wins?” but “should an already-approved bet be taken now, later, split, or
left without a timing recommendation?” Train AFL and NRL separately and group
all snapshots from one match into one chronological fold.

A common cloud collection foundation was implemented for AFL, NRL, EPL, EFL,
NFL and UCL. It provides append-only odds quotes, canonical latest states,
fixed checkpoints, adaptive cadence, API-quota records, collection health and
timestamped news-event intake. Key files are:

- `supabase/migrations/20260903_market_timing_snapshots.sql`
- `cloud/odds_collector.py`
- `cloud/news_event_ingest.py`
- `cloud/collection_health.py`
- `cloud/odds_collection_config.json`
- `cloud/README.md`

Live collection is deliberately disabled with
`ODDS_COLLECTION_LIVE_ENABLED=false`. Activation requires a rotated Odds API
key, Supabase migration, Railway/environment configuration, dry capture,
identity validation and quota checks. The architecture is designed to run in
the cloud while both laptops are off.

News must preserve both publication and capture timestamps. Archive official
teams, injuries, press conferences, match reports, weather and material role
changes. Later information must never leak into earlier simulated decisions.
The timing model cannot create a bet; it can only advise execution for a bet
that already passes the production model’s EV and staking rules.

## 5. Racing ratings and sectional data

Sydney sectional coverage was audited and the ATC Swiss Timing source was
integrated. The importer validates the report year, cleans runner identities,
adds finish clocks where derivable and safely matches sectional runners to
official results. Melbourne/Racing.com and Sydney/ATC data now support the
race-day tempo design.

The Guest House investigation found a systematic young-horse compression issue
in accepted `form-first-v2.0`: opposition collateral dominated the level while
age/WFA normalization, winner margin, time and sectional achievement did not
raise the accepted performance. Guest House remains 98.46 in the accepted
model but rated 104.30 as a V2.10 achieved run. Oliveanotherday rated 110.36 and
Natural Fling 98.55 in that shadow, preserving a sensible performance order.

V2.10 is `SHADOW_ONLY_AMBER`. It reduced historical young Group/Listed
compression, but full achieved-run uplift failed as an automatic next-start
forecast. The validated three-year-old carry-forward candidate is only 15% of
the uplift. Production remains `form-first-v2.0`; V2.10 cannot affect prices or
bets until append-only prospective monitoring and its stored promotion policy
pass.

## 6. Expected Tempo engine

The five-step Expected Tempo build is complete in shadow:

1. immutable race/meeting feature dataset;
2. physical and relative tempo targets;
3. chronological backtest and probability calibration;
4. race-day replay that updates only from prior completed races;
5. append-only governed snapshots and promotion scorecard.

The completed replay produced 872 snapshots and 649 eligible governed updates.
Middle/late continuous MAE improved in all three folds, but classification log
loss lost to V0 in fold two. Status therefore remains `SHADOW_ONLY_AMBER`.
Early tempo stays at V0; same-going completed races can create capped
middle/late shadow updates. Different-going evidence gets zero live weight.
`horse_price_integration=false` is enforced. No tempo output may change a horse
price until prospective gates pass and a separate integration decision is
recorded.

Cloud-ready race-day automation is implemented for Saturday Sydney and
Melbourne meetings. It discovers cards, polls during the configured race-day
window, archives observations and writes immutable Supabase tempo snapshots.
The code is ready but not deployed because Supabase credentials and Railway
control were unavailable. Saturday’s Sydney run is still required to measure
actual ATC PDF publication latency.

## 7. Tipping fix

The EPL tipping transition was fixed so advancing the visible gameweek does not
discard unresolved fixtures from the preceding week. Results synchronization
continues checking the relevant previous gameweek, preserving each person’s
stored tip and awarding points when the final match becomes complete. The
TypeScript tipping test exists, but the Windows checkout lacked installed Node
dependencies (`tsx`), so it could not be executed during the final sync.

## 8. Immediate next actions

1. On the MacBook, pull `origin/main` and confirm commit `35758b0`.
2. Rotate the exposed Odds API key; store the replacement only in local/cloud
   environment variables.
3. Install Node/Python dependencies on the Mac and run the tipping, UCL, NFL,
   Expected Tempo and cloud tests.
4. Apply both Supabase migrations only after reviewing the target project.
5. Deploy odds collection disabled, run dry validation, then enable it when the
   Odds API subscription is restored.
6. Deploy the tempo worker disabled, validate Sydney/Melbourne discovery and
   source latency, then begin append-only shadow collection.
7. Recover/export the older dense AFL/NRL odds database for timing research.
8. Keep normal football engines, player shadows, market-timing shadows, racing
   V2.10 and Expected Tempo strictly separated under their promotion gates.
9. Build V2.10’s prospective next-start snapshot/outcome monitor before making
   any promotion claim.
10. Continue UCL with timestamped player availability and verified close data;
    retain market-specific evaluation and chronological leakage controls.

## Current source-control state

GitHub `main` was verified at full hash
`35758b028b33ef4c56b6f7c01878f40ce63f3249`. The complete meaningful BetMate
workspace is available from that revision. The Windows working directory may
still show changes relative to its older locked local Git index; GitHub is the
authoritative transfer point for the MacBook.
