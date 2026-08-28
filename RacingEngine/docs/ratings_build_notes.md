# Ratings build notes

This is the permanent working record for the ordered ratings build in
`docs/ratings_build_plan.md`. Update it whenever a decision is made, code or data
changes, a report is produced, a test is run, or an unresolved issue is found.

Each entry records:

- what was intended;
- what changed;
- what was produced;
- how it was tested;
- what was learned;
- decisions made; and
- open issues or blockers.

## 22 August 2026 — revised context gates 1–6

### What was intended

Freeze the accepted base, separate race weight conditions, reconstruct true
weight evidence, calculate changes between runs, assemble the remaining context
and create a leakage-safe table for later learning.

### What changed

- Added `racing_engine/context_features.py`.
- Added `runner_weight_contexts` and `point_in_time_features` to storage.
- Added `tests/test_context_features.py`.
- Added `docs/context_feature_architecture.md` and revised this build plan.
- Froze `performance-par-v1.0`; all weight-response variants remain shadow.
- Classified races into handicap, quality handicap, WFA, set weights, set
  weights plus penalties and unknown.
- Stored carried weight, official WFA, field-relative weight and chronological
  weight/rating/class/distance changes independently.
- Added strictly prior Race Strength, daily variant, going, sectional quality,
  DT-W, steward event counts, days since last run and campaign run number.
- Marked target-result weight as ineligible in point-in-time availability data.

### Outputs

- `data/outputs/context_feature_build_2026-08-22.json`
- 29,845 `weight-context-v1.0` rows.
- 29,845 `point-in-time-context-v1.0` rows.
- Weight-condition counts: 19,133 handicap; 2,744 quality handicap; 2,628 set
  weights; 3,945 set weights plus penalties; 1,382 WFA; 13 unknown.
- Prior-feature coverage: 20,571 weight; 20,749 Race Strength; 16,917 daily
  variant; 18,280 sectional confidence; 3,719 rows with steward evidence.
- 9,096 target rows have no linked prior run and remain honest debutant/no-history
  rows rather than being dropped.

### Testing

- Added race-condition precedence and strict-prior-history tests.
- Confirmed the second race sees the first race's weight, never its own result.
- Full project suite: 65 tests passed using `.venv/bin/python`.
- A system-Python run initially missed the installed `pypdf` dependency; this
  was an interpreter/environment issue, not a code failure.

### Findings and decisions

- Carried-weight coverage is strong (29,456/29,845), official WFA could be
  calculated for 23,526 rows, and allocated weight is separately available for
  only 354 rows.
- The stored source data provides zero separately verified apprentice-claim,
  overweight or penalty values. These fields stay NULL.
- No predictive improvement is claimed in this work. It creates the correctly
  timed input table required to measure improvement next.
- Do not promote either prior weight experiment: both were worse on headline
  validation and holdout log loss and their uncertainty intervals crossed zero.

### Problems encountered and addressed

- The first contextual rebuild performed a lookup per runner. It was replaced
  with bulk joins and bulk insertion.
- Daily variants have many as-of snapshots. They are collapsed to one historical
  meeting value for the prior-run summary rather than multiplying runner rows.
- Steward names use their own normalized identity. Current exact-name matching
  recovers 3,719 prior rows; durable horse-ID linking remains an improvement.

### Open work

1. Capture pre-race allocated weight, apprentice claim, overweight and penalties
   from a provenance-preserving source/card snapshot.
2. Add explicit minimum-weight and compressed-weight-scale evidence.
3. Link steward events to durable horse IDs.
4. Audit same-day daily-variant timing before using any live-race feature.
5. Import timestamped Betfair markets.
6. Train and ablate small candidates chronologically; do not tune on holdout.

## 22 August 2026 — current-form and race-ranking experiments

### Objective

Test the first two improvement branches without changing the accepted model:
better current-form state and a race-level probability/ranking model.

### Implementation

- Added `racing_engine/form_ranking_research.py`.
- Added `tests/test_form_ranking_research.py`.
- Used the existing 152 chronological `performance-par-v1.0` horse-state
  cutoffs and `point-in-time-context-v1.0` features.
- Fitted coefficients only on the frozen train period ending 31 August 2024.
- Tested 864 train, 789 validation and 793 historical-holdout races.
- Used race-level softmax/conditional-logit probability books.
- Added an internal chronological 70/30 training split to select regularization
  without consulting validation or holdout.

### Results

All log-loss and Brier deltas below are candidate minus baseline; negative is
better.

| Candidate | Validation log loss | Holdout log loss | Validation Brier | Holdout Brier | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| peak + history | -0.001563 | -0.001845 | -0.000332 | -0.000367 | freeze/revise |
| current form | -0.001955 | -0.002062 | -0.000410 | -0.000412 | freeze/revise |
| race core | -0.004210 | -0.008129 | -0.000994 | -0.001713 | freeze/revise |
| race core, training-CV regularized | -0.003060 | -0.005944 | -0.000719 | -0.001266 | freeze/revise |
| full race level | -0.002662 | -0.007372 | -0.000834 | -0.001665 | freeze/revise |

The training-CV race core had validation interval `[-0.006350, 0.000264]` and
holdout interval `[-0.010329, -0.001637]`. It nearly passed validation, but the
upper bound remained above zero. The full race-level model also reduced the
holdout top-pick strike rate by 1.26 percentage points, so it is not acceptable.

### Findings

- Peak form and deeper history consistently add a small positive signal.
- Greater uncertainty receives a negative fitted coefficient.
- Prior official rating adds information beyond the current base rating.
- Campaign stage adds a small positive signal and long layoffs a small negative
  signal.
- Prior Race Strength fitted negatively and damaged top-pick ranking in the full
  model. This may represent regression/fatigue/class-placement confounding; it
  must not be interpreted causally.
- Regularization selected entirely inside training reduced ranking damage and
  retained improvements, but did not make validation conclusive.

### Decision and freeze strategy

- No official promotion.
- Freeze `race-level-conditional-logit-v1.0-core-cv` as the leading prospective
  candidate.
- Do not continue tuning coefficients against these observed evaluation races.
- Confirm on genuinely new races, or switch to the separate time/margin branch.
- The accepted rating remains `performance-par-v1.0`.

### Market policy recorded

- Compare ratings to market prices only for 2025 through 15 August 2026.
- Treat 2023–24 as immature rating-development history.
- Keep ratings and eventual race-day pricing engines separate.
- Freeze the future rule at 15% expected value versus opening price before
  examining betting returns; report opening and closing comparisons separately.

### Outputs and verification

- `data/outputs/current_form_ranking_research_2026-08-22.json`
- `data/outputs/current_form_ranking_research_2026-08-22.md`
- Full repository test result: 68 passing tests.

## 22 August 2026 — improvement Step 3: time and margins

### Objective

Determine whether form-anchored winning and beaten margins improve the time
rating itself, without confusing the result with the separate identity change.

### Changes

- Added `racing_engine/time_margin_stage3.py`.
- Added `tests/test_time_margin_stage3.py`.
- Produced `data/outputs/stage3_time_margin_2026-08-22.json` and Markdown.
- Compared 25%, 50% and 100% blends of the existing anchored-margin state.
- Required each candidate both to add information over the identity-only time
  model and to beat the accepted raw-name V1 baseline.
- Used identical runner books across 1,582 races and meeting-day bootstrap
  uncertainty under the frozen evaluation protocol.

### Results

| Candidate | Validation Δ vs identity | Holdout Δ vs identity | Validation interval | Validation Δ vs official | Holdout Δ vs official |
| --- | ---: | ---: | ---: | ---: | ---: |
| margin 25% | -0.000588 | -0.001661 | [-0.001173, -0.000016] | +0.000665 | +0.000778 |
| margin 50% | -0.001101 | -0.003098 | [-0.002297, +0.000048] | +0.000152 | -0.000658 |
| margin 100% | -0.001904 | -0.005270 | [-0.004190, +0.000336] | -0.000651 | -0.002831 |

All three blends improved Brier score versus the identity-only control in both
periods. The 25% blend gave the cleanest isolated margin evidence, while the
100% blend was the only version to beat the official baseline in both periods.
No version achieved both conditions simultaneously.

### Interpretation

- Margins contain genuine-looking information beyond the time/identity state.
- Conservative margin use is more statistically stable.
- The identity-only control is slightly worse than official V1, creating a
  hurdle that the conservative blends cannot recover.
- A stronger margin adjustment recovers and beats V1, but its isolated
  validation evidence is not sufficiently certain.
- Selecting an untested intermediate strength after reading these results would
  be validation tuning and is prohibited.

### Decision

- No promotion.
- Freeze the Step 3 margin branch.
- Retain the full anchored-margin formula as a prospective shadow because it
  beats official V1 directionally in both periods.
- Do not change its coefficient until genuinely new races are available.
- Proceed to Step 4 pace and sectionals as a distinct research branch.

### Verification

- Blend endpoint and runner-book mismatch tests pass.
- Full repository suite: 70 tests passed.

## Step 1 — automated data-readiness report

### Status

Implemented and tested on 21 August 2026. The audit itself is complete. Its
current database verdict is `NOT_READY`, with explicit gaps to investigate.

### Changes

- Added `racing_engine/readiness.py`.
- Added `tests/test_readiness.py`.
- Added a read-only CLI supporting date, state and source filters; JSON and
  Markdown output; and an optional failing exit code for automation.
- Separated structural blockers from optional coverage warnings.
- Treated a recorded steward-source absence as a completed check, not evidence
  that a race was incident-free.
- Kept missing DT-W values as unavailable rather than converting them to zero.

### Outputs

- `data/outputs/data_readiness_2026-08-15.json`
- `data/outputs/data_readiness_2026-08-15.md`

### Verification

- All 13 repository tests passed after implementation.
- The audit covered 2,471 races, 259 meetings and 29,845 runner rows.
- Result rows, class, weather and meeting-level steward checks had 100% coverage.

### Findings

- 399 races lack an official race clock.
- 25 races do not contain exactly one recorded finished winner.
- Margin coverage is 54.73%; most missing margins are in the NSW-authorised
  source, so source semantics must be investigated before treating all rows as
  equivalent defects.
- Runner-time coverage is 76.55% and sectional coverage is 85.79%.
- Historical pre-race-card coverage is 1.17%.
- Explicit DT-W coverage is 2.15%.
- Eleven source-meetings have a gap in their imported race-number sequence.

### Open issues

- Classify the 25 winner anomalies as source defects, dead heats, abandoned/no
  races, or parsing defects.
- Determine which missing official clocks can be recovered from an approved
  authoritative source.
- Confirm whether NSW missing margins are expected source unavailability or an
  importer gap.
- A future summary renderer may be useful because the full gap reports are
  intentionally large.

## Step 2 — freeze the evaluation protocol

### Status

Implemented and frozen on 21 August 2026 as `evaluation-v1`. The canonical
configuration hash is
`30714852ca6da02dca3cc7dd3da0d5af4064c0832af9b6f675933e14c410c693`.

### Implemented decisions

- Version an immutable evaluation configuration and store its SHA-256 hash with
  every evaluation.
- Freeze train, validation, historical-holdout and prospective-holdout dates.
- Score all actual starters, including non-finishers; exclude scratches.
- Retain debutants using the declared population prior rather than excluding
  difficult runners.
- Use race-weighted winner log loss as the primary metric, with Brier,
  calibration, ranking and coverage as secondary diagnostics.
- Compare candidate and baseline on the exact same race and runner set.
- Use paired meeting-day block resampling with a fixed seed.
- Permanently record every exclusion reason and promotion decision.

### Outputs and changes

- `config/evaluation_protocol_v1.json`
- `racing_engine/evaluation_protocol.py`
- `tests/test_evaluation_protocol.py`
- Added immutable prediction-ledger and benchmark-report tables to
  `racing_engine/storage.py` for Step 3.

### Verification

- Protocol date boundaries, overlap rejection and deterministic hashing pass.
- Scratchings are excluded while DNFs remain in the evaluated field.
- Missing winners and dead heats receive distinct exclusion reasons.
- Log loss and Brier calculations match hand-calculated fixtures.
- A future-data poison test confirms that an earlier V1 horse state is
  unchanged when an extreme future race is added.
- All 19 tests available at Step 2 completion passed.

### Notes

- The historical holdout is locked but cannot honestly be called pristine,
  because V1 had previously been inspected over this history.
- Data from 16 August 2026 onward is the genuinely prospective holdout.

## Step 3 — definitive V1 benchmark

### Objective

Run `performance-par-v1.0` through the frozen Step 2 protocol and preserve the
complete prediction-level evidence. This establishes the baseline that every
later model must beat; it does not change rating mathematics.

### Architecture

1. **Chronological prediction runner**
   - Iterate through eligible race dates in order.
   - Build horse state using only information strictly before each target date.
   - Generate a probability for every actual starter, including debutants and
     non-finishers.
   - Persist the information cutoff and protocol/model versions.

2. **Prediction ledger**
   - Store one immutable row per model, protocol, race and runner.
   - Include raw rating, probability, outcome, winner rank, history depth,
     eligibility, exclusion reason and component detail.
   - Enforce uniqueness so reruns replace an identical research artefact rather
     than silently duplicating observations.

