# V2 Ratings Engine architecture

Status: active build from 23 August 2026.

## Product boundary

The Ratings Engine estimates completed-run quality and sustainable demonstrated
horse ability. It is expected to supply roughly 60–65% of the later Pricing
Engine, but contains no market probability, price, EV, bet or staking decision.

```text
official results / identity / profiles
                 |
                 v
Step 1: base Run Figure and Race Strength
  margins + weight + WFA + class/race standards
                 |
                 v
Step 2: historical pace and environment interpretation
  sectionals + pace shape + wind/rain + lane/rail + DT-W + stewards
                 |
                 v
Step 3: collateral form network
  later results revise earlier races; retrospective and PIT modes
                 |
                 v
Step 4: Sustainable Horse Ability
  overall + distance bands + early/middle/late/pressure traits + uncertainty
                 |
                 v
Step 5: historical counterfactual pace scenarios
  slow/even/fast/collapse/sprint-home scenario ratings and likelihoods
                 |
                 v
FROZEN RATINGS ENGINE
                 |
                 v
Step 6: separate Pricing Engine
  today's barrier/map/weather/pattern/etc -> calibrated prices -> market/EV test
```

## Historical environment timeline

One meeting-wide label is insufficient. Each completed race is joined to the
closest valid observations at its actual/scheduled start:

- wind speed, direction and gusts;
- rainfall over recent 10/30/60-minute windows;
- temperature and humidity;
- official going changes and observation time;
- rail position and course configuration;
- reported and observed lane use/pattern;
- source, timestamp, spatial distance and confidence.

Course geometry resolves wind into head/tail/crosswind for every sectional.
Runner position and path estimate exposure/drafting. A runner-wide, DT-W,
headwind and steward comment may describe one event and must be fused into one
workload residual rather than counted repeatedly.

## Sectional outputs

Every race stores continuous early/middle/late pressure, acceleration,
deceleration, leader pressure, field compression and collapse/sprint-home
scores. Human labels are presentation only. Every runner stores early
contribution, mid-race workload, late strength, pressure absorbed, pace
advantage/disadvantage and data confidence.

Sectionals cannot set absolute Race Strength alone. They modify margin
reliability, provide bounded workload/trip residuals and create repeatable
sectional ability traits. Raw, adjusted and counterfactual values remain
separate and fully attributable.

## Counterfactual contract

The engine may report that a horse becomes the most likely winner under an
alternative plausible pace, with scenario rating, probability and uncertainty.
It must never claim certainty that the horse would have won. Counterfactuals
are validated on held-out natural rematches and different observed pace regimes.

## Gates and rollback

Each step persists a new version and a before/after movement ledger. Required
checks include identities/clocks, official classifications, named elite races,
pace archetypes, missing-data neutrality, one-anchor deletion, bounded
collateral revisions, chronological leakage and baseline comparisons. A failed
candidate is frozen; accepted upstream data and ratings are not rebuilt or
silently altered to rescue it.
# Step 2 validated shadow boundary (2026-08-23)

`pace-shape-v2.1-pit-shadow` uses only races before the race being rated to construct sectional pars. Its outputs remain context annotations and never overwrite `v2_run_performances`. Environment adjustments require both a timestamped observation and defensible sectional geometry. Official steward path evidence is separate from lane bias; neither winner locations nor barrier outcomes may manufacture a lane measurement. Named source gaps live in `v2_sectional_data_gaps` and are not imputed.

The frozen evaluation is `reports/v2_ratings/pace_shape_v2_1_evaluation.json`. Promotion requires improvement overall and independently in NSW and Victoria without harming elite-run sanity checks. V2.1 failed that rule.
# Step 2 project lock

Step 3 must not begin until a sectional candidate improves next-start MAE and race-ranking log loss overall, in NSW, and in Victoria. V2.2 separates `achievement_signal`, `trip_signal`, and `steward_signal` in `v2_runner_sectional_components`. All are shadow-only. A fitted zero is retained as evidence that a component adds no validated predictive value; it is never overridden by judgement.

V2.2 is frozen after failing the jurisdiction gate. V2.3 must use distance-specific energy-efficiency curves and preserve V2.2 as its fixed comparator.
# V2.3 energy-sectional boundary

