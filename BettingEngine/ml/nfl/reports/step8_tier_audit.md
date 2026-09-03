# NFL Step 8A — T2/T3 historical tier audit

## Decision

The historical evidence supports continuing T2 quarterback and T3 continuity
as separate live shadows. It does not support a hand-written injury-points table
or promotion to the official paper price.

The audit used 1,599 expanding-window test games from 2019–2024. Every fold was
trained only on earlier seasons. The sealed 2025 vault produced zero predictions
and was not used for fitting or scoring.

## Results

| Model | Margin MAE | Gain vs T1 | Seasons better than T1 | MAE to closing spread |
|---|---:|---:|---:|---:|
| T1 core | 10.309 | — | — | 2.844 |
| T1 + QB | 10.177 | +0.131 | 4/6 | 2.477 |
| T1 + injuries | 10.279 | +0.030 | 4/6 | 2.832 |
| T1 + full T2 | 10.166 | +0.142 | 5/6 | 2.518 |
| T1 + T3 continuity | 10.226 | +0.082 | **6/6** | 2.777 |
| T1 + T2 + T3 | **10.104** | **+0.204** | **6/6** | 2.524 |
| T1 + shuffled T2 | 10.333 | -0.024 | 3/6 | 2.954 |
| T1 + shuffled T3 | 10.328 | -0.019 | 2/6 | 2.891 |

The combined tier improved result MAE in every test season, but the gain ranged
from only 0.027 points in 2022 to 0.472 in 2023. It is real enough to continue
testing and too small to treat as established betting edge.

QB-only output tracks the closing spread better than the combined model. Adding
the simple injury burden moves the model farther from the close. That is a
warning against treating every listed absence equally or adding subjective
injury points.

## Data audit

Historical nflverse injury reports exist for 2014–2025. The 2014–2024 feeds have
`date_modified`; the 2025 feed does not. The development test ends in 2024, so
all tested injury records can be rejected when modified after the game date.

The reports still represent final weekly designations rather than a complete
hour-by-hour news timeline. Injuries are position-weighted but not weighted by a
pregame estimate of player value or expected snaps. Historical actual starters
also reveal who ultimately played; live T2 must instead use a timestamped
starter/backup probability mixture.

## Proposed live shadow structure — not yet frozen

- T2-QB: model-derived starter value minus backup value, multiplied by the
  timestamped probability that each player starts.
- T2-availability: retain as a reported diagnostic until pregame player value
  and expected-snap weighting are implemented. No generic injury points.
- T3-continuity: model-derived roster, offensive-line and receiver continuity;
  no manual narrative adjustment.
- Preserve T1, T1+QB, T1+T3 and T1+T2+T3 as separate frozen outputs so each
  family can be ablated prospectively.
- Keep all components shadow-only and staking disabled.

The next review should decide the live QB probability source and safety caps
before implementing 2026 adjustments.