3. **Metric engine**
   - Calculate primary log loss plus race- and runner-weighted Brier scores.
   - Produce fixed-bin calibration, top-one/two/three rates, winner-rank
     summaries and complete coverage/exclusion reconciliation.
   - Calculate the equal-probability benchmark on the same races.

4. **Segment engine**
   - Report by evaluation period, season, state, source, track, distance, going,
     field size, class family and history depth.
   - Mark small samples rather than suppressing unfavourable results.

5. **Permanent report**
   - Store JSON as the canonical result and render a concise Markdown report.
   - Record database cutoff, code revision when available, model version,
     protocol hash, metric definitions, exclusions and generation timestamp.

### Testing

- Hand-calculate probabilities, log loss, Brier and winner rank on tiny fixtures.
- Confirm probability books sum to one and include all actual starters.
- Confirm scratches are excluded and DNFs remain outcome-zero runners.
- Add extreme future results and prove earlier predictions do not change.
- Confirm the race on the target date cannot build its own horse state or par.
- Run twice and compare prediction ledgers and reports apart from timestamps.
- Reconcile total races into scored plus each mutually exclusive exclusion.
- Reconcile every overall metric with its underlying prediction rows.
- Confirm equal-probability and V1 use exactly the same eligible fields.
- Test date boundaries and every registered segment bucket.

### Completion condition

A reproducible, prediction-level V1 report exists for all frozen periods, all
tests pass, and no unresolved eligibility or look-ahead defect remains. Only
then does V1 become the accepted comparison baseline.

### Implementation result

Completed on 21 August 2026 under the frozen `evaluation-v1` protocol.

#### Changes and outputs

- Added `racing_engine/benchmark.py`.
- Added `tests/test_benchmark.py`.
- Added `benchmark_predictions` and `benchmark_reports` storage tables.
- Produced `data/outputs/definitive_v1_benchmark.json` and its Markdown
  rendering.
- Stored 16,937 runner-level predictions across 1,582 eligible races.

#### Results

- V1 mean race-weighted log loss: `2.326815`.
- Equal-probability log loss on the same fields: `2.335835`.
- V1 mean race Brier: `0.897784`; equal probability: `0.899526`.
- V1 top-rated strike rate: `14.73%`.
- Winner in top two: `27.56%`; winner in top three: `38.94%`.
- Mean winner rank: `5.159`.
- Validation log loss: `2.337710` over 789 races.
- Historical-holdout log loss: `2.315975` over 793 races.
- Fourteen races were excluded for no recorded winner and seven for multiple
  recorded winners.
- Every persisted race probability book sums to one within `1e-9`.

#### Important finding

10,554 of 16,937 evaluated runners used the population prior because V1 had no
prior usable horse state for them at that date. This explains why V1 improves
only slightly over equal probability and is a major limitation of the current
baseline, not evidence of a strong predictive model. The missing-state rate is
consistent with Step 1's NSW time/margin gaps and must remain visible in all
later comparisons.

#### Verification

- All 20 repository tests pass after Step 3.
- The integration test proves ledger idempotency, full starter coverage,
  debutant handling and deterministic headline metrics.
- The real ledger contains 1,582 probability books and none fail the sum-to-one
  reconciliation.
- The final report contains fixed calibration and segment diagnostics by
  period, season, state, source, track, distance, going, field size, class and
  runner history depth.

## Step 4 — normalize sectional semantics

### Objective

Create explicitly named, source-consistent sectional and pace features without
pretending that unlike NSW and Victorian markers represent the same distance.
This step changes data interpretation, not yet the accepted rating model.

### Architecture

1. **Source-semantic registry**
   - Version the meaning of each raw source field and marker.
   - Record whether a value is an individual segment, cumulative time, distance
     remaining, position, speed or distance travelled.
   - Reject unknown layouts rather than guessing their meaning.

2. **Canonical sectional layer**
   - Preserve `runner_sectionals` as raw normalized source evidence.
   - Add derived, versioned features with explicit names such as
     `final_200_seconds`, `final_400_seconds`, `final_600_seconds`,
     `position_600m`, and intermediate pace segments.
   - Store derivation method, required raw markers, source, parser/feature
     version, completeness and quality reason.

3. **Derivation engine**
   - Derive a canonical interval only when the required source markers exist.
   - Use addition or subtraction only where source documentation and fixtures
     prove the marker semantics.
   - Leave unavailable features null; never substitute final 200 for final 400.

4. **Quality and coverage report**
   - Report feature coverage by source, season, meeting, distance and marker.
   - Check impossible times, negative intervals, marker ordering, duplicate
     markers and runner/race mismatches.
   - Compare derived totals against supplied cumulative or finish clocks where
     an independent reconciliation is possible.

5. **Integration boundary**
   - Keep V1 unchanged while the canonical layer is built and inspected.
   - A later registered candidate may consume these features only through the
     frozen evaluation protocol.

### Testing

- Maintain fixed NSW old-layout, NSW new-layout and Victorian source fixtures.
- Test every documented source marker mapping independently.
- Hand-check final-200/400/600 arithmetic on known runners.
- Prove that missing required markers return null plus a reason.
- Prove that unlike markers are never silently substituted.
- Test cumulative-versus-interval conversions and rounding tolerances.
- Reject negative, duplicated, reversed and implausible sectional sequences.
- Confirm derived records retain complete provenance and feature version.
- Test idempotent rebuilding and deterministic coverage counts.
- Add a regression test for the current `marker_metres = 0` ambiguity so it
  cannot re-enter the rating model as a supposedly common final split.

### Completion condition

Canonical final-200/400/600 and intermediate pace fields have verified semantics,
source-specific regression fixtures pass, coverage and quality gaps are reported,
and no derived feature has been promoted into Horse Ability prematurely.

### Implementation result

Completed on 21 August 2026 as `canonical-sectionals-v1.0`.

#### Changes and outputs

- Added `racing_engine/sectional_features.py`.
- Added `tests/test_sectional_features.py`.
- Added the versioned `canonical_sectionals` table while preserving every raw
  `runner_sectionals` row unchanged.
- Produced `data/outputs/canonical_sectionals_v1_coverage.json`.
- Stored one canonical status row for each of 26,392 finished runner results.

#### Frozen source semantics

- Racing NSW stores consecutive 200-metre interval durations at
  metres-remaining markers. Final 200 requires markers 200 and 0; final 400
  requires 400, 200 and 0; final 600 requires 600, 400, 200 and 0. Missing an
  adjacent marker makes the derived interval null.
- Racing Victoria supplies `to 800`, `800 to 400`, and `400 to finish` durations.
  The last value is canonical final 400. The source does not supply final 200
  or final 600, so those remain null rather than being estimated.
- The Racing.com NSW result-fallback source has no equivalent sectional feed
  in the current database and is marked `unsupported_source`.

#### Coverage and quality

- NSW: 8,712/10,598 final-200 values and 8,711 final-400/final-600 values.
- Victoria: 12,253/12,271 final-400 values; final 200 and 600 are unavailable by
  source design.
- NSW result fallbacks: 3,523 runners with no supported sectional semantics.
- Quality status: 20,945 `ok`, 1,904 `incomplete`, 20 `outlier`, and 3,523
  `unsupported_source`.
- Slow outliers are retained and flagged rather than deleted: they may reflect
  an eased, injured or tailed-off horse rather than corrupt source data.

#### Verification

- All 25 repository tests pass.
- Tests cover NSW interval arithmetic, required adjacency, Victorian field
  meanings, unsupported sources, outlier flags, provenance and idempotency.
- A regression test proves the Victorian final 400 is never called final 200.
- Rebuilding produces the same coverage and does not duplicate canonical rows.

#### Model boundary

The frozen `performance-par-v1.0` benchmark still contains its documented
legacy `marker_metres = 0` feature. It is not rewritten after benchmarking.
Every new sectional candidate must use `canonical_sectionals`, so the old
NSW/Victoria mismatch cannot enter a promoted model.

## Environmental and contextual sectional adjustments

Step 4 standardises measurement only. Adjustments will be introduced in
separate registered tests so their effects remain identifiable:

- **Step 11:** estimate the daily track-speed variant, then test weight/WFA.
  Weather observations, including wind, are assessed here only through
  time-stamped, direction-aware candidate features. Going is separated from
  the daily variant so a generally soft track and an unusually slow meeting are
  not treated as the same thing.
- **Step 12:** test sectional pace shape, trip, DT-W, rail/lane pattern,
  barriers, steward evidence and today's projected map one layer at a time.
- Wind must account for course direction and sectional location; a raw wind
  speed without headwind/tailwind geometry is not a valid adjustment.
- Post-meeting variants may clean historical performance. A live prediction may
  use only observations available before that race and cannot use later races
  from the same meeting.

## Self-learning architecture review

Reviewed the sibling `BettingEngine` on 21 August 2026 to identify reusable
learning and automation patterns for RacingEngine. This was a read-only review;
no BettingEngine files were changed.

### Useful existing patterns

- Append-only, timestamped `market_snapshots` preserve price history rather than
  overwriting yesterday's market with today's value.
- `model_runs` provide an auditable record of a pricing execution.
- `ml_shadow_predictions` keep experimental ML output separate from official
  prices.
- `ingest_actuals.py` attaches later results and errors to earlier predictions.
- Walk-forward trainers and backtests use earlier seasons to predict later ones.
- `baz_learning_review.py` compares completed rules and shadow predictions and
  reports missing feedback data.
- Scheduled ingestion jobs demonstrate how regular results and market capture
  can run without manual commands.

### Important limitations not to copy

- BettingEngine is not one self-learning loop: ingestion, training, shadow
  prediction, actuals, reviews and promotion remain separate workflows.
- The learning review measures performance but does not retrain a model.
- Model artefacts have sometimes been local and unversioned, making exact
  reproduction across machines difficult.
- Some training/calibration fallbacks use random folds when chronological data
  is unavailable; RacingEngine must retain strict time ordering.
- Market coverage has been incomplete in several sports, which limits honest
  profitability and CLV conclusions.
- Promotion is documented but not enforced by one common champion/challenger
  registry and gate.

### RacingEngine learning timeline

1. **Now:** continue storing results and canonical evidence. Begin collecting
   append-only, timestamped racing prices as soon as an approved source and
   capture schedule are defined. Missing historical market snapshots cannot be
   reconstructed honestly later.
2. **After Step 10:** begin the first automatic learning cycle. New results can
   update Horse Ability and Race Strength, rebuild a challenger, replay the
   frozen evaluation, and write a comparison report. The accepted model remains
   unchanged unless the challenger passes review.
3. **After Steps 11–12:** the complete base feature system can retrain on an
   expanding window. Each feature family remains independently versioned so the
   system knows which change caused improvement or harm.
4. **After the pricing layer and market capture:** train a separate market-aware
   challenger and measure opening-price accuracy, decision-time value, closing
   line value and realistic returns. The objective Horse Ability model remains
   free of market inputs.
5. **After sufficient prospective evidence:** permit rules-based promotion.
   Initially require human approval. Automatic production promotion is only
   considered after repeated clean cycles, drift checks, reversible artefacts
   and several hundred genuinely unseen race predictions.

### Required automated loop

```text
new meeting data
  -> readiness and source-semantic checks
  -> update horse/race states
  -> train versioned challenger
  -> frozen walk-forward comparison
  -> prospective shadow predictions
  -> attach outcomes and market closes
  -> promotion report
  -> human approve/reject initially
```

Every run must store the data cutoff, feature manifest, protocol hash, code and
model version, training dates, predictions, metrics, exclusions and decision.
Failed challengers remain research evidence and never alter the accepted model.

## Step 5 — horse identity audit

### Status

Completed on 21 August 2026 as `horse-identity-v1.0`.

### Objective

Stop spelling, capitalization, country suffixes and source-layout debris from
splitting one horse into several histories. Preserve every original source name
while linking each runner observation to a durable internal horse ID. Never
merge an ambiguous identity merely because two strings look similar.

### Changes and outputs

- Added `racing_engine/horse_identity.py`.
- Added `tests/test_horse_identity.py`.
- Added `horses`, `runner_horse_links` and `horse_identity_reviews` tables.
- Populated the existing `horse_aliases` table with source spellings, durable
  IDs, canonical names, transformations and review status.
- Produced `data/outputs/horse_identity_v1_audit.json`.
- Reviewed aliases and runner links are protected from later automatic rebuilds.

### Main source defect found

The Racing NSW PDF parser's source name field often contains trailing layout
text representing finishing position and time. For example,
`LIFESAVER 3 67.1` is the source observation for `Lifesaver`. This affected
9,652 runner rows. The raw `runner_results.runner_name` remains unchanged for
auditability; only the identity layer removes the layout suffix.

### Identity rules

- Collapse whitespace and remove the proven NSW position/time layout suffix.
- Remove a terminal registered-country suffix such as `(NZ)` or `(IRE)` while
  preserving the original spelling as an alias.
- Normalize case, accents, spaces and punctuation into a conservative identity
  key.
- Generate a deterministic UUID-based internal ID from that key.
- Prefer a clean mixed-case Racing.com spelling for the canonical display name.
- Send empty or extremely short keys to review rather than linking them.
- Automatic rebuilds cannot overwrite a manually reviewed alias or link.

