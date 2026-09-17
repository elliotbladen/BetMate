# EPL cards Step 5 — 2025/26 backtest

The selected calibrated GLM was evaluated on all 380 EPL matches from 2025/26. The
model and guardrails were frozen before this season; only the closing yellow-card
prices were joined afterwards.

The closing odds file is complete for all 380 matches. The model passed its referee
and probability guardrails on 361 matches. It selected the Over or Under side and
was evaluated at four minimum model-EV thresholds:

| minimum EV | bets | wins | official-result ROI | profit units |
|---:|---:|---:|---:|---:|
| 0% | 204 | 104 | **-5.34%** | -10.90 |
| 5% | 143 | 73 | **-0.46%** | -0.66 |
| 8% | 130 | 63 | **-3.67%** | -4.77 |
| 10% | 119 | 56 | **-5.17%** | -6.15 |

The official football-data settlement target is used for the primary result. Footiqo's
recorded yellow-card total differs on 22 fixtures. Using Footiqo's own totals changes
the 5% row to +1.11% ROI, but the 8% and 10% rows remain negative. That sensitivity is
too large to call the result proven.

The held-out probability calibration also deteriorated: predicted Over rate was 62.2%
against an actual 55.3%, with Brier 0.2511 and log loss 0.6956. The development
calibration therefore did not transfer cleanly to 2025/26.

Conclusion: this first EPL cards model does **not** establish a reliable betting edge
on the 2025/26 closing sample. The 5% official result is close to break-even, but the
higher thresholds lose and the provider disagreement prevents a stronger claim. No
live betting rule should be promoted from this backtest without resolving the result
source and recalibrating the model.
