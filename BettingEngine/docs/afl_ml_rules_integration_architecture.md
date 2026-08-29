# AFL rules + ML integration architecture

## Decision

Do not splice XGBoost features or its raw margin directly into the tier arithmetic.
Treat the rules engine, ML model and bookmaker market as independent probability
forecasters, then combine their frozen outputs in a small, auditable ensemble.

The first production candidate is a 50/50 blend of the rules and ML home-win
probabilities. It is a candidate—not yet the official price—until the prospective
sample and uncertainty gates below are satisfied.

## Data flow

1. Freeze a pre-game record containing input timestamps, rules probability,
   legacy ML probability, current-shadow ML probability, no-vig market probability,
   prices, data-health flags and model versions.
2. Produce each forecast independently. A missing market input remains missing.
3. Combine probabilities, initially with a fixed convex blend. Never average odds.
4. Calibrate the combined probability using predictions from earlier rounds only.
5. Compare the calibrated probability with the current no-vig market probability.
6. Apply abstention, staking and data-health rules after prediction—not inside the
   probability model.
7. After settlement, append outcomes, closing prices, CLV and scoring-rule errors.

## Candidate progression

### Stage A: fixed convex blend

`p = w_rules * p_rules + w_ml * p_ml`, with non-negative weights summing to one.
This has one degree of freedom and is appropriate for the current small archive.

### Stage B: regularised log-odds stacker

After enough frozen observations exist, fit a logistic meta-model on:

- logit of rules probability;
- logit of ML probability;
- logit of genuine opening/current market probability;
- absolute rules–ML logit disagreement;
- data-health indicators and model-version indicators.

Every training prediction must be out-of-sample and every validation fold must
move forward in time. Model changes create new version strata; they must not be
silently pooled as though they were one forecast system.

### Stage C: calibration

Use sigmoid calibration first because the sample is small. Isotonic calibration
is allowed only after a substantially larger, independent calibration set exists.
The calibrator is trained on earlier rounds and evaluated on later rounds.

## Safety gates

- No automatic bet when rules and ML differ by 20 probability points or more.
- No automatic bet when required injury/team/weather inputs are stale.
- No market-aware forecast when bookmaker input is missing.
- Use the closing market only for evaluation; use the timestamped available market
  at decision time for a live recommendation.
- Promote an ensemble only if it improves Brier and log loss prospectively, its
  round-cluster uncertainty interval excludes no improvement, and ROI/CLV remains
  positive across thresholds and model-version periods.
- Continue logging every game, including abstentions, to prevent selection bias.

## Current evidence

The reproducible test is `scripts/backtest_afl_rules_ml_integration.py`. The frozen
archive currently provides 81 settled games over 10 rounds; Round 20 is absent and
Round 22 outcomes are not yet present in the historical workbook. The 50/50 blend
is the best simple candidate, but its round-bootstrap interval still crosses zero.
Therefore it should remain shadow-only for now.
