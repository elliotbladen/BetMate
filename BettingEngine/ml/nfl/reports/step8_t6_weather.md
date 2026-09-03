# NFL Step 8G — T6 observed-weather oracle

## Decision

Weather is worth implementing as a timestamped totals-only live shadow. It is
not authorised to adjust the official total or create a bet.

The historical study used observed temperature and wind from the schedule. That
information has no archived forecast timestamp, so it is an oracle ceiling: it
tests whether weather can matter, not whether we could have known it at our
decision time.

## Results

| Model | Total MAE | Gain vs T1 | Better seasons | MAE to closing total |
|---|---:|---:|---:|---:|
| T1 core | 10.767 | — | — | 2.686 |
| T1 + observed weather | 10.724 | +0.043 | 4/6 | 2.736 |
| T1 + shuffled weather | 10.841 | -0.074 | 1/6 | 2.807 |

Real observed weather improved final-score prediction and strongly beat its
shuffled control. The gain was small and inconsistent across seasons. It also
moved the structural model farther from the closing total, meaning this study
does not demonstrate an unpriced market edge.

## Features and coverage

The oracle tested open-air status, weather availability, wind speed, nonlinear
wind thresholds, temperature deviation, freezing conditions and high heat.
Dome weather was correctly excluded. From 2019–2024, 1,111 games were open-air
and 86.0% had usable observed weather.

## Operating rule

- T6 applies to totals only.
- Live use requires a timestamped forecast captured before the model cutoff.
- Forecast age, provider, target time and stadium coordinates are mandatory.
- Multiple forecast horizons must remain distinct so later forecasts cannot
  overwrite earlier frozen predictions.
- Missing forecasts trigger an unresolved shadow, not calm-weather defaults.
- No live point cap or promotion is authorised yet.
