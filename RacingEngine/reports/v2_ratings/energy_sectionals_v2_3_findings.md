# Step 2 V2.3 energy-sectionals findings

Date: 2026-08-23
Decision: promising frozen candidate; no accepted-rating integration; Step 3 blocked

## Seven tasks completed

1. Constructed full NSW 200m velocity curves and source-honest Victorian three-phase curves.
2. Built strictly prior, source/distance-band/going efficient profiles from previous winners.
3. Derived excess early energy, late deceleration, late burst and front-exposure signals.
4. Fitted sprint, middle and staying coefficients independently by NSW/Victoria with zero available.
5. Tested same-distance-band next starts and lower-cost subsequent pace setups.
6. Ran overall, jurisdiction, distance-band, elite and paired-uncertainty gates.
7. Froze rather than promoted because the complete gate did not pass.

## Coverage and coefficients

V2.3 covers 1,899 races and 18,923 runners. Sprint compensation fitted at `0.1` NSW and `0.4` Victoria. Middle compensation fitted at `0.0` NSW and `0.8` Victoria. Achievement survived only for NSW sprints at `0.1`. Staying was frozen at zero: only 13 NSW and zero Victorian pre-2025 training pairs met the curve rules.

## Holdout results

Compensation-only, 6,231 same-band next runs:

- MAE improved 8.31049 to 8.29719.
- NSW improved 8.33770 to 8.32842.
- Victoria improved 8.28653 to 8.26967.
- Sprint improved 8.31231 to 8.29762.
- Middle improved 8.31046 to 8.30057.
- Staying was unchanged at 8.17355 because its coefficient is zero.

Race ranking, 740 races:

- Log loss improved 2.49883 to 2.48824.
- NSW improved 2.51042 to 2.49788.
- Victoria improved 2.48876 to 2.47985.
- Sprint and middle both improved; staying was unchanged.

The paired 95% interval for race log-loss difference was `[-0.01418, -0.00701]`, a clear improvement. The next-start MAE difference was `-0.01331`, but its interval `[-0.03944, +0.01283]` crossed zero. The next-start benefit is therefore not yet statistically secure.

Horses with compensation >=1 that later encountered a lower-cost pace in the same distance band improved by 2.19 rating points on average across 2,100 pairs. This is an association, not a causal estimate.

## Elite and source sanity

The 2025 Queen Elizabeth correctly records Via Sistina as strong late-burst achievement (`+1.50`) with zero compensation. The 2024 Cox Plate cannot be scored: at 2040m the Victorian feed has one long opening segment followed by two 400m phases, which does not provide a genuine middle-third velocity. Interpolating it would manufacture detail. This blocks Victorian staying promotion.

## Decision and next Step 2 work

V2.3 is the best sectional candidate so far and establishes that energy compensation materially improves ranking. It is not promoted because staying is unsupported and next-start uncertainty crosses zero. Preserve the sprint/middle coefficients unchanged and forward-test them. To finish Step 2, obtain richer Victorian staying sectionals or define an independently validated two-phase staying model, then accumulate enough new same-band runs to tighten the next-start interval below zero.
