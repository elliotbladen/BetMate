# NRL halftime totals v2 — decision record

## Why the old model was rejected

The original totals output used only the combined halftime score and a five-bin
lookup for expected second-half points. Although the bins broadly matched the
historical regression-to-the-mean pattern, captured live statistics did not
affect the total. The user correctly rejected this as too simplistic.

## Data audit

- 754 historical NRL halftime rows exist for 2022–2026; 737 are valid for a
  second-half scoring target.
- The historical deep-stat columns (run metres, line breaks, errors,
  possession and territory) contain zero populated observations.
- On the 2026 holdout, the old lookup produced second-half MAE 8.235 and RMSE
  10.314. A continuous score-state regression produced MAE 8.196 and RMSE
  10.235: a small improvement, confirming halftime score alone is inadequate.

## Rebuild decision

Predict remaining (second-half) points and then add points already scored.

1. Historical score-state baseline trained on 2022–2025.
2. Pregame total retained as a scoring-strength/environment prior.
3. Live process layer uses combined pace and opportunity statistics, not team
   differentials intended for winner/margin prediction.
4. Process adjustment is capped and labelled provisional until deep-stat
   history is large enough for chronological calibration.
5. Produce a residual distribution so a quoted bookmaker line can be converted
   into an Over/Under probability and fair price.
6. Store components and feature coverage for later self-learning.

## Distribution correction after reversion study

The expected mean cannot be used as the betting line. Low-H1 NRL second-half
scores are right-skewed: for H1 totals 0–10 the mean was 27.27 but median 24.
The model now selects at least 40 pre-2026 matches near the current H1 total,
shifts that empirical distribution to the prior/process expected mean, smooths
it with a two-point kernel, and solves for the actual 50/50 line. Over/Under
prices come from that empirical CDF rather than a symmetric Normal assumption.

Repriced outputs:

- Manly–Dolphins: expected mean 35.19, fair 50/50 line 31.75 (n=45).
- Bulldogs–Rabbitohs: expected mean 35.33, fair 50/50 line 33.37 (n=68,
  partial reconstruction).

Research direction: NRL in-game models combine priors, score state and event
features; rugby-league EPV research supports possession location/outcome;
errors, penalties and forced repeat possession materially alter scoring chance.

## Last-night integrity rule

Manly–Dolphins has an exact archived halftime snapshot and can receive the full
v2 calculation. Bulldogs–Rabbitohs has only a reconstructed 0–10 score, so its
v2 result must fall back to score state plus the pregame prior and be labelled
partial. No post-halftime statistics may be passed off as halftime evidence.
