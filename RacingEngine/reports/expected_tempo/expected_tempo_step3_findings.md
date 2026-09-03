# Expected Tempo Engine — Step 3 findings

Date: 3 September 2026
Status: shadow research; no production promotion

## Backtest design

The backtest uses four expanding chronological folds beginning 1 September
2024. Every meeting/date remains wholly on one side of a split. It produces
1,105 genuine out-of-fold race predictions from 1,512 usable races.

Compared models:

- global historical class prior;
- context baseline using state, distance band, going and Group grade;
- regularised multinomial logistic regression;
- histogram gradient-boosted trees;
- an internally calibrated blend of the context baseline and logistic model.

The blend weight is selected using only the final 20% of each training window.
The outer test period is never used to choose it.

## Four-way tempo classification

| Model | Log loss | Brier | Accuracy | Calibration ECE |
|---|---:|---:|---:|---:|
| Global prior | 1.2398 | 0.6786 | 43.71% | 0.0069 |
| Context baseline | 1.2373 | 0.6744 | 43.35% | 0.0179 |
| Calibrated logistic blend | **1.2343** | **0.6726** | 43.26% | 0.0389 |
| Raw logistic | 1.3750 | 0.7293 | 41.09% | 0.1420 |
| Raw boosted tree | 1.4496 | 0.7603 | 41.00% | 0.2084 |

Lower log loss, Brier and ECE are better. The calibrated blend improves log
loss by only 0.24% versus the context baseline and Brier by 0.28%. It lost in
the first fold, equalled the baseline in the second, then won in folds three
and four. That is promising but not robust enough for promotion.

## Continuous pace scores

No ML model wins all early, middle and late targets. The context baseline gives
the best early-score MAE (1.1273 versus 1.1485 global), while the global mean
remains best for middle (1.0863) and late (1.0591). Raw boosted and ridge
models do not justify adoption.

## Exploratory drivers

On the final fold, boosted-tree permutation importance ranks distance first,
followed by calendar month, going, prior-profile coverage and wind speed. Rail
and field size contribute smaller signals. These are diagnostic only because
the boosted model itself underperforms. Group grade does not yet show stable
enough incremental importance across the full model despite the descriptive
Group 1 pattern from Step 2.

## Decision

- Keep the context baseline as the stable benchmark.
- Retain the calibrated blend as a shadow challenger only.
- Reject raw logistic and boosted-tree predictions for live use.
- Do not update horse ratings or prices.
- Step 4 should test whether completed races within the current meeting add
  information beyond this pre-meeting baseline, using only races already run.

The most likely route to improvement is better field-map coverage and genuine
prospective weather/rail snapshots, not greater model complexity.
