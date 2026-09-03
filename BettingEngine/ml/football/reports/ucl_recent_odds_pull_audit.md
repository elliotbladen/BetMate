# UCL recent closing-odds pull audit

## 2025/26 odds source

Footiqo's Champions League odds table (wpDataTables table 639) was queried through its public server-side endpoint. It returned 189 rows for season 2025/2026 with 1X2 closing prices (`xbetClose1FT`, `xbetCloseXFT`, `xbetClose2FT`). The source labels these as closing odds and identifies the bookmaker as 1xBet; no per-price timestamp is exposed, so the provenance status remains `unverified_static_close`.

The raw pull is archived at `data/ucl/markets/ucl_footiqo_closing_1x2_2025_26.csv`.

## Join gate and repair

The current shared walk-forward prediction file contains 189 rows for 2025/26, but its `Date` field contains only two dates (2025-09-16 and 2026-01-20), while the odds table spans 33 match dates through 2026-05-30. This means a team-only fuzzy join can produce false pairings and is not acceptable for a closing-line backtest.

The fixture-date mapping has now been repaired. All 189 2025/26 records were matched to the Footiqo calendar using explicit club aliases and pair occurrence, and the repaired match file is `data/ucl/matches/ucl_matches_openfootball_repaired.csv`.

The date-safe 1X2 evaluation matched all 189 games. At a 10 percentage-point model-edge threshold, there were 113 hypothetical $1 bets, 42 winners, total profit **+$11.87**, and ROI **+10.50%**. This is a provisional static-close result: Footiqo exposes no quote timestamps, and the odds are identified as 1xBet rather than a consensus exchange close. It must not be treated as a confirmed CLV result.

## 2024/25 test

BetExplorer's public 2024/25 results archive exposes 1X2 prices directly in its result tables. The base results page plus the league-phase stage page produced 189 rows, archived at `data/ucl/markets/ucl_betexplorer_2024_25_1x2.csv`.

After conservative club-name resolution, 171 of 189 model fixtures joined cleanly. At the same 10 percentage-point edge threshold: 113 hypothetical $1 bets, 40 winners, total profit **-$6.25**, ROI **-5.53%**. Eighteen fixtures remain unmatched and are excluded pending alias review; this is a partial, non-final season result. The prices are displayed archive odds rather than timestamped exchange closes.
## Recovered 2024/25 totals (2026-09-03)

The public BetExplorer match-odds endpoint returned a 2.5 Over/Under market for all 144 league-phase and 45 playoff fixtures (**189/189, 100%**). These are bookmaker archive prices with displayed creation timestamps, not one exchange-verified close (`unverified_static_close`). Bet365 was used when present (158 fixtures), with an available bookmaker row for the remainder.

| Season | Edge | Bets | Wins | Profit | ROI |
|---|---:|---:|---:|---:|---:|
| 2024/25 | 10% | 95 | 35 | -$10.82 | -11.39% |
| 2024/25 | 20% | 53 | 17 | -$7.02 | -13.25% |
| 2024/25 | 30% | 36 | 12 | -$3.11 | -8.64% |
| 2025/26 | 10% | 113 | 64 | -$8.44 | -7.47% |
| **Combined** | **10%** | **208** | **99** | **-$19.26** | **-9.26%** |

Higher-edge sensitivity: combined 40% edge = 25 bets, 5 wins, -$9.90, -39.60% ROI; combined 50% edge = 12 bets, 3 wins, -$3.30, -27.50% ROI. These samples are very small and remain paper-only.

Raw pull: `data/ucl/markets/ucl_betexplorer_totals_2024_25.csv`; backtest rows: `data/ucl/markets/ucl_betexplorer_totals_backtest_2024_25.csv`.

## 20% edge sensitivity

Using the same flat $1 stake per qualifying bet:

| Season | Matched | Bets | Wins | Profit | ROI |
|---|---:|---:|---:|---:|---:|
| 2024/25 | 171 | 70 | 26 | -$1.01 | -1.44% |
| 2025/26 | 189 | 58 | 21 | +$2.88 | +4.97% |
| Combined | 360 | 128 | 47 | +$1.87 | +1.46% |

## Over/Under 2.5 test

The 2025/26 Footiqo table includes Over/Under 2.5 closing prices. Repricing the same shared Dixon–Coles scoreline matrix and using a 10-point edge threshold produced 113 bets, 64 winners, **-$8.44 profit**, and **-7.47% ROI** at $1 flat stakes. The 2024/25 BetExplorer results table currently exposes 1X2 prices only; its totals prices still need to be pulled from the individual match-odds endpoints before a comparable 2024/25 totals result can be claimed.
