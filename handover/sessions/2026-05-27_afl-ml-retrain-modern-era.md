# Handover — 2026-05-27 — AFL ML model retrained for modern-rule era

## Background

AFL scoring has shifted significantly across rule-change eras. The old ML model was trained
on 2009–2023 data (2,921 games) and was systematically underpredicting totals by ~8 pts vs
actual (and vs market). Research confirmed this is a regime mismatch — the 2009-2021 era had
lower scoring than 2022+. Professional syndicates handle this by filtering training data to
the post-break era, not relying on time-decay alone.

## What changed

### `ml/afl/game_log.py`
- Added `--min-year` CLI argument (default 2022)
- ELO walk-forward still processes ALL historical data (2009 onwards) so ratings are accurate
- Output records filtered: only season >= min_year AND season != 2020 (COVID exclusion)
- Added `season_year` field to the feature record (same as `season`, used as ML feature)
- Updated docstring to reflect new split logic

### `ml/afl/train.py`
- Added `'season_year'` to `FEATURES_MARGIN_TOTAL` (era signal — model learns upward trend)
- Added `--decay` CLI argument (default 1.5)
- Added exponential `sample_weight` in `train_and_evaluate()`:
  `sample_weight = np.exp(np.linspace(0, decay, n))` — oldest game 1.0x, newest 4.5x
- Updated docstring
- Training summary now prints training seasons and decay value

### `ml/afl/backtest_2025.py`
- Added `'season_year'` to `FEATURE_COLS` (was causing feature mismatch error)

## Training run results

```
Features CSV: 954 rows (2022-2026, excl. 2020)
  train:    423 (2022-2023)
  validate: 216 (2024)
  test:     216 (2025)
  deploy:    99 (2026 R1-R11)

Margin model: MAE=31.7 pts, DirAcc=68.5%
Total model:  MAE=24.6 pts, DirAcc=100% (spurious for totals — always +ve)
H2H model:    Acc=65.7%, LogLoss=0.83, Brier=0.255
```

## Calibration improvement (2025 backtest)

| Metric | Old (2009-2023) | New (2022-2023) |
|--------|----------------|-----------------|
| Total MAE | 25.2 pts | **24.6 pts** |
| Bias vs actual | **-8.0 pts** | **-5.8 pts** |
| Totals strike ±10pt edge | ~55% | **61.3%** |
| H2H accuracy | ~65% | **65.7%** |

Mean 2025 actual total: 168.8 pts  
Mean 2025 ML prediction: 163.0 pts  
Mean 2025 market line: 170.6 pts  

Remaining -5.8 pt bias is because 2022-2023 training data also had lower scoring than 2025.
The `season_year` feature allows upward extrapolation for 2026 (scoring ~90 pts/team = 180 pts).

## Commands to retrain (if xlsx updated)

```powershell
cd C:\Users\ElliotBladen\Apps\BettingEngine
$env:PYTHONUTF8 = "1"
# Step 1: rebuild features (ELO warmup from all history, records from 2022+)
& ".\.venv\Scripts\python.exe" ml\afl\game_log.py --xlsx outputs\afl_weekly_review\historical\latest.xlsx --min-year 2022
# Step 2: retrain all three models
& ".\.venv\Scripts\python.exe" ml\afl\train.py --decay 1.5
# Step 3: backtest
& ".\.venv\Scripts\python.exe" ml\afl\backtest_2025.py --xlsx outputs\afl_weekly_review\historical\latest.xlsx
```

## Next retrain timing

- After 2026 season ends: add 2024 to training window (`--min-year 2022` stays, 2024 moves
  from validate to train, 2025 becomes validate, 2026 becomes test)
- Or mid-season: if 2026 scoring continues accelerating (currently 90.2 pts/team, model at 163
  for 2025 games), consider adding 2024 to training now to reduce bias further

## Model files updated

- `ml/afl/results/features_afl.csv` — 954 rows (2022-2026)
- `ml/afl/results/models/margin_model.pkl`
- `ml/afl/results/models/total_model.pkl`
- `ml/afl/results/models/h2h_model.pkl`
- `ml/afl/results/metrics.txt`
- `ml/afl/results/backtest_2025.csv` / `backtest_2025.txt`

## ELO snapshot (end of 2026 R11)

Top 5: Geelong (1739), Sydney (1732), Brisbane (1721), Fremantle (1675), Hawthorn (1664)
Bottom: West Coast (1165), Richmond (1126)
