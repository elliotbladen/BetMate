# RacingEngine ratings build plan

Status: agreed direction as at 2026-08-20. This document preserves the design
decisions and ordered work for the next build sessions. Build and validate one
step at a time; do not silently promote several new rating inputs together.

## V2 reset status — 23 August 2026

The data and run-rating foundation has been rebuilt as `form-first-v2.0`.
Structured cards now own NSW identities/results; sectionals are subordinate;
impossible clocks are quarantined; The Valley is included; an official
Australian Classifications audit set exists; and the elite sanity gate passes
(24 matches, Spearman 0.686). The old NSW/V1 leaderboard is invalidated but
retained for forensic comparison.

The first V2 current-state predictor failed its 577-race chronological test and
is frozen. Do not proceed to pricing or market-edge claims. The next controlled
candidate is the conversion from run performance to current Horse Ability:
robust sustainable peak plus recency, uncertainty, campaign/layoff state and
distance/going suitability. Preserve the V2 run ratings as the baseline and
require an improvement over both V1 and equal chance before promotion.

## Horse Ability V2.1 first candidate — 28 August 2026

The first controlled current-ability candidate is implemented as
`horse-ability-v2.1-sustainable-recency-shadow`. It materialises strictly
point-in-time states from prior accepted V2 runs using a fixed six-run window,
180-day recency half-life, bounded sustainable-peak blend, reliability
shrinkage and explicit robust uncertainty. It remains shadow-only.

The candidate decisively improves the rejected V2 median-last-three state in
validation, beats uniform directionally in validation and conclusively in the
historical holdout, and beats V1 in the historical holdout. It misses V1 by
`0.00094` validation log loss and its required uncertainty gates do not all
pass. It is not promoted.

More importantly, the mandatory Natural Fling breakout audit fails upstream:
the accepted V2 run foundation rates the four-length 15 August Group 3 win only
`83.53`, versus the predeclared 100–110 acceptance range. The present run model
gives a winner zero margin component and lets stale low prior/official anchors
dominate a lightly raced improver. Horse Ability is therefore
`BLOCKED_UPSTREAM` until a separately registered achieved-run recovery passes
the frozen breakout cohort and elite gates. WFA/sex/age versus handicap weight
semantics must be tested separately; they cannot be repaired silently inside
the Horse Ability state.

See `reports/v2_ratings/horse_ability_v2_1_first_candidate_findings.md` and the
machine-readable companion JSON. Do not tune the sustainable-peak blend against
the observed validation/holdout. The next state-family experiment, after the
upstream run gate passes, is explicit history-depth/uncertainty calibration.

## Six-stage V2 ratings-to-market programme — 23 August 2026

Pace shape and pace counterfactuals are first-class requirements. The engine
must be able to identify pace contributors, beneficiaries and disadvantaged
horses and estimate how rankings change under alternative plausible pace
shapes. Counterfactual outputs are probabilities with uncertainty, never claims
that a horse certainly would have won.

### 1. Accepted run-rating foundation

Freeze clean identities/results and rebuild canonical sectionals on V2 keys.
Complete WFA, weight, distance-dependent margins, race-condition families and
historical standards. Produce initial Run Figure plus component ledger. Gate on
identity/clock integrity, official classifications and named elite races.

### 2. Pace-shape and sectional rating

Normalise early/middle/late splits by track, distance, going, rail and same-day
variant. Measure acceleration, deceleration, leader pressure, field compression
and energy distribution. Produce continuous pace scores plus human labels.
Adjust run figures only by bounded, non-double-counted pace/workload residuals.
Gate using pace archetype audits, missing-data tests and next-run repeatability.

### 3. Collateral form and retrospective revision

Select reliable yardstick horses and iteratively back-handicap races as runners
meet again. Store initial and revised figures, every supporting form line,
revision size and convergence. Gate on bounded revisions, one-anchor deletion,
chronological isolation and exact Everest/Cox Plate/Queen Elizabeth/Doncaster
audits.

### 4. Sustainable ability and pace profiles

Convert revised runs into current demonstrated ability with repeatability,
recency, career stage, distance bands and uncertainty. Maintain early-speed,
sustained-speed, finishing-speed and pressure-tolerance subratings. Gate against
V1, simple Elo/rank and naive last-three baselines on identical races.

### 5. Pace counterfactual and ratings completion

Build a historical race simulator conditioned on pace regime. For slow/even/
fast/very-fast/collapse/sprint-home scenarios, redistribute only the estimated
pace/workload effect and return scenario Run Figures, ordering, win likelihood
and uncertainty. Validate on naturally similar rematches and held-out pace
regimes. Freeze the full Ratings Engine only when actual-pace and counterfactual
audits are stable. No barrier/map/current-day inputs enter the base rating.

