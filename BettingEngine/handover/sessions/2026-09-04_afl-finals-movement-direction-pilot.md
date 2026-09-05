# AFL finals market-movement direction pilot

Date: 4 September 2026
Status: shadow-only small-sample experiment

## Objective

Forecast whether AFL handicap and total lines will finish numerically higher,
lower or without a material move at close. Exact closing-line prediction is not
the initial goal; the research question is whether direction accuracy can beat
50% over time on honest unseen matches.

## Four implemented layers

1. Shrunk prior/momentum baseline.
2. Regularised multinomial logistic regression.
3. Shallow histogram gradient-boosted tree.
4. Probability blend whose weights are chosen on a calibration period only.

Handicap and totals are trained, calibrated and evaluated independently. A
material move is fixed at 1.5 points. All matches from one date remain in the
same chronological partition. Rolling team and matchup features use only
earlier completed market paths.

## Inputs and limitation

The current Windows checkout contains the canonical AusSportsBetting workbook
with opening and closing markets. The pilot defaults to matches from 1 June 2026
onward. The previously collected dense intraweek snapshot database is not in
this checkout. The schema already accepts `current_line` and
`move_since_open`; populate those fields after the dense archive is recovered.

The September finals Sportsbet CSV is treated as a prospective shadow card and
is never included in model fitting.

## First chronological result

The three-month build contained 103 matches. The untouched test segment was 27
matches from 2–29 August 2026.

- Handicap blend: 48.1% three-class accuracy and 55.6% accuracy on matches that
  moved at least 1.5 points. It did not beat 50% across all calls.
- Handicap baseline: 29.6% overall; logistic 33.3%; shallow tree 48.1%.
- Totals baseline: 66.7% overall, but only 35.3% on material moves. Much of its
  apparent success was correctly calling no material move.
- Totals blend: 44.4% overall and 41.2% on material moves. It failed.

The correct conclusion is not that AFL movement is solved. There is a weak
handicap-direction signal worth prospectively tracking, a useful totals
no-move baseline, and no validated totals directional ML edge yet. Recovery of
the dense intermediate snapshots is the most important next data improvement.

## Files

- `scripts/line_mover/afl_movement_direction.py`
- `tests/test_afl_movement_direction.py`
- `data/line_movement/models/afl_direction_pilot.joblib`
- `outputs/line_movement/afl_direction_pilot_backtest.json`
- `data/line_movement/predictions/afl_finals_direction_shadow.json`

No forecast from this experiment may create a bet, change a price or increase a
stake. It is an execution-timing shadow only.
