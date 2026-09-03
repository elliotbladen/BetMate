# UCL Step 5 — final two-season backtest

The final walk-forward test covers the two most recent completed seasons: 378 matches across 2024/25 and 2025/26. The model was refit chronologically before each match; no odds were used as features.

## Match probabilities

- **1X2 combined:** accuracy 54.76%, Brier 0.5786, RPS 0.2221, log loss 0.9699.
- **Over 2.5 combined:** accuracy 62.17%, Brier 0.2429. Mean model probability was 70.75% against a 65.87% actual rate, confirming overconfidence.

## Closing-price coverage

Usable public closing 1X2 prices were available for 171 matches in 2024/25 and 189 in 2025/26. Edge-band ROI is recorded in `ucl_recent_two_season_stack_backtest.json`; the combined 10%+ result was +2.20% ROI, while 30%+ and 50%+ edges were negative. U/O 2.5 closing coverage is currently complete only for 2025/26, so it is not a valid two-season ROI test yet.

## Decision

The model remains paper-only. The two-season evidence supports using 1X2 as the baseline audit market, but requires true xG, historical UEFA priors, totals calibration and complete two-season closing-market coverage before live promotion.
