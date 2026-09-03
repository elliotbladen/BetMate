# NFL build handover — 2026-08-30

## User direction

Build NFL in substantially more detail than EPL, targeting roughly four to six
useful layers rather than forcing ten. Go deep on quarterback research in the
shadow. Paid data may be trialled cheaply, but it continues only if a frozen
test beats the core model and shuffled controls. This session is the conclusion
for today.

## Completed

### Step 1 — data contract

- Locked game IDs, team relocation mappings, dates, feature timing and the
  negative-home-favourite spread convention.
- Rebuilt 3,151 unique 2014–2025 regular-season games.
- Contract passes; closing-spread coverage is 3,065 games.
- The manual 50-game true-opener audit remains intentionally deferred.

### Rule eras

- Added dynamic kickoff from 2024.
- Added onside declaration while trailing, touchback to the 35 and both-team
  regular-season OT possession from 2025.
- Added a separate 2026 onside-alignment flag.
- Actual onside events are forbidden pre-game features.

### Step 2 — baselines

- Rolling 2019–2024: ridge margin MAE 10.31, Elo 10.58, closing spread 9.83.
- Ridge total MAE 10.77, closing total 10.35.
- The 2025 vault has never been predicted or evaluated.

### Step 3 — personnel and context

- Downloaded official nflverse weekly rosters and injury reports for 2014–2025.
- Built prior-game QB posteriors, uncertain-starter mixtures, roster/OL/receiver
  continuity and timestamp-checked position-weighted injury burden.
- Core + QB + continuity: margin MAE 10.11 versus core 10.31.
- Shuffled QB worsened to 10.35, supporting a genuine QB signal.
- Injuries were not promoted; weather remains diagnostic without forecast
  capture timestamps. All personnel components remain shadow-only.

### Step 3.5 — deep QB lab

- Downloaded free nflverse-hosted FTN charting for 2022–2025 (cost USD $0).
- Tested catchability, interception-worthy plays, QB-fault sacks, pocket escape,
  blitz, play action, motion, throwaways and created receptions.
- On 544 games from 2023–2024, core MAE was 10.37 and core + FTN was 10.47.
- FTN detail was rejected for promotion but retained prospectively.
- Cheapest useful paid experiment is one month of PFF+ at USD $24.99 using CSV
  exports. Subscription API access is not included. No purchase was made.
- A provider-neutral PFF/SIS import schema is in `ml/nfl/qb_lab.py`.

### Step 4 — challenger and calibration

- Installed scikit-learn and added it to requirements.
- Independent shallow tree: MAE 10.294 versus ridge 10.309, but RMSE worsened
  from 13.260 to 13.291. No promotion.
- Margin-derived H2H: Brier 0.2250, log loss 0.6413, accuracy 65.29%.
- Direct calibrated H2H was worse on all three; rejected.
- Closing market remains strongest. Blending stays disabled until at least 500
  frozen prospective predictions.

## Current state and next session

- Data contract passes.
- 2025 vault remains sealed with zero predictions in Steps 2–4.
- All active pricing remains unchanged; all new work is shadow research.
- Paid test gate: trial one month only, import licensed CSV, freeze fields and
  thresholds, compare core/core+paid/shuffled-paid, cancel if it fails.
- Next delivery step is Step 5: freeze code/config/model hashes, then run the
  vault exactly once and begin the 2026 paper season only when the user approves
  opening the vault.

## End-of-session clarification

- Step 4 did not place or simulate bets at the opening line.
- The reported 65.29% is outright winner accuracy, not an opening-line betting
  strike rate and not proof of profit.
- Step 4 compared predictions with results, closing spreads and closing
  moneyline probabilities.
- A valid opener simulation still requires the precise obtainable bookmaker,
  timestamp, price, spread pushes/key numbers, bookmaker margin, closing-line
  value, flat-stake profit and ROI.
- The deferred true-opening-line audit must be completed before any historical
  opening-line profitability claim is accepted.

## Step 5 update — 2026-08-31

- User explicitly authorised the one-time 2025 vault opening.
- Frozen inputs were hashed before prediction; 272 label-free predictions were
  written and hashed before scoring.
