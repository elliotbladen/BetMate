# UCL Over/Under 2.5 web research findings

## What the external evidence says

- UEFA reports 470 goals in 144 league-phase matches in 2024/25 (3.26 per match), while the full season finished with 618 goals in 189 matches (3.27). The league-phase rate is therefore not a low-goal environment that requires a large blanket Over prior.
- UEFA also shows why goals cannot be used as a substitute for xG: Barcelona scored 28 from 15.27 xG and Inter conceded one goal from 7.82 xG against in the league phase. Finishing and goalkeeper variance are material.
- Research on the Over/Under 2.5 market finds that ratings using shots and corners, with direct probability modelling, outperform a simple goals-only approach; the published edge is small (about 0.8% over a very large sample), not the 20–50% edges our old pipeline produced.

## Diagnosis of BetMate

1. Mixed xG quality: shot-map xG, recovered provider xG and goals fallback are combined. Goals fallback creates false certainty and pushes probabilities into extreme tails.
2. Wrong distribution for an elite cross-competition: a basic independent Poisson/Dixon–Coles score matrix does not model finishing skill, goalkeeper effects, shot volume/quality, red cards or two-leg incentives well enough for UCL totals.
3. Stage mis-specification: league phase, playoff, first leg, second leg and final have different incentives. One generic stage correction was tested, but it was not strong enough and was not separately fitted for knockout-leg state.
4. Insufficient calibration: the model mean Over probability was about 70.45% versus an observed 65.87% across the two seasons. High probabilities are systematically too high.
5. Edge testing was inconsistent: the old 2024/25 test used expected-return edge while 2025/26 used probability edge. The 40–50% results were therefore not comparable and were partly a threshold-definition artefact.
6. Market anchor is underused: published forecasting research finds that calibration to market prices is a dominant accuracy driver. A fixed 50/50 blend is a useful safety rail, but its weight must be learned out-of-sample.
7. Sample and price quality: 378 matches are small for tail-edge claims, and the available prices are static bookmaker archives rather than timestamp-verified exchange closes.

## Correct rebuild direction

Use direct Over probability modelling with shots, corners and xG-quality features; fit league-phase and knockout-leg models separately; remove goals fallback from the primary track; calibrate by walk-forward beta/isotonic regression; and estimate the market-blend weight only on prior seasons. Do not promote on ROI until the model beats a market-only baseline on Brier/log loss and shows stable CLV.
