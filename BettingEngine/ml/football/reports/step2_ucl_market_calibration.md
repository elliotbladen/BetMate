# UCL Step 2 — calibration completion

Step 2 has been completed for the current two-season validation window (2024/25 and 2025/26, 378 walk-forward matches). The common scoreline engine now exposes 1X2, Over/Under 2.5 and Asian handicap -0.5, and each market has a separate calibration audit.

Combined results:

- 1X2: Brier 0.5786, log loss 0.9699, accuracy 54.76%.
- Over 2.5: Brier 0.2429, log loss 0.7043; mean model probability 70.75% versus 65.87% actual, showing overconfidence.
- Asian handicap -0.5 (home): Brier 0.2385.

The model is therefore paper-only. The totals output requires probability shrinkage/calibration before promotion, and all markets still require time-matched closing-line CLV validation. No odds were used as model features.