### Results

- 29,845/29,845 runner rows linked; zero unlinked rows and zero duplicate links.
- 9,096 durable horses created from 15,946 raw distinct name strings.
- 1,997 horses are linked across more than one result source.
- 9,652 NSW layout suffixes and 59 country suffix observations were normalized.
- No short/malformed identity keys required immediate manual review.
- The over-merge audit found zero horses containing different cleaned names
  beyond capitalization.

### Verification

- All 29 repository tests pass after Step 5.
- Tests cover NSW layout cleanup, country suffixes, punctuation/case handling,
  stable IDs, cross-source linking, raw-name preservation, review routing,
  idempotency and protection of reviewed aliases.

### Model boundary

The frozen V1 benchmark remains name-keyed and is not retrospectively changed.
Steps 6 onward must join through `runner_horse_links` and use `horse_id`. This is
expected to recover substantial cross-source history that V1 treated as unrated,
while keeping the comparison against V1 honest.

## Step 6 — class-prior research

### Status

Completed as descriptive research on 21 August 2026. No class number has yet
been added to Horse Ability or used to change the accepted V1 benchmark.

### Brief explanation

A race label such as BM78 or Group 2 is useful, but the label alone does not
prove how strong that particular field was. This step measured the typical
pre-race strength of each class using the runners' official handicap ratings.
Large groups mostly keep their observed value. Small groups are pulled toward a
broader parent average so one unusual race cannot create a false class rating.

### Architecture and changes

- Added `racing_engine/class_prior_research.py`.
- Added `tests/test_class_prior_research.py`.
- Added the versioned `class_prior_research` table.
- Produced `data/outputs/class_prior_research_v1_2026-08-16.json`.
- Built the hierarchy:

```text
all races
  -> state
    -> class family
      -> venue and class family
        -> Group grade / benchmark number / class number
```

- Used race median official handicap rating as the primary field-strength
  evidence and retained the average top-four rating as a diagnostic.
- Estimated an empirical prior strength at each level, bounded between five and
  100 equivalent races. Every row stores its raw value, parent, shrinkage
  weight, shrunk value, coverage and uncertainty.
- All calculations use races strictly before the requested `as_of_date`.

### Results

- 2,364/2,471 races had at least three runners with official ratings and entered
  the research; 107 were excluded explicitly.
- Overall runner official-rating coverage was 94.21%; within eligible races it
  was approximately 97.8%.
- Global median-field prior: 78.95 official-rating points.
- NSW Group races averaged 91.32 before shrinkage; Victorian Group races 88.51.
- NSW Listed races averaged 85.39; Victorian Listed races 81.48.
- NSW benchmark races averaged 73.95; Victorian benchmark races 76.63.
- Group 1 subtypes were strongest as expected, around 97–102 before shrinkage.
- Thirty of 91 fine subtype groups contained fewer than five races and therefore
  rely materially on their parent priors.

### Problems encountered and how they were handled

1. **Missing official ratings:** 107 races, especially older NSW Group,
   handicap and Listed races, lacked three usable runner ratings. They were
   excluded with a named reason rather than filled with invented values.
2. **No usable maiden evidence:** the two NSW maiden races had insufficient
   official ratings. A future maiden must therefore fall back to a broad,
   uncertain parent until equivalent evidence exists.
3. **Unclassified races:** 76 eligible races remain `unclassified`. Many contain
   set-weight or weight-for-age condition text rather than a reliable grade.
   They remain a separate research group instead of being forced into Listed or
   Open classes.
4. **Sparse venues/subtypes:** small groups produced extreme raw averages.
   Hierarchical shrinkage pulls them toward their class/venue parent and records
   the low weight and uncertainty.
5. **Only two states:** the empirical state-level shrinkage estimate is weak and
   reached the conservative 100-race upper bound. Finer levels reached the
   five-race lower bound. These bound hits are exposed in diagnostics and must
   receive sensitivity testing before Step 8 integration.
6. **Restricted population:** the database contains NSW and Victorian Saturday
   metropolitan racing only. The priors cannot be presented as valid for
   provincial, country, Queensland or other jurisdictions.
7. **Evidence is not ground truth:** official handicap ratings are useful
   pre-race evidence but partly reflect the existing handicapping system. Step 7
   will combine them with strictly prior internal Horse Ability and coverage;
   Step 8 will keep actual post-race evidence separate.

### Verification

- All 33 repository tests pass.
- Tests prove sparse-child shrinkage, explicit missing-data exclusions,
  idempotent/versioned storage and the as-of cutoff.
- Adding an extreme future Group race does not change an earlier class-prior
  report.

### Decision

The hierarchy is plausible enough to carry into Step 7 research, but its values
are not promoted into ratings. Step 7 must calculate the actual pre-race field
strength from prior internal horse states, including median, top end, depth,
rated-runner coverage and uncertainty. Step 8 then tests how much the class
prior should contribute relative to the real field assembled for that race.

## Step 7 — pre-race field strength

### Status

Completed on 21 August 2026 as `pre-race-field-v1.0`. The estimates are frozen
historical evidence for Step 8; they have not changed the accepted V1 model.

### Brief explanation

For every historical race, the pipeline stops immediately before that race and
asks how strong the entered horses appeared at that moment. It cannot use the
result being predicted or anything that happened later. It records the expected
field median, strongest four, top rating, proven depth, known-horse coverage and
uncertainty. An unrated horse stays in the field at the frozen neutral prior of
100 with high uncertainty.

### Architecture and changes

- Added `racing_engine/field_strength.py`.
- Added `tests/test_field_strength.py`.
- Added `pre_race_runner_states` and `pre_race_field_strengths` tables.
- Produced `data/outputs/pre_race_field_strength_v1_2026-08-15.json`.
- Replayed all 153 race days chronologically.
- Rebuilt V1 performance evidence at each exact date cutoff and aggregated it
  through the durable Step 5 `horse_id`, not the old raw name key.
- Stored one prior runner record for every actual starter and one immutable
  summary for every field.

### Frozen field measures

- **Field median:** median expected rating across all starters, including the
  declared neutral prior for unknown horses.
- **Rated-only median:** median among horses with genuine prior performance.
- **Top four:** average of the four highest expected ratings.
- **Top rating:** highest expected rating in the field.
- **Depth:** number of genuinely rated horses within five points of the highest
  genuinely rated horse. Unknown neutral horses do not count as proven depth.
- **Coverage:** proportion of starters with a prior internal state.
- **Uncertainty:** root-mean-square runner uncertainty, retaining the penalty
  from unknown or lightly raced horses.

### Results

- All 2,471 races and 26,392 actual starters were stored; no race had fewer than
  two starters under the frozen status rules.
- Mean rated-runner coverage was 53.33%.
- Coverage rose as history accumulated: 13.9% in 2023, 45.4% in 2024, 66.6% in
  2025 and 67.2% in 2026.
- 289 fields had no internally rated runner; 232 fields were fully rated.
- Mean field uncertainty declined from 11.64 in 2023 to 9.51 in 2026.
- The expected median remains close to neutral (99.98 in 2023 and 99.14 in
  2026), while the mean top-four figure rose from 100.04 to 100.67.
- Average proven depth increased from 1.5 rated horses in 2023 to 5.2 in 2026.

### Problems encountered and how they were handled

1. **Cold-start coverage:** the first season has little prior history. Unknown
   horses remain neutral with high uncertainty; they are not excluded or
   treated as weak.
2. **V1 evidence remains sparse:** 12,241 of 26,392 runner observations had zero
   prior usable runs. Durable identity recovers cross-source histories, but it
   cannot manufacture missing clocks or performance evidence.
3. **Source imbalance:** average coverage was 64.5% for Victorian-authorised
   results, 46.1% for Racing NSW, and 36.3% for NSW result fallbacks. Coverage
   and uncertainty remain part of every estimate so this imbalance is visible.
4. **Compressed ratings:** V1 shrinkage holds most horses close to 100, so actual
   field differences are presently modest. Step 8 must not give this weak field
   signal unjustified precision; the stronger class evidence and field evidence
   must retain separate weights and uncertainty.
5. **Depth inflation discovered:** the first implementation counted unknown
   neutral horses as depth. This was corrected so only genuinely rated horses
   within five points of the best rated runner count as proven depth.
6. **Historical starter knowledge:** fields use the recorded actual starters,
   excluding scratchings and non-starters. This represents the field at jump
   time; a later live pipeline must freeze a new estimate after each scratching.

### Verification

- All 35 repository tests pass.
- Tests cover exact summary arithmetic, neutral unrated treatment, uncertainty,
  cross-source identity history, idempotent storage and future-data poisoning.
- An NSW dirty name and Victorian country-suffixed spelling share the correct
  prior state.
- Adding an extreme future race leaves the earlier runner and field estimates
  unchanged.

### Decision

Step 7 provides the required strictly pre-race field evidence, but its 53.33%
average coverage and compressed V1 scale require conservative use. Step 8 will
build Race Strength with separate components for hierarchical class prior,
actual field median, top end, depth, coverage and uncertainty. Post-race time or
margin evidence will remain separate and cannot rewrite the frozen pre-race
estimate.

## Step 8 — Race Strength Rating

### Status

Completed as a research candidate on 21 August 2026 as `race-strength-v1.0`.
It is not integrated into Horse Ability until the controlled Step 9 variants and
Step 10 promotion test are complete.

### Brief explanation

Race Strength now answers two separate pre-race questions: how strong this class
normally is, and how strong the horses entered actually appeared before the
race. The system stores class-only, field-only and combined answers. When the
horses are poorly known, class receives most of the weight. When the field has
strong prior coverage and lower uncertainty, the actual horses receive more
influence.

### Architecture and changes

- Added `racing_engine/race_strength.py`.
- Added `tests/test_race_strength.py`.
- Added `race_strength_ratings` and `post_race_strength_evidence` tables.
- Produced `data/outputs/race_strength_v1_2026-08-15.json`.
- Rebuilt the Step 6 class hierarchy separately at every race-date cutoff using
  only earlier races.
- Selected the most specific available prior in this order: subtype, venue and
  class, state and class family, state, then global.
- Stored complete formula inputs, sample size, uncertainty, coverage, fallback
  level and information cutoff for every race.

### V1 component formula

The official handicap-rating scale and internal Horse Ability scale have
different centres. The provisional class mapping preserves only the relative
class difference:

```text
class-only = 100 + shrunk class prior - as-of global class prior
field-only = 60% field median + 40% top-four average
field reliability = rated coverage × max(0, 1 - uncertainty / 20)
combined = reliability-weighted average of class-only and field-only
```

This is deliberately transparent and provisional. Step 9 must test class-only,
field-only and combined formulations separately; the one-for-one mapping of an
official rating point to an internal point is not yet validated.

### Results

- 2,471/2,471 races received a Race Strength record and a separate post-race
  evidence record.
- 2,345 races used the most specific subtype prior; 38 fell back to venue/class,
  57 to class family, 13 to state, ten to global, and the first eight races had
  no earlier class evidence.
- Mean combined Race Strength was 99.28.
- Mean class reliability was 0.746; mean field reliability was only 0.286 due to
  coverage and uncertainty.
- Average absolute disagreement between class-only and field-only components
  was 6.65 points, providing a useful future diagnostic.
- Mean combined strength by broad class:
  - Group: 106.73
  - Unclassified: 101.63
  - Listed: 101.21
  - Maiden: 99.46, based on fallback evidence only
  - Open/quality: 98.17
  - Handicap unspecified: 96.87
  - Benchmark: 96.28
  - Numbered class: 88.47

### Problems encountered and how they were handled

1. **Different rating scales:** Step 6 uses official handicap ratings centred
   near 79, while internal Horse Ability is centred at 100. The candidate maps
   only the difference from the as-of global class prior. The mapping is stored
   explicitly and must be tested rather than assumed correct.
2. **Weak field evidence:** average field reliability is 0.286. Coverage and
   uncertainty automatically reduce its blend weight; the raw field-only value
   remains visible for inspection.
3. **Early-history class cold start:** eight first-day races had no earlier class
   evidence. They fall back to field evidence or neutral rather than learning
   from their own result.
4. **Mixed `open_or_quality` category:** this label includes heterogeneous race
   conditions and averaged below Listed/Group. It remains separate and is not
   manually promoted because its name sounds strong.
5. **Unclassified races can be strong:** their combined average was 101.63.
   They remain visibly unclassified rather than being assigned a guessed grade.
6. **Large class/field disagreement:** the 6.65-point average gap may represent
   genuine unusually strong or weak fields, but it can also reflect compressed
   V1 horse states. Step 9 must test both components independently.
7. **Post-race leakage risk:** official clocks, winner clocks, margins and runner
   times are stored in `post_race_strength_evidence`. Tests prove changing them
   after the race does not change the pre-race Race Strength record.

### Verification

- All 38 repository tests pass.
- Tests cover formula arithmetic, reliability behaviour, neutral fallback,
  chronological class evidence, idempotency and strict separation of post-race
  evidence.
- Changing the target race's completed times and margins updates only its
  evidence record; its pre-race combined rating remains identical.
