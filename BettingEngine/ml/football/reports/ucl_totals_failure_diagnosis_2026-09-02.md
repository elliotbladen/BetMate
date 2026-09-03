# UCL totals failure diagnosis

## Where the current model is going wrong

1. **Probability generation and betting calibration are being conflated.** A score model can rank matches well while still outputting probabilities that are too extreme. Our 70.45% mean Over probability versus a 65.87% actual rate is classic tail overconfidence.
2. **The xG sample is mixed and provider-dependent.** Only 342/378 recent matches have SofaScore xG; older training rows are goals fallback. Provider xG and goals are not interchangeable observations of the same target.
3. **We are fitting a match model to a market that prices more information.** Closing totals incorporate lineups, weather, injuries, tactical news and bookmaker aggregation. Research on market-calibrated football models finds market calibration can dominate the choice of underlying goal-process model. [Clegg, Song & Cartlidge](https://arxiv.org/abs/2605.16066)
4. **The simple independent Poisson score grid underestimates uncertainty.** UCL totals contain overdispersion and stage/game-state heterogeneity. A negative-binomial or bivariate count model must be tested, not assumed.
5. **The current isotonic calibration is unstable.** It improved Brier but compressed the mean probability to 57.83%, then produced worse betting ROI. This is a calibration-sample/target mismatch, not evidence that isotonic is intrinsically correct.
6. **The 10%+ edge selection is too aggressive for this sample.** Edge thresholds amplify small probability errors; 2024/25 totals closing data is missing, so the apparent strategy is not a complete two-season test.
7. **Feature timing and stage state are incomplete.** League phase, playoffs, first legs and second legs have different incentives and scoring environments. A single U/O curve pools unlike matches.

## Corrective build

- Use only provider-consistent xG for the primary recent-season challenger; keep mixed rows as a separate sensitivity track.
- Fit Poisson, Dixon-Coles and negative-binomial/bivariate models with rolling xG, shots and big chances; select by chronological log loss/Brier, not ROI.
- Calibrate with regularised logistic/beta calibration using expected total goals, stage, xG coverage and market consensus; calibrate on prior seasons only.
- Devig each closing total correctly and measure CLV before staking. Use 0–3% edge paper bands first; do not jump directly to 10%+.
- Complete 2024/25 closing totals before claiming a two-season market result.

The current conclusion is model misspecification plus incomplete market and xG coverage—not proof that U/O 2.5 is unusable.
