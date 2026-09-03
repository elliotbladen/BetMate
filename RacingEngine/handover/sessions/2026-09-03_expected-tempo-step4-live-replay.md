# Expected Tempo Engine — Step 4 handover

Date: 3 September 2026

Step 4 is implemented in `racing_engine/expected_tempo_live.py`, with causal
tests in `tests/test_expected_tempo_live.py`. All 12 Expected Tempo tests pass.

Artifacts:

- `reports/expected_tempo/expected_tempo_step4_live_replay.csv`
- `reports/expected_tempo/expected_tempo_step4_evaluation.json`
- `reports/expected_tempo/expected_tempo_step4_findings.md`

The historical replay has 872 out-of-fold races and 738 live-eligible races.
The safe probability blend records log loss 1.2298 versus 1.2334 for V0, but
does not win every period and remains shadow-only. Full live replacement fails.

Live continuous forecasts improve middle MAE by 12.18% and late MAE by 13.69%,
but worsen early MAE by 2.18%. Step 5 should therefore keep V0 early pressure,
cap all probability movement, and initially permit live changes only to middle
and late pace expectations after minimum evidence/confidence gates.

No horse ratings, horse prices, bets or production models were changed.