- Stored Race Strength and post-race evidence counts both reconcile to all 2,471
  historical races.

### Decision

Step 8 has produced an auditable Race Strength candidate with all components
separate. It has not proved predictive improvement. Step 9 will create new
Horse Ability/prediction variants for class-only, field-only and combined Race
Strength, without adding weight, weather, track bias, stewards or map inputs.

## Step 9 — Race Strength integration variants

### Status

Completed on 21 August 2026. Three experimental Horse Ability versions and one
identity-only control now exist, but none is accepted or promoted until Step 10
evaluation.

### Brief explanation

Each historical run keeps its original V1 time, margin and sectional assessment.
The experiment adds one of three frozen Race Strength adjustments: class-only,
field-only, or combined. The adjusted runs are then aggregated into current
Horse Ability using durable horse IDs. A fourth identity-only control uses the
same durable IDs but adds no Race Strength. This lets the backtest identify
whether any improvement comes from repaired horse histories, class, actual
field strength, or their blend.

### Changes and outputs

- Added `racing_engine/race_strength_models.py`.
- Added `tests/test_race_strength_models.py`.
- Produced `data/outputs/race_strength_model_variants_2026-08-16.json`.
- Created these model versions:
  - `performance-par-v1.0+identity-v1.0`
  - `performance-par-v1.0+race-class-v1.0`
  - `performance-par-v1.0+race-field-v1.0`
  - `performance-par-v1.0+race-strength-v1.0`
- Reused the existing versioned `run_performances` and `horse_rating_states`
  tables rather than creating an opaque parallel store.

### Frozen candidate formula

```text
adjusted run performance = V1 run performance + (selected Race Strength - 100)
```

The coefficient is exactly 1.0 for this registered first experiment. Missing
class-only strength produces a zero adjustment. Time, margin, sectional,
confidence and every original component remain unchanged and auditable.

### Results as of 16 August 2026

- Each variant contains 18,140 adjusted run performances and 7,048 durable
  horse states.
- Identity-only: zero Race Strength adjustments and a mean final state rating
  of 97.90. It provides the clean control for the Step 5 identity repair.
- The old name-keyed V1 contains 10,752 apparent horse states; the reduction is
  expected because Step 5 reunites source spellings and removes NSW layout
  debris.
- Class-only: 17,927 non-zero adjustments; 57 runs lacked class strength and
  remained unchanged. Mean absolute adjustment was 6.54 points, ranging from
  -16.56 to +21.87.
- Field-only: 13,337 non-zero adjustments. Mean absolute adjustment was only
  0.48 points, ranging from -3.80 to +21.73.
- Combined: 17,927 non-zero adjustments. Mean absolute adjustment was 4.86
  points, ranging from -14.49 to +21.86.
- Mean final state ratings were 97.80 class-only, 97.85 field-only and 97.69
  combined.

### Problems encountered and how they were handled

1. **Identity changes the baseline population:** durable IDs merge histories
   that V1 incorrectly split, so the Race Strength variants differ from V1
   through two changes. This was addressed by building the identity-only model
   in Step 9; Step 10 can now measure identity repair separately.
2. **Existing V1 performance outliers:** the base run ratings already range from
   approximately -186.65 to +376.12. The variants retain these values rather
   than silently clipping them during a Race Strength experiment.
3. **Merged histories reveal inconsistency:** some reunited horses have very
   large state uncertainty because their historical run assessments disagree.
   This is exposed rather than hidden. Step 10 must inspect probability tails
   and log-loss failures; later work may require a separately registered robust
   performance-state candidate.
4. **Scale coefficient is unvalidated:** one Race Strength point currently adds
   one performance point. This transparent coefficient is a test candidate, not
   a permanent truth. Step 10 may reject it or motivate a revised registered
   coefficient.
5. **Circular feedback risk:** Step 8 Race Strength remains frozen from the V1
   pre-race states. Candidate-adjusted states do not recursively rewrite the
   field strengths used to create themselves.
6. **Missing early class evidence:** 57 usable run performances came from races
   without class-only strength and receive zero class adjustment.
7. **Scope isolation:** weight, WFA, weather, daily variant, trip, stewards and
   map inputs are explicitly absent so any Step 10 difference is attributable
   to identity and Race Strength only.

### Verification

- All 40 repository tests pass.
- Tests prove neutral/missing adjustment behaviour, exact component isolation,
  durable-ID aggregation, correct multi-run histories and idempotent rebuilding.
- The class-only test adds exactly ten points for a 110 Race Strength while
  leaving time and margin components unchanged.

### Decision

Step 9 successfully created the registered variants. It did not establish that
any variant is better. Step 10 must compare, on identical races and runners:

1. frozen V1;
2. identity-only V1 control;
3. class-only;
4. field-only; and
5. combined Race Strength.

The identity-only control is required because Step 5 corrected enough histories
to materially change the number of horse states. Promotion requires the frozen
log-loss, Brier, calibration, ranking, coverage, segment and uncertainty report.

## Step 10 — Race Strength promotion evaluation

### Status and decision

Completed on 21 August 2026 under the unchanged `evaluation-v1` protocol hash
`30714852ca6da02dca3cc7dd3da0d5af4064c0832af9b6f675933e14c410c693`.
The decision is **REVISE** for every candidate. No Step 9 model is promoted;
the frozen V1 remains the accepted benchmark.

### Brief explanation

The system rebuilt each horse's rating immediately before every test race, then
priced the exact same runners with V1, identity-only, class-only, field-only and
combined Race Strength. Lower log loss is better. A candidate had to improve on
validation, have a 95% paired interval wholly below zero, and improve in the
same direction on the untouched historical holdout. None met all three rules.

### Architecture and outputs

- Added `racing_engine/promotion_evaluation.py`.
- Added `tests/test_promotion_evaluation.py`.
- Produced `data/outputs/race_strength_promotion_step10_2026-08-16.json` and
  its Markdown decision report.
- Stored every runner probability in the versioned `benchmark_predictions`
  ledger and stored the complete report in `benchmark_reports`.
- Used a race-date-exclusive state cutoff and prohibited same-day results.
- Used one common eligibility decision and runner set for all five models.
- Applied the frozen 10,000-repetition, meeting-day block bootstrap with seed
  `20260821`.
- Reported log loss, race/runner Brier, winner rank, top-one/two/three,
  calibration, coverage, history depth, uncertainty, period, state, source,
  track, distance, going, field size and class-family segments.

### Common test population

- 1,582 eligible races and 16,937 runners across validation and historical
  holdout.
- 21 races were excluded identically for all models: 14 missing a unique winner
  and seven containing multiple winners under the frozen dead-heat policy.
- Validation contained 789 races; historical holdout contained 793.
- Frozen V1 overall log loss was 2.326815, matching the Step 3 benchmark.

### Primary results

Candidate-minus-V1 log-loss differences are shown below; negative is better.

| Candidate | Validation | Historical holdout | Validation 95% interval | Decision |
| --- | ---: | ---: | ---: | --- |
| Identity-only | +0.001253 | +0.002440 | [-0.005144, +0.007840] | REVISE |
| Class-only | -0.004049 | +0.004380 | [-0.013911, +0.005652] | REVISE |
| Field-only | +0.001190 | +0.002475 | [-0.005228, +0.007587] | REVISE |
| Combined | -0.002119 | +0.001568 | [-0.010606, +0.006572] | REVISE |

Class-only and combined looked slightly better on validation, but became worse
on holdout. Their uncertainty intervals also include no change. Field-only and
identity-only were slightly worse in both periods. These are small, uncertain
differences, not evidence of an improved probability model.

### Secondary findings

- Durable identity reduced unrated runner predictions from 10,554 to 5,884.
  This is a real coverage improvement, but greater history coverage alone did
  not improve log loss.
- Combined improved holdout top-one strike rate from 14.25% to 16.52% and mean
  winner rank from 5.16 to 5.09, but its holdout log loss and Brier score were
  worse. Better ordering did not translate into better calibrated prices.
- The candidate models created 11–13 runners priced above 50%, with only about
  15–18% winning. V1 produced only two runners in that band, both collectively
  calibrated at 50%. The candidate tail is small but clearly overconfident and
  helps explain the log-loss failure.
- Class-family results are mixed. For example, class and Listed performance
  improved in some candidates, while Open/Quality and other groups weakened.
  No broad segment pattern overrides the failed primary promotion rules.

### Problems encountered and how they were addressed

1. **Identity was a confounder:** the identity-only model isolated Step 5 from
   Race Strength. It showed that recovered histories improve coverage but not
   current forecast quality without better state aggregation.
2. **Validation improvement did not repeat:** class-only and combined reversed
   on holdout. The frozen holdout rule prevented selecting the attractive first
   result.
3. **Small changes could be noise:** meeting-day block resampling retained
   correlated races at the same meeting. Every interval crossed zero, so no
   small point estimate was treated as proof.
4. **Probability tails became too strong:** durable merged histories and the
   one-for-one Race Strength coefficient generated overconfident favourites.
   The report exposes those bins; Step 10 does not clip or recalibrate them
   after seeing holdout results.
5. **Ranking and pricing disagreed:** some top-one results improved while proper
   probability scores worsened. The primary metric remained log loss as frozen,
   preventing a post-hoc switch to the more flattering measure.
6. **Market prices remain unavailable:** this evaluates forecasting quality
   against V1, not profitability or opening/closing market efficiency. Market
   comparison still requires complete timestamped price history in the final
   stages.

### Verification

- All 42 repository tests pass.
- Tests cover deterministic meeting-block intervals, common race/runner sets,
  durable identity history and exclusive information cutoffs.
- The full result reproduces the Step 3 V1 metrics on the same 1,582 races.
- Rebuilding prediction rows is idempotent through versioned database keys.

### Boundary for Step 11

Race Strength remains useful descriptive evidence, particularly for comparing
nominal classes across jurisdictions, but its current one-for-one integration
is not accepted as Horse Ability. Step 11 must test daily track variant and
weight/WFA as separately registered candidates against frozen V1. It must not
quietly carry the failed Step 9 Race Strength adjustment into those tests.

### External research comparison recorded 21 August 2026

Research checked after the decision supports the interpretation that Step 10
rejected the current integration formula, not the concept of class or field
strength:

- Edelman's published Australian metropolitan-racing work describes an
  empirical competitive-strength/class measure that added value out of sample.
  This supports retaining Race Strength as a research feature, while our own
  result shows that the present one-point-for-one-point transfer is unsuitable.
- Benter's computer-handicapping report treats racing probability as a
  multivariable problem and combines a fundamental model with public implied
  probabilities. This is consistent with testing class alongside weight,
  distance, condition and other context rather than treating class as a
  standalone answer.
- Proper-scoring research confirms that log loss rewards honest probability
  forecasts and strongly penalizes unjustified confidence. This supports the
  frozen decision not to promote a model merely because its top-rated strike
  rate improved.
- Large-scale equine research reports that race and final-600 speed vary with
  distance and track condition while accounting for horse rating and carried
  weight. This supports Steps 11–12 being separate contextual tests.
- Betting-market research repeatedly finds that public prices aggregate large
  amounts of information and can show favourite/longshot distortions. This
  reinforces the plan to compare with normalized opening and closing market
  probabilities once timestamped price coverage is adequate.

Sources consulted:

- https://www.taylorfrancis.com/chapters/edit/10.4324/9780203986936-16/competitive-horse-race-handicapping-algorithm-based-analysis-covariance-david-edelman
- https://gwern.net/doc/statistics/decision/1994-benter.pdf
- https://www.stat.berkeley.edu/~ryantibs/statlearn-s23/lectures/calibration.pdf
- https://pubmed.ncbi.nlm.nih.gov/42193723/
- https://academic.oup.com/ej/article/107/440/150/5144344

## Step 11 — daily variant and carried weight/WFA

### Status and decision

Completed on 21 August 2026 under the same frozen `evaluation-v1` protocol.
Daily variant, carried weight and their interaction are all **REVISE**. None is
promoted, so accepted V1 remains unchanged. True WFA is correctly gated because
historical runner age and sex are absent.

### What was built

- Added `racing_engine/step11_models.py` and `tests/test_step11_models.py`.
- Added the versioned `daily_track_variants` table.
- Registered three isolated models:
  - `performance-par-v1.0+daily-variant-v1.0`
  - `performance-par-v1.0+carried-weight-v1.0`
  - `performance-par-v1.0+daily-variant-v1.0+carried-weight-v1.0`
- Produced `data/outputs/daily_variant_weight_promotion_step11_2026-08-16.json`
  and its Markdown report.
- Daily variant uses the median completed-race residual for each meeting, needs
  at least three races, and shrinks toward zero with `n/(n+6)`.
- Carried weight adds one provisional performance point per kilogram above the
  race median. This is relative carried weight, not WFA.
- The interaction adds the two independently registered components.

### Data audit

- Carried weight exists for 29,456 of 29,845 runner results.
- The database has 2,072 races with official times across 153 race days.
- Runner age coverage: zero. Runner sex coverage: zero.
- Racing Australia AR 168–170 and Racing NSW publish age, sex, month and
  distance-dependent scales. Implementing those tables without runner age/sex
  would create false WFA values, so the WFA component remains null and named as
  unavailable.
