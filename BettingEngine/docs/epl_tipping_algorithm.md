# Baz EPL tipping algorithm

Status: implemented as a provisional 1X2 competition decision layer on 27 August 2026.

## Research decision

The existing xG-fed Dixon–Coles/Elo probabilities remain the forecast owner.
Dixon and Coles model changing team strengths and low-score dependence; the
method was designed for English football outcome probabilities. Calibration,
not merely classification accuracy, is the relevant property when probabilities
drive decisions.

Matrix rows are descriptive residuals against de-vigged closing markets. They
overlap (overall, venue, weekday and month), so treating aligned rows as
independent votes would multiply the same matches. Baz therefore shrinks each
row by `N/(N+30)`, weights broad/venue context more than calendar context,
caps each raw outcome adjustment at three percentage points, and applies only
20% of that cap to the pricing probability before re-normalising the 1X2 book.
The maximum practical movement is consequently small.

The contest optimiser is separate. With one point for a correct 1X2 selection,
it selects the largest final probability. Alternative draw points change the
expected-points calculation. A crowd-leverage mode exists in the core but is
not enabled by the CLI until genuine pick-ownership data and pool state are
available. Research on sports pools shows that large-pool win probability can
favour selective differentiation from popular favourites, while forecasting-
competition research shows winner-take-all incentives can distort truthful
forecasting. That is a contest tactic, not evidence that an upset became more
likely.

## Guardrails

- Production probabilities are primary; shadow probabilities are diagnostic.
- Normal/shadow disagreement is shown explicitly.
- Matrix evidence cannot silently overwrite the model.
- Missing matrix sheets mean zero adjustment, not imputation.
- The generated card is provisional until the competition scoring rules are set.
- Baz advises; the user enters every tip.

## Commands and output

```bash
python scripts/epl_tipping_algo.py \
  --pricing results/epl/round2_2026_27.csv
```

Output: `outputs/football/epl/latest_tipping_card.json`.
Baz serves the same artefact at `GET /tips/epl`.

## Research sources

- Dixon & Coles, *Modelling Association Football Scores and Inefficiencies in
  the Football Betting Market*, DOI 10.1111/1467-9876.00065.
- Clair & Letscher, *Optimal Strategies for Sports Betting Pools*, DOI
  10.1287/opre.1070.0448.
- Witkowski et al., *Incentive-Compatible Forecasting Competitions*, DOI
  10.1609/aaai.v32i1.11471.
- Gneiting & Raftery, *Strictly Proper Scoring Rules, Prediction, and
  Estimation*, DOI 10.1198/016214506000001437.

## Required final configuration

Record whether the competition uses plain 1X2, exact scores, margins, draw
bonuses, jokers, lockout times, missed-tip defaults and tie-breakers. Exact-score
rules require the existing Dixon–Coles score matrix to be exposed in the pricing
CSV; they must not be approximated from a 1X2 pick after the fact.
