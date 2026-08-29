# AFL halftime margin v3 activation and totals study

## Active margin correction

`scripts/halfTime_price_afl.py` now preserves the halftime margin and adds 61%
of pregame full-game margin as the fitted remaining-half strength component.
The 61% coefficient was stable at 59.7%–63.7% in leave-one-season-out folds on
874 matches from 2022–2026.

The same inside-50/clearance/clanger information is no longer allowed to change
an active regression weight and then be added again. The legacy regression is
retained only as a printed diagnostic. First-half accuracy continuation was set
to zero, consistent with the archive's near-zero H1-to-H2 relationship.

H2H now uses a calibrated 23.93-point remaining-margin residual SD instead of
the old simulation's roughly 11-point uncertainty. Handicap and H2H therefore
come from the same expected margin without materially overstating confidence.

Three targeted tests pass.

## Totals study

The 875-match leave-one-season-out study found the current five score-state bins
remain competitive: MAE 15.480 and RMSE 19.738. A compact score/shot/accuracy
ridge improved MAE by only 0.023 points. H1-to-H2 accuracy correlation was 0.003;
shot volume was more informative (+0.151) than H1 total (+0.111).

Recommendation: preserve the bins as baseline, but add NRL-v3-style pregame
prior, empirical distribution, deep-stat snapshots and market snapshots. Do not
claim calibrated O/U probabilities until those missing historical inputs have
been collected and evaluated out of sample.

## Totals v3 implementation

The recommendation was subsequently implemented in
`scripts/afl_ht_totals_v3.py` and activated through
`scripts/halfTime_price_afl.py`:

- the five bins remain the score-state baseline;
- 35% of the expected second-half pregame total is retained as a conservative
  forward-calibration prior;
- scoring-shot pace, combined inside-50 volume and clearance volume provide a
  coverage-shrunk live adjustment capped at four points;
- detected in-game injury total effects are applied once and capped;
- historical conditional H2 outcomes provide O/U probability and the median
  fair line separately from the expected mean;
- every output records model version, coverage, sample size and contributions.

The AFL collector now stores normalized and raw Squiggle snapshots plus live
odds at nominal 10/20/30 minutes and halftime. It also derives and stores the
Fox round match ID, allowing unattended halftime pricing to execute the existing
in-game injury detector rather than silently skipping it.

Seven totals/collector contract tests and three margin tests pass. The process
and pregame blend weights remain forward-calibration priors; the bins and
historical distribution are the historically supported layers.
