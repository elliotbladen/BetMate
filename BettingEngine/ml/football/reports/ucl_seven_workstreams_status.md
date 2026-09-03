# UCL seven-workstream rebuild status

All seven workstreams have been executed as far as the free data permits:

1. Fixture identity/date repair: 342/378 modern matches mapped; 36 quarantined.
2. Rolling pre-match features: 1,997 chronological rows and 544 rolling feature columns generated.
3. Unified totals distribution: Dixon-Coles/ClubElo scoreline pricing retained as the coherent base.
4. Calibration: leakage-safe isotonic candidate reduced recent two-season Brier from 0.2440 to 0.2296; beta/stage-aware calibration remains the next challenger.
5. Closing totals: 2025/26 public closing totals tested; 2024/25 totals archive still incomplete.
6. Challenger comparison: raw versus calibrated outputs are archived; no challenger is promoted until both seasons have comparable closing markets.
7. Promotion gate: model remains paper-only pending complete xG/odds coverage and stable CLV.

The rolling feature file is `data/ucl/xg/ucl_rolling_prematch_features.csv`. No future match result is used in a row's pre-match rolling features.
