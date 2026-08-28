# Group 1 Betfair-close backtest handover

Date: 2026-08-28

Downloaded the official Betfair Australia/NZ thoroughbred 2025 archive and
2026 January-July CSV files into `RacingEngine/data/raw/betfair_anz/`.

Implemented `racing_engine/betfair_anz.py` and
`racing_engine/group1_backtest.py`. The locked rule prices each race to 110%
using the final ratings-only temperature of 60 and stakes $1 when the scheduled-
off Betfair best-back price exceeds the model quote by strictly more than 10%.
Commission is applied to positive net market profit: 10% NSW and 7% Victoria.

The test covered 58/59 requested Group 1 races from 2025-08-23 to 2026-08-22.
August 2026 Betfair data is not published, excluding the 22 August Winx Stakes.
There were 452 bets, 9 winners, $452 staked, -$252 gross P&L and -$264.225 net
P&L: -58.46% net ROI. Race-level bootstrap interval: -87.74% to -15.96%.

This exact rule is rejected. The failure mechanism is probability compression:
it creates an average 7.8 apparent value bets per Group 1. Preserve this result
and do not retune Horse Ability against it. Further work belongs to a separately
registered race-specific pricing model.

## Doncaster audit added 29 August 2026

The 2026 Doncaster (Randwick race 8, 4 April) confirms the failure mechanism.
The ratings-only softmax assigned every runner between 4.77% and 7.58%, then
the 110% book quoted every runner between 11.99 and 19.04. It therefore placed
14 bets in a 16-runner field.

Sheza Alibi won at a Betfair scheduled-off price of 2.02. Her point-in-time
ability was 102.85, model probability 6.31% and model 110% price 14.40, so she
was not backed. Pericles was model top-rated at 113.83/11.99; Gringotts was
108.36/13.14. The race lost all 14 stakes.

This shows both excessive probability compression and missing race-specific
information around an emerging favourite. Preserve the Horse Ability layer;
repair only through a separately registered Pricing Engine and do not reuse
this observed year as an untouched final holdout.
