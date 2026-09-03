# Champions League pricing research

## Main findings

1. **Use a probabilistic score model, not a winner classifier.** The established football approach models home and away goals with Poisson/Dixon-Coles components. Recent research on the new incomplete round-robin UCL format specifically combines a bivariate Dixon-Coles model with Elo strength, which supports our core direction.

2. **Strength must be cross-league.** UCL clubs do not share one domestic league. ClubElo, domestic-league xG/ratings, and UEFA's five-season sporting coefficient should be separate inputs, with shrinkage for clubs with limited UCL history. UEFA confirms the five most recent season coefficients are used for sporting seeding, with a 20% association-coefficient floor.

3. **The 2024/25+ league phase needs simulation.** UEFA's format is 36 clubs, eight different opponents per club, four home and four away; places 1–8 go directly to the round of 16, 9–24 enter playoffs, and 25–36 are eliminated. Qualification probabilities therefore require simulating the actual schedule and UEFA tie-break rules, not projecting a normal league table.

4. **Knockouts need a separate state model.** Two-legged ties must simulate first-leg score, second-leg venue, extra time and penalties. The final is one match and uses extra time and penalties if required. Aggregate qualification is a different target from the 90-minute match result.

5. **Calibration matters more than headline accuracy.** Sports-betting research warns that model selection should emphasise probability calibration, log loss/RPS and closing-line value rather than raw hit rate. Large apparent edges must be shrunk or rejected when calibration tests show overconfidence.

6. **Markets are a benchmark and optional calibrator.** The closing market should not be blindly copied, but a devigged consensus line is the strongest available external benchmark. We should measure whether our model adds information to it, using time-matched prices and CLV—not merely whether our bets win.

## Recommended production architecture

**Pre-match strength:** domestic xG/Dixon-Coles, ClubElo, UEFA coefficient prior, squad/player availability, venue and rest/travel. Fit chronologically and shrink new or cross-league teams toward the UEFA/domestic prior.

**Match distribution:** bivariate Dixon-Coles scoreline matrix, with calibrated home advantage and competition/stage effects. Blend DC and Elo only after out-of-sample calibration.

**League phase:** simulate the exact 36-team schedule thousands of times, applying three points for a win, one for a draw, zero for a loss, and the UEFA ranking/tie-break sequence. Output top-8, top-24, elimination and final-position probabilities.

**Knockout:** Monte Carlo each tie from the two match score distributions; preserve aggregate state, home leg, extra time and penalty probabilities. Simulate the draw constraints and bracket before producing tournament prices.

**Decision layer:** compare model probabilities with devigged closing/opening prices, require calibration-qualified edge bands, and track CLV, Brier/RPS, log loss, ROI and drawdown by phase and market.

## What this means for BetMate

Our current upgrade has the correct DC + ClubElo + supported form/rest foundation. The next material improvements are (a) import UEFA coefficient and domestic-strength priors, (b) calibrate against time-matched market probabilities, (c) make league/knockout simulations use the exact official constraints, and (d) activate player/injury effects only when dated historical coverage is complete.

## Sources

- UEFA format overview: https://www.uefa.com/uefachampionsleague/news/0268-12157da4-2d2d-9f011c70f6fa-1000--new-format-fo/
- UEFA regulations 2025/26: https://documents.uefa.com/r/Regulations-of-the-UEFA-Champions-League-2025/26-Online
- UEFA club coefficients: https://www.uefa.com/nationalassociations/uefarankings/club/
- Dixon-Coles/Elo UCL qualification research: https://arxiv.org/abs/2508.20075
- Calibration versus accuracy in sports betting: https://arxiv.org/abs/2303.06021
