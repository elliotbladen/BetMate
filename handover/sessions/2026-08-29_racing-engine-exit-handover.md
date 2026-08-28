# RacingEngine exit handover

Date: 2026-08-29

## Current position

Horse Ability is complete and frozen as
`horse-ability-v2.8-final-research-freeze`. It is a locked research input, not
accepted production, because its validation improvement over V1 remains
statistically inconclusive. Accepted production ratings were not changed.

The requested three-year Saturday metro database is complete: 137/137 Sydney
meetings and 137/137 Melbourne meetings, containing 2,679 races and 36,186
runner records. Official Betfair Australia/NZ 2025 and January–July 2026 files
are cached in `RacingEngine/data/raw/betfair_anz/`.

## Frozen rating configuration

- Four-run responsive state; 90-day half-life.
- 25% peak blend, 1.5-run reliability prior and 10% trajectory.
- 25% initial handicap response; later collateral revisions effective-dated.
- No mechanical layoff decay and no base distance/going adjustment.
- Frozen ratings-only probability temperature: 60.

Named chronological checks: Natural Fling achieved 104.22/current 99.67;
Sheza Alibi WFA achieved 116.24/current 110.83; Gringotts WFA achieved
112.37/current 110.28. The retrospective Gringotts state of 110.87 remains
separately labelled and cannot leak into prior predictions.

## Group 1 Betfair result

The locked rule priced Sydney/Melbourne Group 1 races to 110% from Horse Ability
only and bet $1 when the scheduled-off Betfair best-back price exceeded the
model quote by more than 10%.

- Requested/tested races: 59/58. The unpublished August 2026 file excludes the
  22 August Winx Stakes.
- Bets/winners: 452/9; stake: $452.
- Gross P&L: -$252; net P&L: -$264.225; net ROI: -58.46%.
- Maximum drawdown: $311.325.
- Race-bootstrap 95% net ROI interval: -87.74% to -15.96%.

Reject this exact direct-pricing rule.

## Doncaster diagnosis

In the 2026 Doncaster the temperature-60 conversion compressed all 16 runners
into 4.77%–7.58%, producing 110% prices of 11.99–19.04. It backed 14 runners
and missed the winner.

| Horse | Ability | Model probability | Model 110% price | Betfair close | Bet? |
|---|---:|---:|---:|---:|---|
| Pericles | 113.83 | 7.58% | 11.99 | 18.00 | Yes |
| Gringotts | 108.36 | 6.92% | 13.14 | 15.00 | Yes |
| Sheza Alibi | 102.85 | 6.31% | 14.40 | 2.02 | No |
| Hellsing | 86.09 | 4.77% | 19.04 | 450.00 | Yes |

Sheza Alibi won and the race lost $14 gross. Model probabilities correctly sum
to 100% and quoted implied probabilities to 110%; the fault is inadequate
ability-to-win dispersion and missing current race-specific information.

## Next task

Build a separate versioned Pricing Engine. Do not rewrite Horse Ability to fit
this result. Pre-register development and untouched test periods before fitting
probability dispersion, emerging-horse uncertainty, current campaign, weights,
distance/going, barrier/map and other race-day inputs. The observed Group 1
year can no longer be claimed as a fresh final holdout.

Key reports:

- `RacingEngine/reports/v2_ratings/horse_ability_final_v2_findings.md`
- `RacingEngine/reports/backtests/group1_betfair_close_v1.json`
- `RacingEngine/reports/backtests/group1_betfair_close_v1_findings.md`
- `RacingEngine/reports/data/saturday_metro_3y_coverage_2026-08-28.md`

Exit verification: 141 tests passed with one data-dependent skip before this
documentation-only handover update.