### 6. Pricing integration and market EV test

After ratings freeze, the separate Pricing Engine combines ratings with today's
barrier, projected map/pace, track pattern, weather, jockey/trainer and other
time-stamped evidence, then calibrates probabilities. Compare against
de-vigged opening and closing markets on 2025/26 only. Report all runners and a
predeclared 20%+ estimated-EV betting subset, including calibration, CLV,
commission, liquidity, turnover, ROI, drawdown and confidence intervals. No
profit claim is permitted from ratings alone.

At every stage retain the last accepted version. If a gate fails, freeze that
candidate and revise only its component; never rebuild accepted upstream data
or silently carry a failed adjustment forward.

## Objective

Build an auditable historical Horse Ability and Race Strength system first,
then add today's race-specific adjustments and pricing. The model should know
the difference between demonstrated ability, interpretation of a past run,
current condition/intent, and today's projected race shape.

The initial ambition is not to claim that a partial ratings model can beat a
mature closing market. Matching the market out of sample without consuming
market prices would already be strong evidence. The eventual wagering question
is whether the model adds information beyond the market, particularly at the
time a price is available, and whether that information survives to the close.

## Four separate modelling layers

1. **Horse Ability** — underlying demonstrated merit from historical runs.
2. **Historical run context** — class, opposition, time, weight, pace, ground
   covered, interference and track/lane assistance used to interpret a past run.
3. **Current condition and intent** — campaign stage, trials, placement, gear,
   fitness, stable patterns and time-stamped human evidence. This initially
   affects uncertainty/scenarios rather than rewriting base ability.
4. **Today's projected race** — barrier, map, pace, scratchings, rail, weather,
   jockey and observed same-day track pattern. This produces today's expected
   performance and eventually a probability/price.

These layers require separate database records and component breakdowns. A
manual observation must never silently overwrite Horse Ability.

## How a candidate input passes or fails

Every meaningful feature family is registered before testing with its formula,
data availability, expected direction, missing-value policy, evaluation dates
and primary metric. The immediately previous accepted model is the baseline.

For each candidate:

1. Recreate every historical prediction chronologically using only information
   available before that race.
2. Compare candidate and baseline on the exact same eligible races and runners.
3. Report Brier score, log loss, calibration, winner rank and coverage.
4. Report results by season/time block, jurisdiction, track, distance, going,
   field size, class and history depth.
5. Use race-level or chronological-block resampling to estimate the uncertainty
   of the difference, rather than treating a tiny metric change as proof.
6. Inspect direction, magnitude, missingness and racing plausibility.
7. Confirm the chosen design once on an untouched final holdout.

A feature is promoted only when it improves the pre-registered primary metric,
does not materially damage log loss/calibration or important segments, maintains
acceptable coverage, has a plausible mechanism, and repeats across time blocks.
There is no permanent magic threshold such as `0.001`: the report must include
the effect size and its uncertainty. A narrow inconclusive result is revised or
kept as research evidence, not called an edge.

Coherent interactions are tested only after their components. Examples include
weight with WFA, barrier with track geometry/map, and wide-running evidence with
DT-W/sectionals. Ablation tests then show which component contributes.

## Evaluation and market benchmark policy

### Internal model comparison

- **Brier score:** squared probability error for winners and losers; lower is
  better. Report per-runner and race/field-size-aware summaries.
- **Log loss:** strongly penalizes assigning very little probability to the
  winner; lower is better.
- **Calibration:** runners assigned about 20% should win about 20% over a large
  enough sample.
- **Ranking:** top-rated strike rate, winner in top two/three, and mean/median
  winner rank.
- **Coverage:** eligible/scored races, runners with history, debutants, missing
  features and every exclusion reason.
- **Residuals:** next performance minus expected performance, segmented to find
  systematic under/over-rating.

### Market comparison

The market is an external benchmark, not an input to the base Horse Ability
calculation. Store time-stamped prices separately and remove the bookmaker or
exchange overround before comparison.

Compare against:

- equal probability (`1 / field size`);
- the immediately previous accepted model;
- available opening/decision-time market probabilities; and
- closing market probabilities as the strongest information benchmark.

Tests should answer three different questions:

1. Does the new rating improve our previous rating out of sample?
2. How close is the rating-only model to the market at the same point in time?
3. Does the model add predictive information after controlling for the market,
   and do identified differences beat the later close (CLV)?

