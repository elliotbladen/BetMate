# Expected Tempo Engine — Step 2 targets

Date: 3 September 2026
Status: Step 2 built; research/shadow only

## Delivered

`racing_engine/expected_tempo_targets.py` creates prior-only physical pace
pars and continuous early/middle/late targets. It also supplies a four-way
label (`slow`, `even`, `fast`, `very_fast_or_collapse`) and retains the more
detailed eight-way pace shape.

Physical pars use source, sectional phase semantics, track, exact distance,
going and rail. Cells require minimum depth and thin cells partially pool into
broader history. All races on one date are scored before that date is added to
history, preventing same-day and future leakage.

Race grade, class family and field size deliberately remain predictors. They
are not normalised out of the target because the engine needs to test findings
such as Group 1 races creating more pressure than Group 3 races.

## Output

- `reports/expected_tempo/expected_tempo_step2_targets.csv`
- `reports/expected_tempo/expected_tempo_step2_manifest.json`
- `tests/test_expected_tempo_targets.py`

The build scored 1,512 of 1,565 races. The first 53 lacked sufficient strictly
prior comparable history and remain unscored rather than receiving fabricated
pars.

Condition-adjusted four-way distributions:

- Good: 44.5% slow, 31.8% even, 9.8% fast, 13.9% very-fast/collapse.
- Soft: 43.2% slow, 28.3% even, 11.4% fast, 17.1% very-fast/collapse.
- Heavy: 48.1% slow, 30.4% even, 7.6% fast, 13.9% very-fast/collapse.

The initially observed Group signal survives the physical normalisation:
Group 1 fast plus very-fast/collapse is 40.3% (27/67), versus 25.0% (29/116)
for Group 3. This remains descriptive evidence, not yet an out-of-sample model
result.

## Safeguards and next step

- No horse rating or price is read or changed.
- No wind component is manufactured without course bearings.
- Production remains `form-first-v2.0`; this target layer is research-only.
- The source pace table currently ends 15 August 2026.

Step 3 is to train chronological baselines and challenger models using Step 1
features against these Step 2 targets, with meeting-grouped folds, calibration,
log loss, Brier score and continuous-score error.
