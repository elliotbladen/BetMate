# Value Review - Week Ending 2026-05-05

Source ledger: `data/bets/actual_bets_2026.csv`

Review output: `outputs/bets/value_review_week_ending_2026-05-05.csv`

## Summary

| Scope | Bets | Wins | Losses | P/L | Model Value | Beat Close |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| All | 7 | 4 | 3 | +$53.00 | 6 of 7 positive vs rules engine | 5 clear / 1 neutral / 1 poor |
| AFL | 4 | 1 | 3 | -$78.50 | 4 of 4 positive vs rules engine | 3 clear / 1 poor |
| NRL | 3 | 3 | 0 | +$131.50 | 2 of 3 positive vs rules engine | 2 clear / 1 neutral |

## Read

- The wins/losses alone understate the edge. AFL went 1-3, but all four bets were positive against the rules engine and three of the four beat the close.
- The cleanest value bet was `Dolphins v Melbourne Storm Under 54.5`: model total 44.2, BetMate market close 52.5, user line 54.5.
- `Cronulla -7.5` was strong model value: rules fair line `Cronulla -13.2`, ML shadow also strong, market closed exactly `-7.5 @ 1.90`.
- `Dolphins -3.5` won, but it was not model value. Rules fair line was only `Dolphins -1.4` and ML shadow leaned Storm. This was a result winner, not a process winner.
- AFL open/close was found via the AusSportsBetting AFL workbook. BetMate GitHub currently only has NRL historical odds automation/files, so AFL was not present there.

## NRL Market Detail

| Bet | Open | Close | User | Model | Value Read |
| --- | --- | --- | --- | --- | --- |
| Dolphins/Storm under | 52.5, under 2.10 | 52.5, under 2.05 | 54.5 @ 1.84 | 44.2 total | Excellent line value |
| Dolphins -3.5 | -2.5 @ 1.90 | -3.5 @ 1.85 | -3.5 @ 1.89 | -1.4 fair line | Won, but model-negative |
| Cronulla -7.5 | -4.5 @ 1.90 | -7.5 @ 1.90 | -7.5 @ 1.90 | -13.2 fair line | Model value, neutral CLV |

## AFL Model Detail

| Bet | Open | Close | User | Model | Value Read |
| --- | --- | --- | --- | --- | --- |
| Carlton H2H | 2.50 | 2.45 | 2.55 | 1.75 fair | Model value and beat close |
| Western Bulldogs H2H | 2.90 | 3.15 | 3.21 | 1.67 fair | Model value and beat close, but ML shadow conflicted |
| Adelaide -9.5 | -11.5 @ 1.90 | -8.5 @ 1.95 | -9.5 @ 1.89 | -55.7 fair margin | Strong model edge, but poor CLV |
| Carlton/St Kilda under | 180.5 @ 1.87 | 183.5 @ 1.85 | 183.5 @ 1.89 | 170.9 fair total | Strong model edge and beat close |

## Data Gaps

- Need a standard CLV calculation for line/total bets with different lines, not just price comparison at the same line.
- BetMate GitHub is up to date but currently only stores NRL historical odds. AFL close data came from `https://www.aussportsbetting.com/historical_data/afl.xlsx`.