Being level with a mature closing market using only objective pre-race data would
be an excellent result, not a failure. Profitability additionally requires that
any advantage exceed commission, margin, liquidity and execution error. On-day
information may explain a material share of the remaining gap; it must be added
as time-stamped evidence rather than backfilled with hindsight.

Every candidate receives a permanent promotion report containing configuration,
data cutoff, code/model version, eligible sample, metrics, segment results,
uncertainty, failure cases and the promote/revise/reject decision.

## Same nominal class at different venues and jurisdictions

A BM72 is a race condition, not a universal quality number. A Sydney Saturday
metro BM72, Hawkesbury BM72 and Brisbane BM72 may attract materially different
fields. Do not hard-code one fixed rating for every BM72 and do not hard-code
subjective venue offsets without evidence.

Use a hierarchical class prior with partial pooling:

```text
national/broad benchmark prior
  -> jurisdiction prior
    -> meeting grade / metro-provincial-country prior
      -> venue and class-band prior
        -> this race's pre-race field strength
```

Fine-grained groups borrow strength from their parent when sample sizes are
small. The stored record includes sample size, shrinkage weight and uncertainty.
The actual pre-race field—median/top-four ability, depth and proportion of rated
runners—then moves the race away from its class prior. Later performance tests
whether the hierarchy predicted future form, but cannot leak back into the
original pre-race estimate.

Current data covers NSW/Victorian Saturday metro racing. It cannot honestly
estimate Hawkesbury or Brisbane-specific effects until those jurisdictions and
meeting grades are sourced with equivalent provenance. Until then, visitors
from outside scope need a broad, uncertain prior rather than false precision.

## Intricate race-context evidence

Steward reports are valuable but incomplete. They will not reliably capture
every missed start, wide passage, lane choice, pace advantage, quiet preparation
or visual fitness clue. Missing evidence must remain unknown, not be interpreted
as a trouble-free run.

### Objective data available now

- barrier and field size;
- in-run positions at supplied markers;
- sectional times;
- explicit NSW DT-W values;
- official steward events;
- rail, weather, class, weight, jockey and trainer.

These can support conservative historical trip features such as slow-start
frequency, actual settling position, position change, ground covered, late split
and corroborated interference. Barrier is a pre-race opportunity; actual trip
evidence determines whether it became an advantage.

### Evidence to add after the base model

- structured video/replay review for wide/no-cover, lane, traffic and ride shape;
- live same-day rail/lane and leader-pattern observations;
- trials, gear changes, nominations and placement patterns;
- trainer-intent hypotheses;
- yard/parade observations; and
- probabilistic barrier-manners and map scenarios.

Every manual or inferred observation requires horse/race identity, category,
source, observer, timestamp before the race where applicable, confidence,
evidence text and immutable revision history. Initially it changes uncertainty
or scenario weights. It becomes a numerical adjustment only after enough
prospectively recorded examples pass the same out-of-sample test.

Track bias has two distinct uses. A post-meeting estimate may clean historical
run merit. A live estimate for race 5 can use only races 1–4 and information
timestamped before race 5; later races cannot be used retrospectively.

## Ordered build

### Step 1 — automated data-readiness report

Report completeness by meeting/source for results, official/runner times,
margins, sectional markers, runner metadata, class, weather, DT-W, steward
checks/reports/events and pre-race cards. Finish with an explicit readiness
status and reasons for every gap.

### Step 2 — freeze the evaluation protocol

Fix train/validation/holdout dates, eligibility, unrated-horse handling,
field-size treatment, metrics, segments, resampling and promotion rules.

### Step 3 — definitive V1 benchmark

Persist race-level predictions, probabilities, Brier/log loss, calibration,
ranking, coverage and segment diagnostics for the frozen periods.

### Step 4 — normalize sectional semantics

Derive and validate explicitly named final-200/400/600 and intermediate pace
features across NSW and Victorian source formats. Never substitute unlike splits.

### Step 5 — horse identity audit

Detect collisions and source spelling variants, populate reviewed aliases and
introduce durable internal horse identifiers.

### Step 6 — class-prior research

Measure sample sizes and outcomes by the hierarchical class/jurisdiction/meeting
structure; design shrinkage and inspect outputs before rating integration.

### Step 7 — pre-race field strength

Using strictly prior horse states, calculate field median, top end, depth,
rated-runner coverage and uncertainty, then freeze each pre-race estimate.

### Step 8 — Race Strength Rating

Combine the shrunk class prior with actual pre-race field strength. Store
post-race time/margin evidence separately with a complete component breakdown.

### Step 9 — Race Strength integration

