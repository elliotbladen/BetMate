# UCL architecture and five-step build plan

## Architecture

The model will have four connected layers:

1. **Data and identity:** archived UEFA fixtures, domestic results, xG, odds, line-ups, injuries, UEFA coefficients and draw metadata. Every record is time-stamped, canonicalised and quarantined if identity or date is uncertain.
2. **Cross-league team strength:** time-decayed Dixon-Coles attack/defence, hierarchical domestic-league effects, ClubElo and UEFA five-season coefficient prior. New or lightly observed clubs are shrunk toward the cross-league prior.
3. **Match distribution:** bivariate Dixon-Coles scoreline probabilities with calibrated home advantage, phase/stage effects, player availability and rest/travel context. A calibrated DC/Elo blend produces one coherent distribution.
4. **Competition state:** exact league-phase table simulation and knockout Monte Carlo. The simulator applies the actual 36-team schedule, UEFA points and tie-break rules; knockout simulations carry aggregate score, venue order, extra time and penalties.

## Five implementation steps

1. **Strength and prior rebuild:** import and validate UEFA coefficients, domestic xG/results and ClubElo; estimate cross-league shrinkage and calibrate the DC/Elo blend chronologically.
2. **Match-market expansion:** derive 1X2, Asian handicap and totals from the same score matrix; add devigged market consensus as a benchmark and calibrator, never as a leaked feature.
3. **League-phase simulator:** reconstruct each 2024/25+ draw graph, simulate remaining fixtures thousands of times, and output top-8, top-24, elimination and final-position probabilities.
4. **Knockout simulator:** add draw constraints, two-leg aggregate state, second-leg home advantage, extra time and penalty shoot-outs; validate against historical ties.
5. **Backtest and promotion gate:** run 2024/25 and 2025/26 walk-forward tests by phase and market; require calibration, CLV, drawdown and stability gates before live staking.

## Is 1X2 sufficient?

**No—not for the complete UCL model.** 1X2 is sufficient as the first match-outcome baseline and is required for validating the core probability engine. It is not sufficient for three reasons:

- A scoreline model naturally contains goal-margin and total-goal information that 1X2 discards.
- Asian handicap and totals are major football markets; research finds Asian-handicap prices can be efficient forecasts and often carry lower margins than conventional 1X2. [Research](https://www.sciencedirect.com/science/article/pii/S0169207024000670)
- UCL’s most valuable outputs are often qualification markets—top 8, top 24, tie qualification and outright winner—which cannot be represented by a single match 1X2.

The practical order is therefore: keep 1X2 as the core audit market, add Asian handicap and totals next, then add league-phase and knockout qualification markets. We should not promote any market solely because 1X2 accuracy looks good; calibration and closing-line value must be checked separately. UEFA's 36-team league phase and knockout rules make this state simulation essential. [UEFA format](https://www.uefa.com/uefachampionsleague/news/0268-12157d69ce2d-9f011c70f6fa-1000--new-format-fo/) [UEFA regulations](https://documents.uefa.com/r/Regulations-of-the-UEFA-Champions-League-2025/26-Online)