- At the final historical cutoff, 213 meeting variants were usable, one had
  insufficient races, and three beyond eight lengths were flagged for review.
  Usable variants averaged -0.06 lengths and ranged from -12.49 to +4.99 when
  review flags are included.

### Promotion results

Candidate-minus-V1 log loss is below; negative would be better.

| Candidate | Validation | Historical holdout | Validation 95% interval | Decision |
| --- | ---: | ---: | ---: | --- |
| Daily variant | +0.000102 | +0.000471 | [-0.000937, +0.001211] | REVISE |
| Carried weight | +0.000257 | +0.000495 | [-0.001315, +0.001792] | REVISE |
| Daily + weight | +0.000379 | +0.000971 | [-0.001779, +0.002476] | REVISE |

All candidates were marginally worse in both periods, and every interval
included no difference. There is no evidence for promotion at the registered
coefficients.

### Problem found and fixed during evaluation

The first Step 11 evaluation incorrectly asked for durable horse IDs even though
these isolation candidates deliberately retained V1 raw-name keys. That made
all candidate runners appear unrated and produced equal probabilities. The
invalid report was overwritten, the evaluator now requires an explicit `raw`
or `durable` key mode for every candidate, and a regression test prevents the
error recurring. Only the corrected results above are authoritative.

### Verification

- Corrected evaluation covers the same 1,582 races and 16,937 runners as V1.
- It uses 10,000 meeting-day bootstrap repetitions and race-date-exclusive
  horse states.
- Candidate unrated coverage matches V1 at 10,554 runners.
- All 48 repository tests pass after Step 11 and follow-on work.

## Ten post-Step-10 follow-on actions — build overview

Completed or scaffolded on 21 August 2026. “Built” below does not mean
“promoted.” Once the historical holdout was inspected in Step 10, it could no
longer be reused to tune these ideas and still be described as untouched.
Promotion now requires results dated 16 August 2026 onward.

### 1. Continue Step 11

Complete. Daily variant and relative carried weight were built and tested
separately and together. All received REVISE. WFA awaits runner age and sex.

### 2. Rebuild Horse Ability aggregation

Added a research-only robust durable-identity state model:
`performance-par-v1.0+robust-identity-state-research-v1.0`. It caps each
horse's historical run evidence to 20 points either side of that horse's median
before recency/confidence aggregation. This prevents one extreme run from
dominating while preserving the raw evidence. It produced 7,048 shadow states
and awaits prospective evaluation.

### 3. Reduce Race Strength influence

Built separate 10%, 25% and 50% combined Race Strength shadow models. Each has
18,140 performances and 7,048 durable states. They are explicitly research-only:
selecting a coefficient using the already viewed holdout would be test leakage.

### 4. Use Race Strength as confidence

Built a confidence-only shadow model. It does not add Race Strength points.
Instead, unreliable Race Strength evidence reduces the historical run's weight
in the horse-state calculation. It has 18,140 runs and 7,048 states and awaits
prospective testing.

### 5. Make Race Strength conditional

Built a small reliability-gated conditional model. Group/Listed races can use
up to 25%, benchmark races up to 10%, and other classes up to 5%; each maximum
is multiplied by observed Race Strength reliability. This is a registered
research hypothesis, not an accepted coefficient.

### 6. Future-form confirmation

Completed a descriptive next-start check across 11,092 paired runs. Correlation
between current Race Strength and change at the next performance was only
`0.0419`; mean next-run change was -0.43 points. That is very weak confirmation
and supports keeping Race Strength descriptive until a better controlled target
and prospective evidence show value.

### 7. Probability calibration

Added `racing_engine/probability_calibration.py` with coherent whole-field
temperature scaling and a training-only grid fit. It refuses to fit when no
designated training prediction ledger exists. There are currently zero stored
train-period predictions, so status is `AWAITING_DESIGNATED_TRAIN_PREDICTIONS`.
It has not been fitted on validation or holdout after seeing those results.

### 8. Expand historical data

Added `racing_engine/expansion_readiness.py`. Current coverage is exactly 2,471
Saturday races: 1,325 NSW and 1,146 Victoria. Queensland, South Australia,
Western Australia, Tasmania, ACT and Northern Territory are missing, as is a
canonical meeting-grade field. National/provincial class priors therefore remain
not ready. The gate requires authorised results, source provenance, durable
identity, meeting grade, times, weight and runner age/sex before activation.

### 9. Start collecting market prices

Added append-only `market_snapshots` storage and
`racing_engine/market_prices.py`. The importer validates decimal odds, preserves
every timestamp instead of overwriting, is idempotent, and normalizes complete
books to remove overround. Current observations: zero. Market comparison remains
`AWAITING_TIMESTAMPED_MARKET_DATA`; missing historical prices were not invented.

### 10. Keep Race Strength descriptive

Added a permanent descriptive output by class family and state. Current mean
combined strengths remain: Group 106.73, Listed 101.21, Benchmark 96.28 and
Class 88.47; NSW averages 98.75 and Victoria 99.89 across this restricted
Saturday metropolitan population. The output explicitly says it is comparative
research, not an accepted Horse Ability adjustment.

### Files and consolidated status

- Added `racing_engine/race_strength_followons.py` and tests.
- Added `racing_engine/market_prices.py`,
  `racing_engine/probability_calibration.py`,
  `racing_engine/expansion_readiness.py` and infrastructure tests.
- Added `racing_engine/followon_status.py`.
- Added append-only `market_snapshots` and versioned `model_calibrations` tables.
- Produced `data/outputs/race_strength_followons_2026-08-16.json`.
- Produced `data/outputs/followon_status_2026-08-21.json`.

### Current hard boundaries

1. The latest result is 15 August 2026. There are zero races in the prospective
   period beginning 16 August 2026, so no new shadow candidate can be promoted.
2. There are zero timestamped market observations, so opening, decision-time,
   closing, CLV and profitability comparisons cannot yet run.
3. Runner age and sex are absent, so official WFA normalization cannot run.
4. Only NSW/Victorian Saturday metropolitan history is present, so national,
   weekday, provincial and country ratings cannot yet be claimed.

### Accepted-system position after all work

The accepted model remains `performance-par-v1.0`. Race Strength, daily variant,
relative weight, robust state, reduced/conditional strength and calibration all
remain versioned shadow research. The architecture can now ingest the missing
evidence and learn from genuinely new results without rewriting historical
decisions or pretending that unobserved data exists.

## Winning-margin research and correction

### Status

Researched and implemented as a prospective shadow candidate on 21 August
2026. The candidate is promising retrospectively but is **not promoted** because
it was designed after the historical holdout had already been inspected.

### Correction to the earlier explanation

V1 does preserve the relative five-length superiority of a winner over a horse
beaten five lengths: the beaten horse's run is placed five internal points below
the winner when margin rather than an individual clock supplies the difference.
It was therefore too broad to say the winner received no benefit at all.

The actual omission is absolute anchoring. V1 primarily sets the winner's level
from winning time versus a long-run par. Given the same winning time, its winner
can receive the same absolute figure whether it wins by a nose or five lengths;
only the beaten horses move. Mature form handicapping instead anchors the whole
race to reliable previous form/standards, then places the winner above that
anchor by the observed or reasonably achievable margins.

### External findings

- The British Horseracing Authority starts from previous form, establishes the
  race level with a suitable pounds-per-length calculation, and explicitly
  shows a one-length winner being rated above a known runner-up. It also allows
  for additional superiority when an easy winner could have won farther.
- BHA pounds per length changes materially with distance and also depends on
  ground, pace and course. It gives approximately 3.41 lb/length over five
  furlongs on good-to-firm ground versus 1.22 over one mile six furlongs.
- Timeform likewise varies margin poundage with distance, time and surface and
  combines margins with carried weight and age.
- IFHA guidance uses approximately 3 lb/length at 1000m, 2 at 1600m and 1 at
  2800m+, modified for going and pace. It warns that beaten-horse margins may
  deserve a different allowance from the winning margin.
- BHA also warns that slow pace bunches finishes and excessive pace exaggerates
  gaps. Time and sectionals must therefore affect confidence in literal margins.

Sources:

- https://www.britishhorseracing.com/regulation/performance-figures/
- https://www.britishhorseracing.com/regulation/handicapping-tools/
- https://www.timeform.com/horse-racing/features/awards/how_timeform_handicaps_horses
- https://www.ifhaonline.org/resources/terms_LWBRREC.pdf

### Candidate architecture

Added `racing_engine/winning_margin.py` and `tests/test_winning_margin.py` with
model version `performance-par-v1.0+form-anchored-margin-research-v1.0`.

For each completed historical race it:

1. reads only frozen pre-race horse states as the form yardsticks;
2. uses official beaten margins, or derives the gap from runner/winner clocks
   when the official margin is absent;
3. uses a distance-dependent relative margin multiplier inspired by the IFHA
   shape, normalized to one internal point per length at 1600m;
4. calculates the winner level implied by each known horse's prior rating plus
   its margin behind the winner;
5. takes a robust median race anchor and reduces its reliability when coverage
   is poor or the implied anchors disagree;
6. blends that anchored form figure with V1 rather than adding a flat bonus;
7. caps margin evidence at 12 lengths; and
8. records that weight/WFA and pace refinement are still unavailable rather
   than silently assuming them.

This means a dominant winner can rise, a weak winner can fall, and the whole
field remains internally related. It avoids automatically awarding five points
merely because the official margin says five lengths.

### Final-snapshot output

- 18,140 historical performances and 7,048 durable horse states.
- 1,458 of 1,711 rated historical races had enough prior form to establish an
  anchor.
- 881 winners were raised and 580 were lowered relative to their V1 time-based
  level.
- Mean absolute run adjustment was 1.55 points.
- Output: `data/outputs/winning_margin_research_2026-08-16.json`.

### Retrospective diagnostic

Against raw-name V1, candidate log loss improved by 0.000651 on validation and
0.002831 on historical holdout. Overall top-one strike rate increased from
14.73% to 15.61%, top-three from 38.94% to 40.39%, and mean winner rank improved
from 5.16 to 5.11. Overall runner Brier was marginally worse.

Because durable identity is part of this model, the cleaner isolation is against
the identity-only control:

- validation log-loss difference: -0.001904, 95% meeting-block interval
  [-0.004187, +0.000324];
- historical-holdout difference: -0.005270, interval
  [-0.010222, -0.000678].

The holdout direction is encouraging and its interval excludes zero, but the
validation interval narrowly includes zero. More importantly, this formula was
created after those results had ceased to be untouched. The report is therefore
explicitly `promotion_eligible=false`; new races from 16 August 2026 onward are
required for an honest decision.

Output:
`data/outputs/winning_margin_retrospective_diagnostic_2026-08-16.json`.

### Remaining margin work

- Source runner age and sex, then add official Australian WFA.
- Distinguish cumulative official margin from distance to the preceding horse
  at ingestion for every provider.
- Learn Australian distance/going margin scales using training data rather than
  permanently borrowing an international curve.
- Add pace/sectional reliability so an overly strong pace reduces exaggerated
  gaps and a crawl gives suitable weight to a decisive sprint finish.
- Prospectively score the frozen candidate before any coefficient revision.

## Full architecture and market-readiness audit

### Audit conclusion — 21 August 2026

The project is **not yet at the finished prospective-pricing stage** described
by `ratings_build_plan.md`, `project_tracker.md` and
`three_season_rating_assignment.md`. Steps 1–10 built the evaluation and Race
Strength foundation. Step 11 tested partial daily-variant and carried-weight
ideas. Step 12—the large contextual build—has mostly not been implemented.

The correct description is:

- ready for controlled historical research and candidate backtests;
- not ready to claim a complete Horse Ability model;
- not ready for production prices or wagering decisions;
- not yet ready for the main ML challenger; and
- able to continue storing immutable raw results, provided official prospective
  predictions are not claimed unless they were frozen before those results.

### Layer-by-layer reality check

| Layer | Evidence/data | Numerical model status | Decision |
| --- | --- | --- | --- |
| Long-run track/distance/going par | Built | Accepted in V1 | Keep |
| Winning margin | Stored but provider semantics need audit | Promising form-anchored shadow | Prospective test required |
| Horse identity | Built, all historical runners linked | Durable-ID shadows built | Accepted infrastructure |
| Class hierarchy/Race Strength | Built descriptively | Full integration failed Step 10 | Research only |
| Daily track variant | Built for research | Registered version slightly worsened V1 | Revise |
| Carried weight | 29,456/29,845 runners | Relative-weight candidate worsened V1 | Revise |
| WFA | Official scale identified | Blocked: zero runner age/sex | Must source profiles |
| Canonical sectionals | 26,392 runs; final-400 on 20,964 | Only a small old last-400 clue enters V1 | Full pace profiles not built |
| Pace shape | Positions widely available | No early/middle/late pace model | Not built |
| DT-W/trip | Only 643 runner DT-W values | No trip correction | Not ready |
| Rail/lane/meeting pattern | Rail text and sectional positions exist | No bias estimate | Not built |
| Weather/wind | 2,471 matched rows; wind complete | No rating adjustment | Not built |
| Steward reports | 1,079 reports, 6,714 events, 556 reviews | No ablation or accepted adjustment | Evidence only |
| Barrier | 25,460/29,845 results | No geometry/map interaction | Not built |
| Jockey/trainer | Stored on historical rows | No validated feature | Not built |
| Campaign stage | Historical dates exist; prior research/spec exists | No first/second-up state model | Not built |
| Current fitness/intent | Some steward evidence only | No timestamped condition model | Not built |
| Today's cards | 29 cards and 385 card runners | Inadequate historical card coverage | Not ready |
| Speed map/scenarios | No complete pre-race style feature table | No probabilistic map | Not built |
| Probability calibration | Temperature code built | No designated training ledger; not fitted | Blocked |
| Market comparison | Append-only schema/importer built | Zero observations | Blocked |
| Automatic learning loop | Architecture described | No complete predict-freeze-result-score-promote scheduler | Not built |
| ML challenger | No point-in-time training matrix | No RacingEngine ML model | Premature |

