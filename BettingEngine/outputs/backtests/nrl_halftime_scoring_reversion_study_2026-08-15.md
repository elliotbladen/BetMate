# NRL halftime scoring reversion study — 2026-08-15

## Sample

- NRL: 737 valid matches, 2022–2026.
- AFL comparison: 875 valid matches, 2022–2026.
- Target: combined points scored after halftime.
- No historical live totals lines are present, so this is a scoring-distribution
  study, not a bookmaker ROI backtest.

## NRL findings

- League first-half average: 22.90; second-half average: 23.47.
- Correlation between first- and second-half totals: -0.182.
- Linear slope: each additional first-half point predicts 0.254 fewer
  second-half points.
- Bottom-decile first halves (12 or fewer): n=87, average H1 9.70, average H2
  27.98. H2 uplift versus league H2 average: +4.51 points, bootstrap 95% CI
  +2.31 to +6.90.
- H1 totals of 0–10: n=49, average H1 7.92, average H2 27.27, but median H2
  only 24 and SD 10.83.
- Restricting to 2023–2025: n=46 low halves, average H2 27.41, uplift +3.90,
  Welch p=0.017.

## Critical betting-line distinction

For H1 totals of 0–10, using 26 as the second-half fair number:

- actual H2 below 26: 53.1%;
- above 26: 42.9%;
- exactly 26: 4.1%;
- mean actual H2: 27.27.

The mean is above 26 while a majority land below 26 because the distribution is
right-skewed. A small number of second-half scoring explosions lift the expected
points value. Therefore expected total (mean) and a 50/50 betting line (median)
must not be treated as the same number, and a symmetric Normal distribution is
not suitable in this low-H1 state.

## AFL comparison

- AFL first-half average: 82.60; second-half average: 84.94.
- H1/H2 correlation: +0.111; slope +0.117.
- Bottom-decile first halves: average H2 82.19, which is 2.75 below the league
  H2 average; bootstrap 95% CI -7.42 to +2.07.

Thus this sample shows stronger mean reversion in NRL, not AFL. AFL low scoring
is more persistent. However, NRL low-half outcomes are sufficiently skewed that
an Under can still win more often than an expected-mean forecast suggests.

## Model consequence

The v2 process/prior mean remains useful as an expected-points forecast, but it
must not be published directly as the fair betting line. Replace the Normal
probability layer with an empirical or negative-binomial predictive
distribution, publish mean and median separately, and calculate Over/Under fair
odds from the empirical CDF. Historical live market lines are still required to
test ROI and market calibration.
