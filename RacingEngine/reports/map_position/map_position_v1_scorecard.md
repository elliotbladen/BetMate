# Map Position Indicator V1 — First Shadow Scorecard

Date: 4 September 2026

## Build result

- Canonical early-time recovery version: `canonical-sectionals-v1.1-early-recovery`
- Map version: `map-position-shadow-v1`
- Historical runner rows: 43,721
- Runners with an observed map-position label: 37,713
- Full RacingEngine test suite: 168 passed, 1 skipped
- Production pricing/rating impact: none

## Early-time recovery

The provenance-checked `official finish time - complete final-800m chain`
derivation recovered early-to-800 values for:

- 14,426 `racing-com-nsw-authorised-v2` runners;
- 8,662 `rnsw-authorised` runners; and
- 14,149 Victorian aggregate-source runners retained from their directly
  supplied opening phase.

Total current early-to-800 coverage is 37,237 of 43,721 canonical runner rows.
The 3,523 results-fallback rows remain unsupported and were not imputed.

## First chronological diagnostic

| Metric | Map V1 | Population baseline | Passed? |
|---|---:|---:|---|
| Multiclass log loss | 1.30154 | 1.26434 | No |
| Multiclass Brier score | 0.17713 | 0.17262 | No |
| Top-state accuracy | 28.37% | n/a | Descriptive only |

The first empirical horse-history model fails promotion. This is a useful
negative result: the storage, point-in-time labels and constrained simulator
work, but the probability model requires distance/track/going conditioning,
better identity pooling, stable/jockey effects, pre-race tactics and verified
geometry before another frozen evaluation.

## Governance

Status remains `SHADOW_ONLY_DIAGNOSTIC`. No output may alter accepted ratings,
horse prices, EV, bet selection or staking.