Create new model versions for class-only, field-only and combined formulations.
Do not add weight, track bias, stewards or map inputs in this step.

### Step 10 — promotion evaluation

Run the registered comparison, uncertainty analysis and permanent decision
report. Promote, revise or reject without changing the frozen test rules.

### Step 11 — daily variant and weight/WFA

Test daily variant, weight/WFA and then their justified interaction in separate
versioned comparisons.

### Step 12 — contextual layers

Add normalized pace/sectionals, trip/DT-W, barrier manners, meeting/rail/lane
pattern, steward ablation, campaign stage, stable/intent evidence, yard evidence
and today's probabilistic map one controlled layer at a time.

## Current build position — 22 August 2026

The original Steps 1–11 have been built and researched. Race Strength was
promoted only where justified; WFA and both weight-response candidates remain
shadow research because they did not improve the frozen validation/holdout
tests. The next architecture is deliberately split into the following gates:

1. Freeze `performance-par-v1.0` and preserve the existing evaluation ledger.
2. Classify every race as handicap, quality handicap, WFA, set weights, set
   weights plus penalties, or unknown.
3. Reconstruct carried-weight context without guessing missing allocated
   weight, claims, overweight or penalties.
4. Calculate chronological changes in weight, official rating, class and
   distance, plus whether the horse moved to a stronger race.
5. Join prior daily variant, going, sectionals, distance travelled, steward
   evidence, campaign stage and Race Strength as separate contextual evidence.
6. Materialise one leakage-audited point-in-time row per historical runner.
7. Improve source capture for the missing weight components and pre-race cards.
8. Import timestamped Betfair opening, decision-time and closing markets.
9. Train small, interpretable candidates using training data only.
10. Run chronological ablations and promote only repeatable improvements.

Steps 1–6 in this revised gate sequence are complete. They prepare trustworthy
inputs; they do not by themselves claim a predictive improvement.

## Current-form and ranking gate — 22 August 2026

Steps 1 and 2 of the post-research improvement plan have now been tested:

1. improved current form using peak-versus-current form, uncertainty and
   history depth; and
2. a race-level conditional-logit layer using only prior point-in-time inputs.

Every coefficient was fitted on the 2023-08-12 to 2024-08-31 training period.
Validation and historical holdout were evaluation-only. All candidates improved
headline log loss in all three periods, but the frozen 95% validation intervals
still included zero. Therefore no candidate was promoted.

The leading frozen research candidate is `race-level-conditional-logit-v1.0-core-cv`.
It improved validation log loss by `0.003060` and historical-holdout log loss by
`0.005944`, with Brier improvements in both periods. Its validation interval was
`[-0.006350, 0.000264]`: close, but not proof under the frozen rule.

Do not tune this candidate further against the observed validation/holdout.
Preserve it for prospective confirmation. Move temporarily to the next distinct
research branch: time/margin interpretation or data/market collection.

### Future market boundary

Market comparison is restricted to races in 2025 through 15 August 2026. The
2023–24 history is rating-development data and is not a fair market showdown.
The ratings engine remains the primary product; the pricing engine will later
add current weight, barriers, course, map and other race-day information.

When timestamped prices exist, report a separately frozen wagering rule:

`bet only when model expected value is at least 15% versus the opening price`.

Report that rule against both opening and closing prices, including commission,
coverage and sample size. Do not alter the 15% threshold after seeing returns.

## Step 3 improvement branch — time and margins

Completed and frozen on 22 August 2026. The experiment isolated the existing
form-anchored margin signal from the separate durable-identity change by using
`performance-par-v1.0+identity-v1.0` as its research control. It also required
the complete candidate to beat accepted `performance-par-v1.0`.

Three pre-specified strengths were tested over the same 1,582 validation and
historical-holdout races:

| Margin strength | Validation vs identity | Holdout vs identity | Validation vs official | Holdout vs official |
| --- | ---: | ---: | ---: | ---: |
| 25% | -0.000588 | -0.001661 | +0.000665 | +0.000778 |
| 50% | -0.001101 | -0.003098 | +0.000152 | -0.000658 |
| 100% | -0.001904 | -0.005270 | -0.000651 | -0.002831 |

Negative log-loss deltas are improvements. The 25% blend conclusively added
information relative to the identity-only time control, but did not beat the
accepted baseline. The full blend beat the accepted baseline in both periods,
but its isolated validation interval included zero. No version satisfied both
requirements, so none was promoted.

Freeze the margin branch. Preserve the full form-anchored candidate for new-race
confirmation, but do not choose a new blend using the already observed results.
Proceed to the distinct pace/sectional branch.
