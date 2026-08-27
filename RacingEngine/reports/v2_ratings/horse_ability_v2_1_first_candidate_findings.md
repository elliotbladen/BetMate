# Horse Ability V2.1 — first controlled candidate

Date: 28 August 2026  
Candidate: `horse-ability-v2.1-sustainable-recency-shadow`  
Accepted run input: `form-first-v2.0`  
Decision: **BLOCKED_UPSTREAM**

## What was built

The first point-in-time Horse Ability state uses only prior accepted V2 run
performances. It applies a fixed six-run window, 180-day recency half-life,
bounded 35% sustainable-peak blend, reliability shrinkage toward 100 and robust
uncertainty. Same-day results are excluded. No barrier, map, market, weather,
jockey, trainer or current-race input enters the state.

Only probability temperature was fitted, using the frozen training period. The
state formula was not tuned against validation or holdout. Weight/WFA semantics
were deliberately not altered inside this candidate.

The build materialises auditable pre-race rows in
`v2_horse_ability_states`. The full machine-readable evaluation is
`horse_ability_v2_1_first_candidate.json`.

## Chronological evidence

All models were evaluated on identical races and runner sets.

| Period | Races | Candidate log loss | Rejected V2 | V1 | Uniform |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 979 | 2.34224 | 2.36392 | 2.33577 | 2.33737 |
| Validation | 876 | 2.33415 | 2.34724 | 2.33322 | 2.34001 |
| Historical holdout | 835 | 2.32806 | 2.32679 | 2.33492 | 2.34077 |
| Observed 22 August diagnostic | 19 | 2.25218 | 2.27825 | 2.27756 | 2.24948 |

The candidate materially improves the rejected V2 state in validation
(`-0.01308` log loss; 95% interval `[-0.02016, -0.00629]`). It beats uniform
directionally in validation and conclusively in historical holdout. It beats V1
in historical holdout, but misses V1 by `+0.00094` in validation and that paired
interval includes no improvement. It also narrowly loses to the rejected V2
state in historical holdout. Therefore it cannot be promoted.

The 22 August period is diagnostic only. Its outcomes were already observed
before this candidate was specified and it is not an untouched prospective
holdout.

All three rating models selected the maximum tested training temperature of 60.
That is evidence that early-history ratings are too dispersed/noisy, especially
when many horses have little prior V2 evidence. The next state candidate must
address history-depth/uncertainty calibration explicitly rather than merely
extending the temperature range or tuning the peak blend on observed holdouts.

## Current named states

| Horse | Ability | Recency | Sustainable peak | Uncertainty | Rated runs |
| --- | ---: | ---: | ---: | ---: | ---: |
| Gringotts | 115.20 | 115.94 | 118.40 | 3.09 | 19 |
| Autumn Glow | 114.56 | 115.57 | 119.07 | 3.94 | 13 |
| Sheza Alibi | 105.27 | 103.21 | 113.40 | 10.47 | 7 |
| Natural Fling | 89.60 | 79.42 | 78.47 | 9.60 | 2 |

These remain shadow states and are not signed-off Horse Ability ratings.

## Mandatory upstream failure

Natural Fling's 15 August 2026 Caulfield Group 3 win is the predeclared breakout
audit. Its accepted achieved-performance range is 100–110. The current V2 run
figure is only `83.53`, so Horse Ability promotion is blocked regardless of the
aggregate metrics.

The stored components explain the failure:

- official handicap rating: 71;
- collateral anchor: 78.17;
- collateral weight: 80%;
- Group 3 class standard: 105;
- resulting race strength/performance: 83.53;
- winning margin: four lengths;
- winner margin component: zero.

The current run model intentionally sets every winner's beaten margin to zero.
That prevents a dominant win from providing positive performance evidence. It
also lets stale low official/prior ratings dominate a lightly raced improver.
This is exactly the failure anticipated by the breakout architecture.

The Sheza Alibi/Gringotts audit identifies a second semantic issue: all carried
weight differences are reversed mechanically, without separating handicap
burden from WFA, age or sex allowance. That question must be solved as a
separate run-interpretation family rather than hidden in current-state weights.

## Required recovery sequence

1. Preserve `form-first-v2.0` and this V2.1 candidate for forensic comparison.
2. Register a new achieved-run candidate that adds independently bounded
   winning-margin evidence and reduces stale-prior authority for lightly raced,
   corroborated improvers. It must solve a frozen historical cohort, not only
   Natural Fling.
3. Register handicap/WFA/age/sex weight semantics separately. Re-audit Sheza
   Alibi versus Gringotts and all corresponding race-condition cohorts.
4. Require the elite official-classification gate, Natural Fling 100–110 gate,
   chronological ranking, jurisdiction and false-breakout tests to pass before
   using the recovered run figures in Horse Ability V2.1.
5. Then test the next Horse Ability state family: uncertainty/history-depth
   calibration first, followed separately by campaign/layoff and
   distance/going suitability.

No pricing or game-day implementation is authorised by this result.
