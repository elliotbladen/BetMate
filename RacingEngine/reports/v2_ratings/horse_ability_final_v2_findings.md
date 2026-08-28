# Final Horse Ability V2 findings

## Decision

Freeze `horse-ability-v2.8-final-research-freeze` as the completed research
rating for the one-year Betfair backtest. Do not promote it into accepted
production ratings yet.

## Headline evidence

| Period | Races | vs rejected V2 | vs V1 | vs uniform |
|---|---:|---:|---:|---:|
| Validation | 876 | -0.01866 | -0.00464 | -0.01144 |
| Historical holdout | 835 | -0.00354 | -0.01167 | -0.01752 |

Negative log-loss differences favour the final rating. Its validation interval
against V1 is [-0.01238, +0.00293], which includes zero. That prevents a claim
of conclusive production superiority.

## Named audits

- Natural Fling achieved run: 104.22; current ability: 99.67.
- Sheza Alibi WFA achieved run: 116.24.
- Gringotts WFA achieved run: 112.37.
- Initial chronological ability: Sheza Alibi 110.83, Gringotts 110.28.
- Current retrospectively revised ability: Gringotts 110.87, Sheza Alibi
  110.83—effectively level.

All mandatory named checks pass on the chronological model used for backtests.
The retrospective view is reported separately and never leaked backward.

## Remaining weaknesses

The model trails V1 in listed races (+0.00430), other-class races (+0.00817)
and sparse-history fields (+0.00460). It also trails rejected V2 in Group 1,
Group 3 and staying subsets, although those subsets generally beat V1 and
uniform. These are declared diagnostics, not reasons to retune before the
market backtest.

## Backtest boundary

The configuration and probability temperature are now locked. Betfair prices
may be used only as the comparison and execution price, never as a rating
feature. Any staking/value rule must be declared before returns are inspected.
