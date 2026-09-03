# EPL and Championship results/closing import

Imported: 2 September 2026  
Source: Football-Data current-season `2627/E0.csv` and `2627/E1.csv`

## Coverage

| League | Completed weekend rows | Latest result | Duplicate match keys | Closing 1X2 | Closing O/U 2.5 |
|---|---:|---|---:|---:|---:|
| EPL | 10 | 31 August 2026 | 0 | 10/10 | 10/10 |
| Championship | 12 | 29 August 2026 | 0 | 12/12 | 12/12 |

Weekend is defined as 28–31 August 2026 for this import.

## Closing fields retained

- Bet365 1X2: `B365CH`, `B365CD`, `B365CA`
- Maximum-market 1X2: `MaxCH`, `MaxCD`, `MaxCA`
- Average-market 1X2: `AvgCH`, `AvgCD`, `AvgCA`
- Bet365 closing totals: `B365C>2.5`, `B365C<2.5`
- Maximum closing totals: `MaxC>2.5`, `MaxC<2.5`
- Average closing totals: `AvgC>2.5`, `AvgC<2.5`
- Modern closing Asian handicap and prices are also retained.

Football-Data does not supply a BTTS closing market in these league files.
BTTS performance reports must use an independently archived BTTS close or
clearly label any proxy; do not infer BTTS closing odds from 1X2 or totals.

## Import method

The fetcher now supports `--live-merge`. It downloads only the configured live
season, replaces matching date/home/away records with the latest source row,
adds newly completed matches, retains historical seasons and produces one row
per match key.

Commands used:

```text
python ml/football/fetch/fetch_results.py --league epl --live-merge
python ml/football/fetch/fetch_results.py --league championship --live-merge
```

The result and closing-odds datasets are ready for separate EPL and EFL
performance reports.
