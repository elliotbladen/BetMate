# Historical odds review download — 15 September 2026

This is a data-only review collection. No model, pricing, production database or
application code was changed.

| Competition | File | Source | Coverage | Odds fields |
|---|---|---|---|---|
| AFL | `data/afl/historical/raw/afl_20260915.xlsx` | AusSportsBetting | 3,568 rows | H2H, line and totals open/min/max/close where supplied |
| NRL | `data/nrl/historical/raw/nrl_20260915.xlsx` | AusSportsBetting | 3,629 rows | H2H, line and totals open/min/max/close where supplied |
| EPL | `BettingEngine/ml/football/data/epl/matches/epl_matches.csv` | Football-Data E0 | 4,590 rows, 2014/15–2026/27 | bookmaker snapshots plus closing columns where supplied |
| EFL Championship | `BettingEngine/ml/football/data/championship/matches/championship_matches.csv` | Football-Data E1 | 6,693 rows, 2014/15–2026/27 | bookmaker snapshots plus closing columns where supplied |
| UCL | `BettingEngine/ml/football/data/ucl/matches/ucl_historical_odds_kaggle_2003_2024.csv` | Kaggle public benchmark | 7,596 UCL rows, 2003–2024 | static 1X2 only; no opening/closing fields |

The exact byte counts and SHA-256 hashes are in
`historical_odds_review_2026-09-15.json`. UCL is deliberately labelled as a
benchmark rather than a closing-line dataset because its source does not provide
quote timestamps or separate opening/closing values.
