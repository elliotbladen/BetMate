# EPL cards Step 4 — calibration and guardrails

The development period was tested with rolling-origin predictions:

- Train 2022/23, validate 2023/24.
- Train 2022/23–2023/24, validate 2024/25.
- Keep 2025/26 untouched for Step 5.

The GLM beat the direct referee/team baseline on the two validation seasons:

| candidate | Brier | log loss |
|---|---:|---:|
| baseline | 0.2820 | 0.7600 |
| GLM | **0.2628** | **0.7212** |

Both candidates were underestimating the observed Over 3.5 rate, so a Platt logistic
calibration map was fitted on the 760 rolling-origin predictions. The calibrated GLM
was marginally better than the calibrated baseline (Brier 0.2389 vs 0.2396; log loss
0.6708 vs 0.6721). The GLM is therefore the selected candidate for Step 5.

The live guardrails are:

- referee must have at least 25 prior EPL matches;
- one side must have calibrated probability at least 57%;
- otherwise the match is no bet, regardless of the displayed fair price.

The held-out 2025/26 price file contains 361 eligible matches and 19 matches rejected
for a thin referee sample. This is a candidate list only; Step 5 still has to join the
2025/26 closing odds and evaluate calibration, CLV and ROI.