`v2_runner_energy_sectionals` stores source-honest velocity profiles, optimal prior-only ratios, energy cost, late deceleration, burst ability and front exposure. NSW uses 200m observations. Victoria uses only its observed three segments. Distance-band histories and coefficients are separate. Groups with fewer than 50 training pairs are forced to zero.

## Step 2 promotion lock — 23 August 2026

Step 2 remains locked. The frozen sprint/middle candidate is recorded in the
append-only `v2_sectional_forward_ledger`; coefficients are hashed and cannot
be refitted using the holdout. Its first unseen card is 22 August 2026, after
the 15 August training cutoff but before the candidate was formally frozen, so
it is labelled a prospective-style holdout rather than a live post-freeze test.

Victorian staying races remain shadow-only. A source-honest opening/final-400
fallback excludes the unobserved middle phase. It improved point estimates but
failed both paired 95% confidence gates. Official Racing.com material confirms
richer 200m split/cumulative data exists; resolving and backfilling that feed is
preferred to treating three aggregate phases as complete evidence.

## V2.4/V2.5 recovery boundary — 23 August 2026

The official Racing.com GraphQL sectional structure is now the primary
Victorian evidence path. `v2_vic_200m_sectionals` preserves every individual
split, actual position at the marker, payload hash and source URL while official
V2 results continue to own horse identity. Coverage is 1,330/1,341 historical
races, 13,919 matched runners and 106,249 segments.

V2.4 uses the richer intervals with source/band/going pars. V2.5 is a separately
versioned experiment using track-distance-going pars with a broader source-band
fallback. Neither changes accepted ratings. Promotion is governed by
`config/sectional_promotion_protocol_v2.json`; directional improvements alone
are insufficient.

The next candidate must separate three products: observed run achievement,
compensation for inefficient energy/trip, and a persistent pace-style trait.
Latent ability should be evaluated against multiple later neutral runs rather
than requiring one noisy next start to fully express the recovered energy.
Expected race-shape matching remains an eventual pricing-engine input and must
not be leaked into the historical rating.

### Current build boundary

As of 23 August 2026, the ratings build is deliberately paused until next week
inside Step 2. Step 2 is unfinished and Step 3 is architecturally locked. The
resume sequence is: append immutable forward evidence, score newly observable
next starts, implement V2.6 target decomposition, and rerun
`sectional-promotion-protocol-v2.0`. No V2.4/V2.5 refit is permitted against the
held-out August 22 races.

### Expert breakout audit

Promotion also requires a named breakout-horse plausibility report. Natural
Fling's 15 August 2026 Caulfield Group 3 win is the first case. Its mandatory
achieved-performance acceptance range is **100-110** on this engine's scale,
reflecting a four-length defeat of Listed/Group-quality opposition and expected
Group 2/3 competitiveness. This band is never used as a fitted target: the
engine must reach it from independent time, variant, margin, WFA, sectional and
collateral evidence. A figure outside the band blocks promotion and triggers an
architecture review. In particular, a dominant winner must receive positive
performance evidence; it is insufficient merely to downgrade beaten runners.

### Future ability architecture

Early Group-horse detection is part of the ratings engine. The state model must
keep achieved performance, current latent ability and future development
separate. Each horse state carries a posterior mean, uncertainty and pace-style
vector. Exact age, sex and starts influence its transition distribution—not the
already completed run figure. Independent time, variant, WFA, margin and
sectional evidence may move a lightly raced horse rapidly away from a stale
official-rating prior.

The breakout evaluator is point-in-time and cohort based. It freezes every
candidate at the flag date, evaluates later peak rating and Listed/Group results
at 90/180/365 days, and reports calibration, false positives and lead time as
well as successful discoveries. Individual-race effects are removed before
updating persistent ability. See `docs/future_group_horse_research.md` for the
research basis, cohort definition, gates and grey areas.

V2.3 is frozen despite consistent ranking improvement because next-start uncertainty includes zero and Victorian staying resolution is inadequate. Step 3 remains blocked. No consumer may join V2.3 into accepted ratings until those gates are resolved.
