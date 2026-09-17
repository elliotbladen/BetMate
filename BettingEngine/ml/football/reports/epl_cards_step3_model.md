# EPL cards Step 3 — model fitting and pricing

The model is fitted on 2022/23–2024/25 (1,140 matches). The 380 matches in 2025/26
are held out and priced only after fitting; Step 5 will evaluate them.

Two prices are produced:

1. **Referee/team baseline**

   `lambda = referee_yellow_rate × (home_team_rate + away_team_rate) / league_rate`

2. **Regularized Poisson GLM**

   The GLM predicts a multiplicative deviation around the pre-match league baseline
   using referee, team, cards-drawn, foul and venue deviations. The features were
   built in Step 2 and contain no current-match information.

Both lambdas are converted to Over/Under 3.5 yellow-card probabilities using a
negative-binomial distribution. The fitted training dispersion is `alpha = 0.02183`.
Fair odds are the reciprocal probabilities; no bookmaker margin or ROI claim is made
at this stage.

The out-of-sample 2025/26 average expected totals are 3.50 for the baseline and 4.11
for the GLM. Those are prices to be tested, not evidence that the GLM is better. Step
5 will compare calibration and market performance against the baseline and closing
prices.