### Important meaning of “16 August forward”

Do not suppress or postpone raw result ingestion. Authorised results, cards,
sectionals, profiles and market snapshots should be stored as immutable evidence
when available. The boundary applies to evaluation:

1. a candidate and its formula must be frozen;
2. its prediction must be persisted before the race;
3. only then may the result be attached and scored; and
4. the result cannot be used to revise the candidate and simultaneously remain
   part of its untouched prospective test.

Races already run without a pre-race frozen prediction are useful new historical
data, but they are not prospective evidence for that candidate. Raw data capture
and model promotion are therefore separate operations.

### Betfair historical-price research

Official Betfair material confirms that genuine historical market backtesting
is available:

- Betfair Australia's free Australia/New Zealand Thoroughbred CSV files cover
  2020–2025 and monthly 2026 files. They include runner-level BSP, result,
  pre-play/in-play minimum and maximum prices and volume, weighted average price,
  and best available prices plus market overround at scheduled start.
- Those free 2023–July 2026 files overlap almost the entire RacingEngine history
  and are the best first acquisition for closing/BSP benchmarking.
- Betfair Historical Stream data is available for Australian/New Zealand markets
  from October 2016. Basic provides one-minute last-traded prices without volume;
  Advanced provides one-second top-three ladders and volume; Pro supplies full
  ladders at API-tick frequency.
- Basic is suitable for an initial time-path/opening-versus-close study when
  last-traded price is sufficient. Advanced is preferable for executable
  decision-time back/lay prices, liquidity and slippage simulation.
- Purchased historical files can be downloaded programmatically only after they
  are attached to the account's `My Data` collection. The official API supports
  listing packages/files and downloading them.
- Betfair requires historical or delayed services for testing, analysis,
  training and simulation. Live logged-in data has separate product/licensing
  requirements. Australian users are advised to contact
  `automation@betfair.com.au` before purchasing detailed stream data.

Official sources:

- https://betfair-datascientists.github.io/data/dataListing/
- https://betfair-datascientists.github.io/modelling/dataSources/
- https://betfair-datascientists.github.io/data/usingHistoricDataSite/
- https://support.developer.betfair.com/hc/en-us/articles/12859956891932-How-Can-I-Make-HTTP-Requests-to-the-Historical-Data-API
- https://historicdata.betfair.com/Betfair-Historical-Data-Feed-Specification.pdf
- https://developer.betfair.com/en/vendor-program/product-requirements/

### Backtesting now

Two separate backtests are possible:

1. **Forecast backtest:** already operational. Reconstruct point-in-time ratings,
   score log loss/Brier/ranking/calibration and compare candidates on identical
   runners.
2. **Market and wagering backtest:** possible after Betfair matching. Compare
   rating-only probabilities with normalized scheduled-start/BSP probabilities,
   then with genuine decision-time prices where stream data supports them.
   Simulate commission, liquidity, slippage, scratchings and a rule frozen before
   evaluation. BSP is a powerful closing benchmark but is not an executable
   early price and must not be presented as one.

The first useful acquisition is the free Australian/NZ Thoroughbred CSV history.
It can answer how far V1 and each shadow model sit from the market and whether
the promising winning-margin candidate adds information beyond market prices.
Detailed Advanced stream data is only necessary when testing exact entry times,
available back/lay prices, movement, volume and execution.

### ML assessment

ML is technically possible but a production ML model is premature. The database
has 2,471 races, 29,845 runner results and only 153 distinct race days. That is
enough for a small, strongly regularized tabular challenger, but not enough to
justify a large neural model or careless random cross-validation.

Before ML:

- build one point-in-time runner feature table with exact availability cutoffs;
- source age/sex and correct WFA;
- finish winning-margin semantics;
- create pace/sectional, trip, rail/bias and campaign features;
- ingest and identity-match Betfair markets;
- group splits by chronological meeting day and never split runners from the
  same race across train/test;
- keep market probability out of the objective rating-only challenger, then
  test a second market-aware residual/blend model separately; and
- retain frozen V1 and the transparent candidate as baselines.

A sensible first challenger is regularized multinomial/logistic or gradient-
boosted ranking/classification with race-group normalization and shallow trees.
It should predict an entire probability book, not independent unnormalized win
probabilities. Deep sequence models should wait for materially broader weekday,
provincial and interstate history.

### Corrected pre-prospective build order

1. Source durable horse profiles: date of birth/foaling date, sex, country and
   provenance; calculate age on every race date.
2. Audit cumulative-versus-preceding margin semantics and freeze the form-
   anchored margin candidate.
3. Implement official Australian WFA, carried weight and their margin-anchor
   interaction as separate candidates.
4. Acquire and match the free Betfair 2023–July 2026 Thoroughbred CSV files;
   compare V1/shadows with scheduled-start and BSP probabilities.
5. Build source-consistent early/middle/late pace and sectional profiles.
6. Add pace reliability to margin interpretation.
7. Complete DT-W sourcing/validation and conservative trip adjustment.
8. Estimate daily track plus rail/lane/meeting pattern after pace correction.
9. Implement campaign stage/current-state profiles, including first-up,
   second-up, distance and going suitability with shrinkage.
10. Run steward-category ablations with decay; veterinary findings change
    fitness uncertainty rather than automatically granting rating points.
11. Build today's projected-race layer: cards, scratchings, barrier geometry,
    probabilistic map/tempo, weather, jockey and uncertainty scenarios.
12. Generate designated training predictions, fit calibration, and build the
    transparent market comparison.
13. Only then train a small ML challenger and a separate market-aware blend.
14. Freeze the complete candidates before calling later races prospective.

This order supersedes the mistaken impression that finishing Step 11 meant the
entire architecture was ready. It does not erase completed research; it puts it
back into the correct larger sequence.

## Session decision record — 21 August 2026

The user and assistant reviewed the build after concern that the lack of model
improvement might indicate missing fundamentals. The discussion established:

- the previous explanation of winning-margin treatment was incomplete;
- V1 preserves relative beaten gaps but does not adequately anchor the absolute
  winner level to known opposition and margins;
- authoritative handicapping research supports whole-race form anchoring with
  distance/pace/going-sensitive margin scales rather than a flat winner bonus;
- the new form-anchored margin shadow is the first encouraging retrospective
  candidate, but remains prospectively gated;
- completing Steps 1–11 did not complete the architecture because most
  contextual Step 12 layers remain absent;
- raw data ingestion should continue, while prospective claims require a saved
  prediction made before the result;
- free official Betfair Australia/NZ history can provide BSP and scheduled-start
  market comparison over the existing sample;
- ML is possible later as a small point-in-time tabular challenger, not yet as a
  large or production model; and
- the next committed build is durable horse profiles, historical age-on-race-
  day and official Australian WFA, including testing and controlled backtesting.

The detailed implementation chronology and numerical findings remain in the
preceding Winning Margin and Full Architecture audit sections. This record is
also copied to the dated handover and standalone session Markdown document.

## Horse profiles, historical age and official WFA — 21 August 2026

- Added versioned profile observations and runner-derived profiles with source
  provenance. Birth date, reported racing age, sex and country stay separate.
- The authorised Racing.com feed exposes horse ID, official racing age, sex and
  registered country, but not exact foaling date. DOB remains null, not guessed.
- Implemented AR161 historical age, AR168 WFA, AR169's 2kg female allowance and
  AR170 northern-sired Jan–July-foal allowances with explicit data gates.
- Refreshed the configured 1 and 8 August Victorian meetings: 228 observations
  across 218 horses; 228 ages, 228 sexes, 73 explicit countries, zero DOBs.
  Durable identity propagated these to 1,566 of 29,845 appearances (5.2%).
- All 58 tests pass. A research-only one-point-per-kg relative WFA candidate was
  slightly worse: validation delta +0.001324 (789 races), holdout +0.002323
  (793 races); negative favours the candidate and both intervals crossed zero.
- Decision: **REVISE / no promotion**. Sparse profiles and a first simple weight
  response do not establish that WFA is unhelpful.
- Output: `data/outputs/wfa_relative_weight_research_2026-08-21.json`.
- Next: acquire authorised exact DOB and sire-hemisphere history, rebuild full
  NSW/Victorian coverage, then test predeclared shrunk interactions prospectively.

## Internet source and lack-of-progress review — 21 August 2026

- Exact foaling dates are publicly visible on Breednet, with sex, country and
  sire/dam provenance. It is the best free discovery source found, but its terms
  limit use to personal/non-commercial viewing and prohibit reproduction. Bulk
  ingestion therefore needs written permission or a data licence.
- Racenet profiles appear similarly rich (including foal date in structured
  profile data), but no authorised modelling feed was confirmed. Punters pages
  are useful for manual checking/form downloads, not yet a verified durable
  profile licence.
- Racing Australia/Stud Book is the authoritative origin. Racing Australia
  confirms registration contains colour, sex, foaling date, sire and dam.
- Punting Form is the strongest ready-made modelling option found: historical
  point-in-time data, API, Betfair history and 10+ years of sectionals, but its
  modeller/commercial access requires a sales arrangement and historical data
  is separately priced.
- Racing Queensland also publishes genuinely open web services without
  copyright restriction, making it the best clean expansion source to assess.
- The weak WFA diagnostic is unsurprising: only 5.2% profile coverage, weight is
  endogenous to assessed ability, WFA is primarily a fair-conditions scale, and
  the tested one-point-per-kg relationship was deliberately simple. A tiny
  contextual correction cannot be expected to repair missing class, pace, trip,
  going and market information in the base model.
- Current progress is mainly infrastructure and falsification: the system is
  successfully preventing weak ideas from being promoted. Forecast improvement
  is more likely after complete point-in-time features, learned/shrunk effects
  and market benchmarking are combined—not from adding one rule in isolation.

## Seven-part historical profile scrape and WFA rerun — 21 August 2026

1. Racing Australia historical pages were tested first; older weights, form and
   results pages report that their material is no longer available.
2. Added `breednet-profile-v1.0` for DOB, sex, country, sire/dam, sire country
   and profile race-history evidence.
3. Profiles attach only with an exact local race-date overlap. Same-name pages
   without overlap are rejected.
4. Accepted HTML is gzip archived with URL, parser version and SHA-256.
5. Racing.com validation was perfect: 208/208 age and 208/208 sex matches.
6. AR168/169 was rebuilt; AR170 separately flagged 1,445 appearances using sire
   country plus Jan–July foaling.
7. The identical chronological validation/holdout protocol was rerun.

Full-run result: 9,067 requested, 8,319 parsed and 6,148 matched, plus 29 pilot
matches. There are 6,177 verified horses. 2,171 ambiguous/no-overlap pages were
rejected, 745 failed strict parsing and 3 network failures stayed missing.
Coverage rose from 5.2% to 24,096/29,845 appearances (80.7%); exact DOB covers
23,948 appearances. All 61 tests pass.

The WFA candidate moved closer to V1 but remained slightly worse. Validation
(789 races) was +0.000230, interval [-0.005836,+0.006861]. Holdout (793 races)
was +0.001475, interval [-0.011252,+0.014498]. Decision remains **REVISE / no
promotion**. Next learn and shrink weight response on training data, separated
by handicap versus set-weight/WFA conditions, rather than assume one point/kg.

Outputs: `data/outputs/breednet_profile_full_2026-08-21.json` and
`data/outputs/wfa_relative_weight_full_profiles_2026-08-21.json`.

## Kilogram-to-point research and fitted response — 21 August 2026

The statement “1kg = 1 point” mixes two rating scales and is not universally
correct:

- Racing NSW and Racing Victoria benchmark handicapping use 0.5kg per official
  benchmark point: **1kg = 2 official benchmark points**.
- RacingEngine V1 points are approximately length-style performance units, not
  official benchmark points.
- IFHA margin guidance varies with distance: about 3lb/length at 1000m,
  2lb/length at 1600m and 1lb/length at 2800m+. Converted to internal
  length-style points, this is approximately 0.735, 1.102 and 2.205 points/kg.
  IFHA also says pace and going affect the scale.

Added two research candidates: the official IFHA distance curve and a training-
only within-horse response. The latter compared consecutive runs within the same
race-type/distance segment, winsorised extreme changes and shrank estimates
toward zero with 200 equivalent pairs. Frozen training estimates included:

