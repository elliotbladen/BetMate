# Sydney/Melbourne Group 1 Betfair-close backtest

## Locked rule

- Period requested: 2025-08-23 through 2026-08-22.
- Population: Sydney and Melbourne Group 1 races only.
- Ratings: `horse-ability-v2.8-final-research-freeze`, strictly point in time.
- Rating probabilities: frozen temperature 60.
- Model prices: probabilities marked to a 110% book.
- Bet: $1 win when `Betfair close / model price - 1 > 10%`.
- Betfair close: `BEST_AVAIL_BACK_AT_SCHEDULED_OFF`.
- Commission: 10% NSW and 7% Victoria, charged on positive net race-market
  profit after all selections in that race.

## Coverage

Official Betfair files cover 58 of 59 requested Group 1 races. The unpublished
August 2026 file prevents inclusion of the 22 August Winx Stakes. All 58
available markets and their eligible rating runners matched completely.

## Result

| Measure | Result |
|---|---:|
| Races | 58 |
| Bets | 452 |
| Winning bets | 9 |
| Stakes | $452.00 |
| Gross P&L | -$252.00 |
| Gross ROI | -55.75% |
| Net P&L | -$264.23 |
| Net ROI | -58.46% |
| Maximum drawdown | $311.33 |
| Race-bootstrap 95% net ROI interval | -87.74% to -15.96% |

NSW returned -49.47% net ROI on 236 bets; Victoria returned -68.28% on 216.
Only nine of 58 races were profitable.

## Interpretation

This rule fails decisively. The frozen probability temperature compresses
ratings heavily toward equal chance. Against a sharp Group 1 close that makes
many long-priced runners appear to offer value: the strategy averaged 7.8 bets
per race. The occasional large-priced winner did not compensate for the broad
set of losing selections.

The result does not show that the Horse Ability ordering is useless. It shows
that this conversion from broad ability ratings to Group 1 win probabilities
is not sufficiently discriminating or race-specific for betting. Do not tune
the completed rating retrospectively to repair this return. Any next test must
be registered as a separate pricing model and evaluated on new or partitioned
data.
