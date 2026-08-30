# NFL Step 4 — Independent challenger and calibration

## Result

The independent shallow-tree challenger was tested on 1,599 rolling-origin
games from 2019–2024. It consumed point-in-time team features only: no tier
outputs, betting prices or future results entered the feature matrix. The 2025
vault remained untouched and official prices were not changed.

| Margin predictor | MAE | RMSE |
|---|---:|---:|
| Ridge | 10.309 | **13.260** |
| Shallow tree | **10.294** | 13.291 |
| Closing spread | 9.834 | 12.794 |

The tree improves MAE by only 0.015 points while worsening RMSE by 0.031. That is
not a meaningful or stable promotion result. It remains an independent shadow.

| Total predictor | MAE | RMSE |
|---|---:|---:|
| Shallow tree | 10.785 | 13.614 |
| Closing total | 10.347 | 13.060 |

The challenger total does not beat the market.

## Head-to-head calibration

| Probability source | Brier | Log loss | Accuracy |
|---|---:|---:|---:|
| Margin-derived | **0.2250** | **0.6413** | **65.29%** |
| Direct calibrated classifier | 0.2260 | 0.6447 | 64.23% |
| Closing market | 0.2106 | 0.6088 | 66.96% |

Margin-derived H2H wins all three internal comparisons against the direct head,
so it remains authoritative. Calibration parameters were learned from the
season immediately before each test fold. The market remains the strongest
reference.

## Decision

- Do not promote the shallow tree.
- Do not activate the direct H2H classifier.
- Do not blend structural and ML prices.
- Continue frozen prospective collection through at least 500 predictions.
- Preserve the challenger as an independent disagreement signal.

Artefacts: `ml/nfl/challenger.py`,
`data/nfl/predictions/step4_challenger.csv`, and
`ml/nfl/reports/step4_challenger.json`.