- handicap sprint 0.077 points/kg after shrinkage (733 pairs);
- handicap middle 0.255 (172 pairs);
- handicap staying 0.063 (only 9 pairs, heavily shrunk);
- set-weight sprint and WFA segments effectively zero.

Neither candidate improved V1. IFHA deltas were +0.000403 validation and
+0.001379 holdout. Learned-response deltas were +0.001226 and +0.002236.
All intervals crossed zero; both are REVISE and non-promotable. All 63 tests
pass. Therefore no universal kilogram correction belongs in the official model.
The official benchmark conversion remains useful for interpreting allocated
weights, while performance correction must remain distance/race-context aware.

Output: `data/outputs/weight_response_research_2026-08-21.json`.

## Controlled V2 rebuild — 23 August 2026

### Why V1 was invalidated

The V1 elite leaderboard failed a basic racing check. Investigation found that
Racing NSW sectional-PDF text had been allowed to own runner identity and runner
finish clocks. PDF layout debris produced names such as `NAME 3 70.4`, and a
77.81-second runner clock was attached to a 2000m race whose official time was
123.47. V1 then treated that impossible clock as ability, creating performance
figures above 300. V1 tables remain preserved for audit, but its NSW identities,
runner clocks, leaderboards and downstream conclusions are not promotable.

### V2 architecture and rebuild

1. NSW runner identity and official result now come only from Racing.com's
   structured race card. A new `racing-com-nsw-authorised-v2` source contains
   1,388 races and 19,870 runner rows through 15 August 2026.
2. Racing NSW PDFs are subordinate evidence. A sectional is stored against the
   V2 result source only when race number and runner number already exist on the
   structured card. A missing PDF no longer removes a valid result.
3. The clean rebuild excludes `rnsw-authorised` identity rows. It contains 2,720
   NSW/Victorian Saturday metropolitan races and 36,712 card runners.
4. Race clocks outside 12.0–20.5 m/s are quarantined. Runner clocks faster than
   the official winner or more than 20 seconds slower are quarantined. V2 uses
   no runner clock to set race level. There are 1,394 quarantine records; 1,391
   are explicit missing official times and three are observed impossible clocks.
5. The Valley had accidentally been absent from Victorian discovery. It is now
   included, restoring 19 meetings/186 races and Via Sistina's Cox Plate.
6. A 25-row official 2024/25 Australian Classifications audit set was saved from
   Racing Australia. It is evaluation evidence, not copied into V2 output.
7. `form-first-v2.0` starts with prior form/collateral evidence from the first
   four finishers and a historical class holding figure. It uses the IFHA
   distance-dependent margin curve (3lb/length at 1000m, 2lb at 1600m, 1lb at
   2800m+) and relative carried weight. Sectionals and raw speed cannot set the
   absolute race level.
8. A Racing.com semantic trap was fixed: the winner row contains the winning
   margin, not lengths beaten, so the winner is always zero lengths beaten.
9. The same-season elite audit matched 24 horses with Spearman rank correlation
   0.686. All four predeclared sanity checks passed: at least seven Group 1 runs
   in the top ten, at least two named expected elite horses, correlation >=0.50,
   and no impossible clock used.

### Prediction rerun and freeze decision

Only after the sanity gate passed, a chronological test compared equal chance,
V1 and a deliberately simple V2 current-state conversion on the same 577 races.
Temperatures were fitted on 2024; the untouched test was 2025-01-01 through
2026-08-15, requiring at least 60% prior-form coverage in both models.

- Uniform log loss 2.32102; race Brier 0.89826.
- V1 log loss 2.33564; race Brier 0.90085; top pick 13.69%.
- V2 log loss 2.45365; race Brier 0.93405; top pick 12.48%.

Therefore the V2 *run-performance/race-strength foundation* passes its racing
sanity check, but the naive median-last-three conversion to current predictive
ability fails and is frozen. It must not replace V1 for predictions. The next
experiment is a separately versioned current-ability model with recency,
reliability, distance/going suitability, campaign/layoff state and robust peak
handling. Opening/closing market comparison was not run: that belongs to the
later pricing-engine window with timestamped 2025/26 prices.

Primary artefact: `reports/v2_ratings/v2_rebuild_report.json`.

## Ratings-engine boundary and research direction — 23 August 2026

The product boundary was restated explicitly: Horse Ratings will contribute an
expected 60–65% of the eventual Pricing Engine, but it is a standalone system.
It estimates historical run quality and sustainable demonstrated ability. It
does not contain today's barrier/map, likely pace, current track pattern,
weather forecast, jockey/trainer intent, market prices, probability calibration,
EV, staking or bet selection. Those belong to the later Pricing Engine.

The proposed 20% EV betting threshold is therefore not a ratings promotion
criterion. It can only be tested after the Pricing Engine creates calibrated
probabilities and timestamped opening/closing prices are available. Profit at
20% estimated EV cannot be assumed in advance because model calibration,
overround, commission, liquidity and selection error determine realised EV.

### Findings from official and academic research

- IFHA ratings express ability in pounds and use distance-dependent
  pounds-per-length, WFA and sex allowances. Pace and going affect how literally
  margins should be interpreted; slowly run and heavy-ground form is less
  reliable. Annual ratings represent best sustainable performance, not a blind
  maximum.
- BHA handicappers begin with previous form, weight and margin relativities.
  Historical race standards and time analysis supply holding figures when form
  is sparse. They select credible anchor/yardstick horses rather than average
  every runner mechanically.
- As horses run again, BHA revises earlier races using collateral or
  back-handicapping. This is the main missing mechanism exposed by Ka Ying
  Rising, Via Sistina and the current top-four-median failures.
- BHA distinguishes a run performance figure from the handicap/current rating.
  Current ability can sit below an isolated peak when the figure is unreliable,
  flattering, stale or contradicted by recent form.
- Research on structured competitions shows raw ranks cannot identify absolute
  ability: elite horses self-select into elite races. Race/event level and the
  network connecting fields must be modelled.
- Statistical time studies confirm distance, track, going, weight, field size
  and barrier affect recorded time. Time therefore needs normalisation and a
  reliability role; it cannot independently define class.

### Ordered ratings-only build

1. Freeze the clean V2 identity/result/clock layer and expand its audit tests.
2. Separate three persisted objects: raw Run Figure, retrospectively revised
   Run Figure, and current Sustainable Horse Rating.
3. Replace top-four median Race Strength with a robust anchor selector using
   established/repeated figures, uncertainty and race-condition awareness.
4. Add historical standards for named races and hierarchical class/age/sex/
   condition groups, with shrinkage and no hard universal Group floor.
5. Implement iterative collateral back-handicapping with convergence bounds,
   provenance and a strict point-in-time mode for future prediction tests.
6. Correct WFA/sex/weight relativity by race date and distance. Keep handicap,
   set-weight, WFA and age-restricted equations separate.
7. Add winner-dominance and margin reliability: winning margin versus beaten
   margin, eased horses, extreme margins, pace/going reductions and caps.
8. Rebuild time as independent supporting evidence: same-day variant,
   track/distance/rail/going pars, pace shape and sectional completeness. Time
   may raise confidence or flag disagreement, not silently overwrite form.
9. Build Sustainable Horse Rating from best repeatable figures, recency,
   uncertainty, career stage and distance-band evidence; preserve separate
   sprint/mile/middle/staying abilities where supported.
10. Create a larger official audit across 2023/24–2025/26 with exact race-level
    official figures, plus mandatory case audits for Cox Plate, Queen Elizabeth,
    Everest, Doncaster and major age-restricted races.
11. Require racing gates before forecasting: official rank agreement, sensible
    Group hierarchy, known elite performances, no identity/clock contamination,
    stability under one-race deletion and bounded retrospective revisions.
12. Only after the ratings gates pass, run chronological ratings tests against
    V1, equal chance and simple rank/Elo baselines. Market/EV tests wait for the
    separate Pricing Engine.

### Sectional role inside the Ratings Engine

Sectionals are historical performance evidence, not a pricing input when used
to interpret completed races. The current `form-first-v2.0` deliberately uses
no sectional adjustment. Audit on 23 August found matched raw V2 NSW sectionals
for 988 races and Racing.com Victorian sectionals for 1,330 races, but the
canonical builder still supports the old `rnsw-authorised` key rather than
`racing-com-nsw-authorised-v2`. This must be corrected before any sectional
experiment; old PDF runner identities must never return through the feature
join.

The planned sectional model has four distinct outputs:

1. **Race pace shape:** early, middle and late pressure relative to a
   track/distance/going/same-day standard.
2. **Runner energy distribution:** early speed, mid-race efficiency and late
   strength, expressed relative to the race and an external par rather than raw
   seconds.
3. **Performance interpretation:** bounded pace/trip adjustments and reduced
   margin reliability for crawls, collapses, heavy going and incomplete data.
4. **Ability profile:** repeatable sprint/mile/middle/staying sectional traits
   with uncertainty; no single fast last 400 becomes permanent ability.

Sectionals must not independently set Race Strength and must not be double
counted with overall time or beaten margin. Same-race relative splits explain
who benefited; external/day-adjusted pars determine whether the race itself was
fast or slow. Coefficients and caps will be fitted on training data and promoted
only if they improve next-run rating stability and chronological winner ranking.
Today's projected pace remains a later Pricing Engine feature.

Historical environment is part of Step 2 Ratings, not deferred to Pricing.
Store race-timestamped wind speed/direction/gusts, rainfall windows, official
track changes, rail, lane use and observed meeting pattern. Resolve wind against
course/section orientation to estimate headwind/tailwind/crosswind exposure.
Combine exposure with sectional position: a leader or uncovered wide runner
may work harder into a headwind than a runner drafting behind. Reported,
observed and statistically confirmed lane effects remain separate evidence.
Related wind, wide-run, DT-W, sectional and steward observations must be merged
into one workload estimate to prevent multiple bonuses for the same trip.

The timing boundary is strict: conditions observed during a completed race
interpret its historical rating in Step 2; forecast/live information available
before an upcoming race is consumed only by the Step 6 Pricing Engine.

## Step 2 shadow build — pace, sectionals and environment — 23 August 2026

Implemented `pace-shape-v2.0-shadow`. It does not alter `form-first-v2.0`.

- Canonical sectional semantics now accept clean NSW source
  `racing-com-nsw-authorised-v2`; PDF names never own identity.
- NSW consecutive 200m intervals are summed into early/middle/late phases. For
  races longer than 1200m the documented final-1200 window is used because the
  source commonly does not publish earlier intervals. Victoria retains its
  source-defined start-to-800, 800-to-400 and final-400 phases.
- Phase pars are source/track/distance/going specific with an explicit
  same-source distance/going fallback and robust median/MAD scaling.
- Stored continuous early/middle/late pace, acceleration, leader pressure and
  field-compression evidence plus labels. Stored runner early contribution,
  pressure absorbed, position change, pace advantage and a capped +/-2-point
  *shadow* adjustment.
- Built 1,865 race pace shapes and 18,995 runner pace rows from 1,933 races with
  at least three complete runners. Labels: 702 even, 282 slow, 243 fast, 175
  sprint-home, 161 collapse, 127 very slow, 92 sustained high pressure and 83
  very fast.
- Rebuilt weather history, including The Valley: all 2,720 clean races now
  have timestamp-matched hourly station observations. Official steward reports
  exist for 1,079 Victorian races. Lane-report coverage is zero.
- Wind direction/speed are stored, but headwind/crosswind components remain
  null until reliable course and sectional bearings are sourced. No guessed
  course orientation or statistical winner-derived lane bias is active.

Named-race audit: the 2024 Cox Plate classified as a pace collapse (fast early
1.78, fast middle 1.23, slow late -0.87); Pride Of Jenni absorbed the largest
pressure. The 2025 Queen Elizabeth classified fast early. The 2026 Doncaster
classified even at 75% field coverage, but Sheza Alibi's runner number is absent
from the PDF splits, so she correctly has no personal sectional adjustment.
The 2025 Everest has no matched sectional report and remains missing rather
than inferred.

Step 2 is **SHADOW / NOT PROMOTED**. Before rating integration it requires
course bearings, lane/path evidence, better NSW completeness, pace-archetype
manual audits, chronological par construction, next-run repeatability tests and
an ablation proving the bounded adjustments improve the accepted ratings.

Outputs: `reports/v2_ratings/canonical_sectionals_v2_rebuild.json` and
`reports/v2_ratings/pace_shape_v2_shadow.json`. All 83 tests pass.

### Freeze strategy

Each stage is versioned and frozen if it misses its gate. The accepted clean
data and previous rating stage remain unchanged while the failed component is
reworked. In particular, do not proceed from Race Strength to Sustainable Horse
Rating if the named elite-race audit is wrong; do not proceed from ratings to
pricing if the rating-only chronological test is worse than its baselines.
# 2026-08-23 — Step 2 nine-gate completion

