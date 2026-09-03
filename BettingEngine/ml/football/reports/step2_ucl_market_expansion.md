# UCL Step 2 — unified market outputs

The shared UCL engine now emits one coherent scoreline distribution and derives four market families from it: 1X2, Over/Under 2.5, Asian handicap -0.5 and the underlying expected-goal rates. The 1X2 probabilities are the calibrated Dixon-Coles/ClubElo blend; totals and handicap are derived from the same matrix, so markets cannot contradict each other.

Market calibration remains separate by market. This is deliberate: 1X2, totals and handicap have different margins and error shapes. The engine does not consume odds as model features. Closing prices are reserved for devigging benchmarks, calibration diagnostics and CLV tests.

The walk-forward output now records `p_over25`, `p_under25`, `p_ah_home` and `p_ah_away` alongside 1X2. The remaining Step 2 work is the two-season out-of-sample calibration run, which will be completed before market promotion.
