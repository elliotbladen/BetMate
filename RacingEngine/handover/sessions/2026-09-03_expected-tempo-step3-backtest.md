# Expected Tempo Engine — Step 3 backtest handover

Date: 3 September 2026

Step 3 is implemented in `racing_engine/expected_tempo_model.py`, with tests in
`tests/test_expected_tempo_model.py`. All nine Expected Tempo tests pass.

Artifacts:

- `reports/expected_tempo/expected_tempo_step3_oof_predictions.csv`
- `reports/expected_tempo/expected_tempo_step3_backtest.json`
- `reports/expected_tempo/expected_tempo_step3_findings.md`

There are 1,105 out-of-fold predictions across four expanding chronological
folds. The internally calibrated context/logistic blend has aggregate log loss
1.2343 versus 1.2373 for the context baseline, but it does not win all folds.
It remains shadow-only. Raw logistic (1.3750) and boosted tree (1.4496) fail
against the baseline. No continuous ML model wins early, middle and late pace
targets together.

Production horse ratings and prices remain untouched. Step 4 should implement
the causal after-each-race meeting updater and compare V0 pre-meeting forecasts
with V1/V2/etc forecasts using only earlier completed races on that card.
