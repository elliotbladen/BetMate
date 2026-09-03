# UCL totals rebuild progress

Using the newly downloaded free SofaScore event/statistics layer, we tested a leakage-safe isotonic calibration for Over/Under 2.5. The calibrator was fitted only on 1,494 matches before 2024/25 and evaluated on the 378 matches from 2024/25–2025/26.

- Raw Over probability: Brier 0.2440; mean probability 70.45%.
- Calibrated probability: Brier 0.2296; mean probability 57.83%.
- Actual Over rate: 65.87%.

The Brier improvement is meaningful, but the calibrated mean is now too conservative, showing that a single isotonic curve is not the final answer. The next iteration should use a beta/logistic calibrator with stage and xG-coverage indicators, then validate against complete closing totals.