- Ridge margin MAE 10.162/RMSE 12.978; tree MAE 10.137/RMSE 13.014.
- Personnel oracle worsened to MAE 10.343 and is not promoted.
- Margin-derived H2H achieved 65.81%; direct H2H 61.76%; market 67.19%.
- Ridge remains the structural paper candidate. Tree remains shadow-only.
- No tuning against 2025, no blending and no staking are authorised.
- The 2026 paper protocol is frozen in `ml/nfl/step5_paper_2026.yaml`.

## Step 6 update — 2026-08-31

- Reconstructed 32 final-2025 team states and applied the frozen 0.35 offseason
  regression for 2026 Week 1.
- Frozen 16 label-free, market-free Week 1 paper predictions before capturing
  the schedule reference; prediction SHA-256 begins `d263696e`.
- Refit the fixed ridge specification through 2025 without changing
  hyperparameters; tree output remains an independent shadow.
- Activated all 2026 rule-era flags.
- Schedule lines have no bookmaker or original quote timestamp, so all 16 are
  reference-only and zero qualify for CLV/ROI.
- Starting QBs are unresolved; T0 status is baseline paper only/no bet.
- Staking remains disabled. Step 6 is a paper launch, not a betting launch.

## Live odds availability note — 2026-08-31

- The user confirmed that the live Odds API subscription is currently expired
  and is expected to be renewed in approximately one week.
- Until a valid key is restored, missing live quotes are an expected upstream
  limitation, not a model failure.
- The frozen Week 1 predictions remain valid as paper forecasts, but no schedule
  reference or stale fallback price may be treated as an obtainable bookmaker
  quote.
- Valid-quote count remains zero, staking remains disabled and CLV/ROI grading
  remains unavailable until timestamped bookmaker quotes are captured.
- After renewal, odds collection may resume without regenerating or modifying
  the frozen Step 6 prediction file.

## Step 7 update — 2026-08-31

- Added `ml/nfl/step7_market_shadow.py`, supporting direct Odds API capture,
  offline validation and offline import.
- Captures are append-only, timestamped and hashed; the frozen Step 6 prediction
  hash is checked before any market evidence is written.
- Quote qualification checks matchup mapping, bookmaker identity, aware
  timestamps, pre-kickoff timing, decimal prices and spread/total consistency.
- T0 data health, T1 structural baseline, T2 QB/personnel shadow and T3
  continuity/injury shadow states are emitted for every frozen game.
- All recommendations remain `WATCH` or `PASS`; betting thresholds and staking
  remain disabled.
- An expired or missing Odds API key produces `upstream_unavailable` and no fake
  market archive.
- NFL architecture plus Step 7 validation suite passes 24 tests.

## Step 8A update — 2026-08-31

- Added a clean historical split: T2 is QB plus reported availability; T3 is
  roster, offensive-line and receiver continuity.
- Reran 1,599 expanding-window games from 2019–2024 with zero 2025 vault rows.
- T2 improved margin MAE by 0.142 points in aggregate and in 5/6 seasons.
- T3 improved margin MAE by 0.082 points and in all 6/6 seasons.
- T2+T3 improved MAE by 0.204 points and in all 6/6 seasons, but the gain varied
  substantially by year.
- Within-season shuffled T2 and T3 controls both worsened the T1 baseline.
- QB-only tracked the closing spread best; the crude injury burden weakened the
  combined close comparison, so generic injury points remain rejected.
- Added `ml/nfl/step8_tier_audit.py`, JSON/Markdown reports and a negative-control
  test. The focused NFL suite now passes 25 tests.

## Step 8B update — 2026-08-31

- Added a timestamped live T2/T3 input contract and a 16-game Week 1 template.
- No quarterback, injury or continuity value was fabricated; all games currently
  fail closed as unresolved and receive no tier score.
- Trained a shadow-only coefficient artifact through 2024 on 2,879 development
  games. Historical actual starters remain oracle-only.
- T2 mixes starter and backup profiles using a timestamped starter probability.
- Simple injury fields remain diagnostic with zero applied points.
- T3 continuity produces a separate model-derived shadow contribution.
- Combined output is labelled uncapped/unapproved, cannot overwrite T1 and
  cannot enable staking.
