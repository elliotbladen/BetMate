# NFL Step 8E — T4A venue audit

## Decision

Venue context is rejected as a margin adjustment and retained as a totals-only
shadow diagnostic. Travel remains untested because the current historical store
does not contain team/stadium coordinates or travel distance.

The expanding-window audit covered 1,599 games from 2019–2024. Features were
neutral site, roof state, grass/artificial surface and each team's logarithmic
number of prior games at the stadium. Stadium familiarity was calculated before
the current game updated the count. The 2025 vault was not used.

## Results

| Target | T1 MAE | T1 + T4A MAE | Gain | Better seasons | Shuffled MAE |
|---|---:|---:|---:|---:|---:|
| Margin | 10.309 | 10.314 | -0.005 | 3/6 | 10.317 |
| Total | 10.767 | 10.707 | +0.060 | 5/6 | 10.781 |

Venue context slightly worsened margin prediction and therefore receives no
side points. It improved final-score total MAE by 0.060 points and beat T1 in
five seasons, while shuffled venue data worsened the baseline. The gain is
small but directionally credible.

Against closing market numbers, T4A moved the margin model 0.008 points closer
but moved the total model 0.102 points farther away. This suggests the closing
total already contains venue information efficiently, or our venue signal is
useful for scoring but not yet calibrated to market pricing.

## Coverage and restrictions

- Stadium, home/neutral designation and roof: 100%.
- Surface: 98.6%.
- Historical travel distance, coordinates and body-clock difference: absent.
- Recorded temperature and wind are postgame observations and are excluded from
  this pregame tier.
- No manual home-field, dome, grass or international-game points are authorised.
- T4A is totals-only shadow research; it cannot change T1 or enable a bet.

T4B should only be built after adding a versioned venue/team geography table.