- Replaced retrospective sectional pars with strictly chronological, prior-race-only pars (`pace-shape-v2.1-pit-shadow`). This reduced scored races from 1,865 to 1,565 because early races now seed history instead of borrowing from the future.
- Completed numeric/manual archetype audits. The labels are useful flags, but extreme meeting-wide slow readings show the going bucket does not fully absorb meeting speed.
- Audited official course/wind sources. ATC and VRC offer live track wind tools; a reproducible public historical archive and surveyed section bearings were not established. Headwind/crosswind fields therefore remain null.
- Lane bias remains unavailable. Official steward path events are retained separately: 4,048 clean runners match slow-start/interference/held-up/wide evidence. These events are not presented as measured lanes.
- Next-start test: 12,140 pairs. Base MAE 8.4509; pace-adjusted MAE 8.4485 (improvement 0.0025 only). NSW improved 0.0132; Victoria worsened 0.0020.
- Disadvantaged/suitable-next-run group: 1,032 runs improved by 1.39 points next start; neutral control (7,555) changed -0.18. Encouraging association, not causal proof.
- Chronological race-ranking ablation (1,203 test races): log loss 2.53106 base versus 2.53098 adjusted. NSW worsened; Victoria improved. Top-pick strike fell from 12.47% to 12.39% overall.
- Cox Plate 2024 now scores very fast early (+1.49), fast middle (+1.69), weaker late (-0.64). Pride Of Jenni gets +1.97 context compensation; Via Sistina -0.38. The latter demonstrates why pace must annotate context rather than subtract achievement from an elite winning run.
- 2025 Everest has zero official sectional rows in the current archive. Sheza Alibi's 2026 Doncaster runner 15 is absent from the stored official sectional PDF. Both are registered permanent current-source gaps and are never imputed.
- Promotion decision: **fail/freeze**. The effect is too small, inconsistent by jurisdiction, and still confounds meeting speed. Keep the accepted V2 rating unchanged.
# 2026-08-23 — Step 2 adjustment recovery V2.2

- The project remains locked on Step 2; Step 3 is explicitly blocked until sectional adjustments pass.
- Added `sectional-adjustment-v2.2-shadow` with exact-condition residual history and leave-one-race-out meeting-speed correction.
- Separated achievement, trip compensation and steward evidence. All coefficients were fitted independently for NSW/Victoria with zero as a valid choice.
- Achievement was rejected at zero in both jurisdictions. Trip survived at NSW 1.0 and Victoria 0.3 alone; steward evidence survived only in Victoria at 1.0.
- Holdout next-start MAE improved from 8.05433 to 8.05008 for trip-only, but NSW race-ranking log loss worsened. Combined improved overall log loss slightly but also worsened NSW.
- No candidate improved next-start MAE and ranking log loss in both jurisdictions. Nothing was promoted.
- Research points toward distance-specific energy-efficiency curves, drafting/exposure and late deceleration rather than a generic weighted sectional blend. That becomes V2.3 within Step 2.
- Frozen evidence: `reports/v2_ratings/sectional_adjustment_v2_2_build.json`, `sectional_adjustment_v2_2_evaluation.json`, and `sectional_adjustment_v2_2_findings.md`.

## Step 2 two-part audit — 23 August 2026

- Researched the Victorian source rather than guessing extra splits. Racing.com
  documents 200m split and cumulative sectional data and CSV availability. The
  current importer saves only three aggregate phases, so this is an ingestion
  limitation, not proof that official detail does not exist.
- Built `vic-staying-two-phase-v1.0-shadow` using only observed opening and
  final-400 phases. The fitted coefficient was 0.8 from 334 pre-2025 pairs.
  Holdout next-start MAE improved from 7.9187 to 7.8811 and ranking log loss
  from 2.6974 to 2.6739, but both paired 95% intervals crossed zero. Audit and
  promotion therefore failed.
- Froze V2.3 sprint/middle coefficients at their pre-holdout values and stored
  their SHA-256 identity in an append-only forward ledger. No coefficient was
  re-estimated from the 22 August card.
- Imported official 22 August 2026 NSW and Victorian results into an isolated
  rebuild. There were 118 runners with supported energy signals and 12 races
  met the common prediction policy. NSW improved by 0.00219 log-loss points;
  Victoria worsened by 0.01052; combined log loss worsened from 1.92403 to
  1.92925. Sprints were almost flat/slightly favourable; middle distance was
  worse. Next-start outcomes remain pending.
- **Decision:** remain on Step 2. Do not tune to this one card. Acquire more
  post-cutoff meetings, wait for subsequent starts, and repair the richer
  Victorian 200m ingestion. Step 3 is prohibited until improvements hold
  overall, in both jurisdictions, by distance band, and under uncertainty.

## Seven-test Step 2 recovery programme — 23 August 2026

1. **Victorian 200m source repaired.** The public Racing.com runtime exposed
   the official sectional GraphQL query and CSV host. The verified backfill
   covers 1,330/1,341 races, 13,919 runners and 106,249 splits. Horse identity
   remains owned by official V2 results; 103 ambiguous/unmatched observations
   were rejected. No rating was changed.
2. **Audit frozen.** `sectional-promotion-protocol-v2.0` fixes training cutoff,
   common-race coverage, minimum future sample sizes and paired uncertainty
   requirements. Market/EV testing remains Step 6.
3. **Unseen meetings appended.** The only results available after the training
   cutoff at the current date are the 22 August NSW and Victorian metropolitan
   meetings. They are immutable ledger evidence, not training data. More truly
   live meetings do not yet exist and cannot be manufactured.
4. **Forward scoring.** V2.4 scored 127 runners. Twelve races met prediction
   coverage. NSW improved, Victoria worsened, and combined log loss worsened by
   0.00152. Next-start results are not yet observable.
5. **Full audits.** In the 2025+ historical holdout, V2.4 improved ranking
   overall, in both states and every distance band. Ranking uncertainty was
   favourable. Next-start MAE improved directionally overall/both states/all
   bands, but its overall 95% interval was -0.03737 to +0.00521. It failed.
6. **Stall diagnosis.** The old three-phase Victorian data was a genuine data
   defect, now solved. The remaining stall is target/model design: sectional
   compensation contains stable race-ranking information, but a single next
   start is noisy and can contain a new adverse trip. Generic additive energy
   bonuses also mix run achievement, trip recovery and pace suitability.
   Research supports distance-specific pacing, drafting and course/condition
   pars rather than raw final speed alone.
7. **Distinct candidate tested.** V2.5 used hierarchical
   track-distance-going pars. Compensation-only improved next-start MAE by
   0.02035 and ranking log loss, but its next-start 95% upper bound was +0.00143.
   It narrowly failed and was not promoted. Further coefficient nudging on the
   same holdout is prohibited.

### Route over the line — V2.6 specification

- Estimate a persistent horse pace-style vector separately from the run rating:
  preferred early pressure, acceleration point, sustained-speed capacity and
  late burst.
- Estimate latent ability using the median of the next two or three eligible
  same-band performances and a separate next-neutral-trip target. All targets
  must be constructed point-in-time and handle right-censoring.
- Replace hard par fallbacks with partial pooling across track, exact distance,
  going and rail/course configuration.
- Model drafting/exposure from actual split positions, then add curvature,
  gradient, wind and measured extra distance only where sourced.
- Train on pre-2025, select once on 2025, and reserve 2026 plus the live ledger
  as final untouched tests. Do not select coefficients against both years.
- Promote only after the frozen protocol passes. If latent ability improves but
  winner ranking does not, retain the feature as an explanatory pace trait. If
  ranking improves but latent ability does not, keep it for the later race-shape
  pricing layer rather than forcing it into the core rating.

### Build status — paused until next week

Step 2 is deliberately paused on 23 August 2026 and will be resumed next week.
It is not marked complete. Step 3 remains locked. On resumption, append new
meetings and subsequent-start outcomes to the immutable ledger, then begin the
pre-specified V2.6 target decomposition. V2.4 and V2.5 must not be retuned using
the August 22 holdout. The project only leaves Step 2 after the frozen promotion
protocol passes in full.

### Breakout-horse sanity check — Natural Fling

Natural Fling's four-length Group 3 Caulfield win on 15 August 2026 is now a
named hard expert sanity test. The owner's 20 years of wagering experience
assesses the completed run at **100-110 on this engine's intended scale**. She
beat Listed/Group-quality opposition by four lengths and is already considered
capable of winning Group 2/3 company. A candidate outside 100-110 fails this
domain audit and forces a review of the rating architecture.

This is a hard acceptance band and still must not be inserted as a fitted
training label. The model must reach it from independent evidence rather than
being numerically forced to print 100. A result such as the current 83.53 means
the architecture is wrong or incomplete. The test specifically detects
over-shrinkage toward pre-race official ratings, failure to credit a dominant
winner, and excessive dependence on the beaten field's prior ratings. Required
outputs are raw time/variant, positive winning-margin interpretation, WFA, 200m
sectional achievement, collateral strength, age/development uncertainty and
separate achieved-versus-projected ratings.

Ka Ying Rising's 2025 Everest remains the elite comparison. The audit should
test whether the gap is defensible after both performances receive equivalent
evidence treatment; it must not assume that Dan O's numerical scale maps
point-for-point onto this engine.

### Future Group horse research decision

Early identification is now a first-class ratings-engine objective, not a later
pricing extra. Pure collateral is structurally late: it waits for a horse to
defeat recognised quality before recognising the ability that enabled the
defeat. Research supports combining independent achieved-performance evidence
with a point-in-time latent ability trajectory and an uncertain forward
projection.

The engine will separately produce achieved run rating, current latent ability,
30/90/180-day development distribution, pace-style vector and breakout
probabilities. Shrinkage toward an old official rating can weaken only when
independent time, margin, WFA and sectional evidence corroborate the move. The
rule is symmetric and must also reject false breakouts.

A frozen historical young-horse cohort will measure whether ability is detected
before later Listed/Group or peak-rating confirmation. Required metrics are
precision, recall, calibration, false-discovery rate, future peak-rating MAE and
lead time, with explicit retirement/export/missing-outcome reporting. Natural
Fling remains a hard 100-110 case but cannot be used as a fitted target. Full
research, sources, grey areas and gates are recorded in
`docs/future_group_horse_research.md`.
# 2026-08-23 — Step 2 V2.3 energy curves

- Completed all seven V2.3 tasks. NSW retains full 200m curves; Victoria remains an honest three-phase source and is never interpolated into fake 200m data.
- Built chronological winner-derived efficient profiles by source, distance band and going; derived early-energy, late-deceleration, burst and front-exposure signals.
- Compensation improved 2025+ same-band MAE overall, NSW, Victoria, sprint and middle. It improved race-ranking log loss overall and in both jurisdictions with a paired 95% interval fully below zero.
- Suitable lower-cost next setups improved +2.19 points across 2,100 pairs.
- The next-start MAE confidence interval still crosses zero. Staying is frozen at zero because pre-2025 support is 13 NSW and zero Victoria; the Victorian 2040m source cannot produce a genuine middle third.
- Decision: V2.3 is the strongest candidate but remains frozen. Accepted ratings unchanged and Step 3 blocked. Forward-test sprint/middle; solve staying resolution separately.

## Exit update — 29 August 2026: final Horse Ability and Group 1 pricing test

Horse Ability V2 is complete as
`horse-ability-v2.8-final-research-freeze`. The configuration is locked: four
runs, 90-day half-life, 25% peak blend, 1.5-run reliability prior, 10%
trajectory; 25% initial handicap response with effective-dated collateral
revision; zero mechanical layoff decay; zero distance/going base adjustment.
It is a final research freeze, not production promotion, because the validation
interval against V1 includes zero. All named chronological gates pass: Natural
Fling achieved 104.22/current 99.67; Sheza Alibi achieved 116.24 versus
Gringotts 112.37 and current initial ability is 110.83 versus 110.28.

The requested one-year Sydney/Melbourne Group 1 Betfair-close test was then run
without changing the rating. The rule used the frozen ratings-only temperature
of 60, converted runner probabilities to a 110% book, and staked $1 when
`Betfair scheduled-off best back / model 110% price - 1 > 10%`. It covered 58
of 59 races; Betfair has not published August 2026, so the 22 August Winx
Stakes is excluded. Result: 452 bets, nine winners, $452 stake, -$252 gross P&L
and -$264.225 after commission, or -58.46% ROI. The race-bootstrap 95% interval
is [-87.74%, -15.96%]. Reject this direct pricing rule.

The 2026 Doncaster explains the failure. Ratings-only probabilities were very
compressed: all 16 runners received 4.77%–7.58%, producing 110% quoted prices
from 11.99 to 19.04. Betfair had Sheza Alibi at 2.02 while the model rated her
102.85, assigned 6.31% and quoted 14.40. The rule did not bet the winner and bet
14 of the other 15 runners. Pericles was the highest model ability at 113.83
and 11.99; Gringotts was 108.36 and 13.14. This is not a bookmaker-margin bug:
the underlying ability-to-win probability conversion and missing race-specific
information are inadequate for Group 1 pricing.

Do not change the completed Horse Ability ratings to fit these returns. The
next task is a separately versioned Pricing Engine. It must address probability
dispersion, sparse/emerging-horse uncertainty and current race context, choose
its rules on a declared development partition, and reserve new races or an
untouched time block for confirmation. The observed one-year Group 1 set is no
longer an untouched final holdout.