- The focused NFL suite passes 28 tests.

## Step 8C update — 2026-08-31

- Built 446 regressed QB profiles from play-by-play through 2025; 104 profiles
  belong to players who appeared in 2025.
- Added a 16-game reviewed-starter sheet requiring starter, backup, probability,
  source, published timestamp and review cutoff.
- The adapter resolves player IDs and inserts historical profiles without using
  future 2026 performance.
- A blank or unresolved review writes no enriched file and applies no points.
- The focused NFL suite passes 30 tests.

## Step 8D update — 2026-08-31

- Downloaded the official nflverse 2026 weekly-roster and depth-chart release
  assets, both updated 30 August, and archived their hashes.
- The 2026 injury release does not yet exist, so injury inputs remain unresolved.
- Extracted timestamped QB1/QB2 candidates for all 32 teams without assigning
  unsupported starter probabilities.
- All QB1 candidates and 28/32 QB2 candidates have historical profiles; missing
  backups require an explicit no-history prior if they become relevant.
- Rejected the first T3 continuity calculation because the pre-cut roster has
  89.125 ACT/INA players per team. Its 0.33–0.53 returning shares are denominator
  artefacts and are retained only as ineligible diagnostics.
- T3 will be recalculated after final cuts when average active/inactive roster
  size is no greater than 60.
- The focused NFL suite passes 32 tests.

## Step 8E update — 2026-08-31

- Built point-in-time venue features for neutral site, roof, surface and prior
  team familiarity with each stadium.
- Walk-forward tested 1,599 games from 2019–2024 with shuffled controls and zero
  2025 vault predictions.
- Venue context slightly worsened margin MAE (10.309 to 10.314) and is rejected
  for side adjustments.
- It improved total MAE from 10.767 to 10.707 in 5/6 seasons; shuffled venue data
  worsened to 10.781. T4A remains a totals-only shadow.
- T4A moved farther from the closing total, so it is not evidence of a pricing
  edge and cannot affect bets.
- T4B travel remains untested because coordinates/distances are absent.
- The focused NFL suite passes 33 tests.

## Step 8F update — 2026-08-31

- Archived the T4A venue study with file hashes.
- Tested nonlinear short-rest, very-short-rest, long-rest, rest-mismatch and
  unusual-weekday features on 1,599 walk-forward games from 2019–2024.
- T5 worsened margin MAE from 10.309 to 10.343 and total MAE from 10.767 to
  10.785; it was better in only 1/6 margin seasons and 2/6 total seasons.
- T5 also moved farther from both closing spreads and closing totals and
  performed worse than shuffled controls.
- T5 is rejected as a separate tier. T1 retains only its regularised linear rest
  difference/sum; no manual bye or short-week points are allowed.
- The focused NFL suite passes 34 tests.

## Step 8G update — 2026-08-31

- Verified the T5 archive hashes before proceeding.
- Built an observed-weather oracle for totals using open-air status, availability,
  nonlinear wind and temperature features.
- On 1,599 walk-forward games, total MAE improved from 10.767 to 10.724 in 4/6
  seasons; shuffled weather worsened to 10.841.
- Weather moved farther from the closing total (2.686 to 2.736 MAE), so it is not
  evidence of a betting edge.
- T6 is approved only for a future timestamped totals shadow. Observed schedule
  weather can never populate a live pregame price.
- The focused NFL suite passes 36 tests.

## Step 8H update — 2026-08-31

- Verified the sealed T6 oracle archive and implemented an Open-Meteo live
  forecast collector with immutable raw/normalized captures and hashes.
- Added a 16-game Week 1 stadium registry containing schedule stadium identities
  but no fabricated coordinates.
- Collection requires verified WGS84 coordinates, coordinate source and
  verification timestamp for every game.
- Kickoff-hour through +3-hour temperature, precipitation, wind and gusts are
  normalized for the totals shadow.
- Current result is `unresolved_no_weather_capture`: 0/16 coordinates verified,
  zero API calls and zero forecast archives.
- The focused NFL suite passes 37 tests.
