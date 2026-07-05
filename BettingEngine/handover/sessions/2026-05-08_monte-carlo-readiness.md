# Monte Carlo Simulation Readiness

Date: 2026-05-08

## Context

Elliot asked whether the projects are "66-75% there" specifically in terms of being ready to run a Monte Carlo simulation, not in terms of the overall BetMATE product.

Consultant answer:

> For NRL Monte Carlo v1, the data is much closer than the full product. Data readiness is roughly 70-80%.

The main missing piece is not raw data. The missing piece is the simulation layer, calibration, and backtesting.

## Current Data Position

The project already has the main ingredients needed for a basic Monte Carlo engine:

- historical NRL results
- historical market odds and lines
- detailed NRL match-stat JSON files
- current pricing outputs from BettingEngine
- model expected home score
- model expected away score
- expected margin
- expected total
- fair H2H odds
- fair handicap line
- fair total line
- weather/referee/injury context
- existing ML model files for margin, total, and H2H

Observed local data snapshot during review:

- `BettingEngine/data/import/results_2025.csv`: 213 result rows
- `BettingEngine/data/import/odds_2025.csv`: 430 odds/market rows
- `BettingEngine/ml/data/match_stats/`: 912 JSON match-stat files
- `BettingEngine/ml/models/`: margin, total, and H2H model joblib files exist

## Readiness Estimate

| Area | Readiness |
|---|---:|
| Historical results | 80% |
| Odds/market lines | 70% |
| Current model numbers | 85% |
| Weather/ref/injury context | 60-70% |
| Error calibration | 35-45% |
| Simulation script | 0-10% |
| Backtest/reporting | 30-40% |

Overall assessment:

> For Monte Carlo specifically, BetMATE/BettingEngine is around the 66-75% mark with the data. The missing part is implementation and calibration, not the raw information.

## What Monte Carlo V1 Should Do

For each upcoming game:

1. Take BettingEngine's expected margin and expected total.
2. Use historical model error distributions to add realistic uncertainty.
3. Run about 20,000 simulated scorelines.
4. Output:
   - home win probability
   - away win probability
   - cover probability at the market line
   - over/under probability at the market total
   - most likely score bands
   - volatility rating
   - edge versus bookmaker market

Example outputs:

```text
Model says 58%, market says 52%.
Covers +6.5 in 61% of simulations.
Over 46.5 hits in 54% of simulations.
Most likely score band: 22-28 to 16-24.
Volatility: medium.
```

## Missing Calibration

Before the simulation can be trusted, the engine needs to calculate:

- margin error distribution: actual margin minus predicted margin
- total error distribution: actual total minus predicted total
- correlation between margin error and total error
- how volatility changes by game type, such as big favourite, close game, wet weather, high total, low total
- whether model probabilities beat bookmaker implied probabilities over a backtest

The first version can start simple:

- one global margin error standard deviation
- one global total error standard deviation
- one global margin/total correlation estimate
- normal or empirical sampling

Later versions can segment volatility by:

- favourite size
- total band
- weather
- referee type
- venue
- team style
- injury disruption

## Product Direction

Monte Carlo should become part of the paid intelligence layer later, not the free launch.

Free users may eventually see a simple version:

```text
BetMATE Sim Read:
Storm win 57% of simulations.
Line cover lean: small.
Total lean: no clear edge.
```

Paid users could see:

- full sim distribution
- score bands
- alternate line probabilities
- H2H/line/total edge table
- uncertainty rating
- model versus market probability
- "wait / bet / pass" from Baz

## Recommended Next Build

Build `scripts/monte_carlo_nrl.py` or a small `simulation/` module that:

1. Reads a pricing CSV such as `results/r11_pricing_2026.csv`.
2. Reads historical predictions/results for calibration.
3. Estimates margin and total error parameters.
4. Runs simulations per game.
5. Writes a CSV/JSON output for BetMATE and Baz.

Suggested output path:

```text
BettingEngine/outputs/monte_carlo/nrl/r11_2026_simulations.csv
BettingEngine/outputs/monte_carlo/nrl/r11_2026_simulations.json
```

## Consultant View

This is a legitimate near-term feature because the model already produces the correct mathematical spine:

```text
expected home points -> expected away points -> margin -> total -> fair prices
```

Monte Carlo does not replace the model. It sits on top of the model and answers:

> If this model number is right on average, how often does each betting outcome happen once normal NRL randomness is included?

This would make BetMATE feel more intelligent than a standard odds comparison site, because it turns the model number into outcome probabilities and risk ranges punters can understand.
