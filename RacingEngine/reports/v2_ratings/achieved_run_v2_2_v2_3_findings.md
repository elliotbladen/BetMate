# Corroborated and calibrated achieved-run candidates

Date: 28 August 2026  
Decisions: **V2.2 revise; V2.3 reject/revise; neither promoted**

## V2.2 independent corroboration

`achieved-run-v2.2-corroborated-shadow` retained the corrected race-condition
weight semantics and required a dominant breakout to be supported by either:

- a meeting-adjusted clock at least 0.5 historical MAD faster than the prior
  track/distance median; or
- hierarchical energy compensation at or above the pre-2025 winner 75th
  percentile (2.724).

The 886 energy training rows exclude Natural Fling, Gringotts and Sheza Alibi.
Only 25 breakout races received anchor relief and 44 dominant winners received
positive-margin evidence.

V2.2 passed elite Spearman (0.509), the 90-day broad cohort, and the
Gringotts/Sheza WFA audit. It failed Natural Fling: 83.53. Her meeting-adjusted
clock was only +0.145 fast MAD (threshold +0.5), and her energy compensation was
1.120 (threshold 2.724). The stored evidence does not independently corroborate
her breakout under the frozen definitions.

## V2.3 training-calibrated partial update

`achieved-run-v2.3-calibrated-shadow` replaced the binary zero/full fallback
with a coefficient fitted only on 1,022 pre-2025 examples and their following
90-day peak. The three named audit horses were excluded. A fixed 0.00–1.00 grid
selected **0.35**, with training MAE 7.4497 versus 7.5728 at zero and 7.6913 at
full relief.

Results:

- Natural Fling: **91.73**, still below the fixed 100–110 gate.
- Sheza Alibi: **116.44**; Gringotts: **112.57**.
- Frozen 90-day MAE: candidate 8.332, class-only 9.108, official 12.307.
- Frozen 365-day MAE: candidate 9.339, class-only 9.428, official 17.783.
- 180-day MAE narrowly misses class-only: 9.008 versus 8.972.
- Elite Spearman is 0.498, narrowly below the required 0.50.

## Conclusion

The broad evidence supports a bounded partial update, not the roughly 70%+
update required to force Natural Fling into range. Raising the coefficient for
one horse would contradict the training optimum and is prohibited.

The remaining Natural Fling gap is not a Horse Ability aggregation problem. It
requires better achieved-run evidence: a validated race/meeting time model,
more discriminating sectional energy decomposition, stronger opposition/race
strength evidence, or later point-in-time collateral confirmation. Until one of
those passes its independent gate, Base Run Figure, collateral promotion and
Horse Ability promotion remain blocked.
