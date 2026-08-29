# NRL ML margin/H2H coherence correction — 2026-08-12

The first NRL shadow version independently trained a margin regressor and an
H2H classifier. Out of sample, they nominated different winners in 79 of 426
games (18.5%), and the classifier often assigned weak probabilities to large
predicted margins.

## Correction

- The XGBoost margin forecast remains the expected home scoring margin.
- The fair home handicap is the negative of that margin.
- Home-win probability is now calculated from the margin using the held-out
  margin residual scale saved in the versioned model bundle.
- The direct H2H classifier is retained in live output as a diagnostic
  challenger, but it no longer sets the official ML H2H price.
- Totals were not changed.

## Walk-forward evidence (2024–25, 426 games)

| H2H method | Accuracy | Brier | Log loss |
|---|---:|---:|---:|
| Independent classifier | 61.03% | 0.2316 | **0.6553** |
| Margin-derived | **62.68%** | **0.2313** | 0.6559 |

The live Round 24 repricing is in
`outputs/results/nrl_r24_ml_shadow_v2_2026-08-12.txt`.
