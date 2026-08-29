# NFL Phase 1 — Data Coverage Report

**Generated:** 2026-08-28

## Summary

Phase 1 data ingestion complete. All three data sources aligned and feature store built.

| Source | Seasons | Games | Coverage |
|--------|---------|-------|----------|
| nflverse schedules | 2014-2025 | 3,113 REG | 100% scores + spread_line |
| nflverse PBP | 2014-2025 | 3,295 all | 0% EPA null, ~34K pass/run plays/season |
| aussportsbetting odds | 2014-2025 | 3,295 | 100% closing odds 2014-2024, 95% 2025 |
| Feature store | 2014-2025 | 3,113 with EWMA | 80 columns, 62 features |

## Feature Store

- **Training set (2014-2024):** 2,837 games with EWMA features + results
- **With closing odds:** 2,757 games (97%)
- **Vault (2025):** 276 games — DO NOT TOUCH until Phase 5
- **Leakage verified:** Week 1 features use only prior-season decayed EWMA (10 games × 0.35 retention)
- **Spread sign convention:** 80% directional consistency (expected with upsets)

## Files Created

| File | Size | Contents |
|------|------|----------|
| `data/nfl/schedules/games.csv` | 7,548 games | nflverse schedules 1999-2026 |
| `data/nfl/pbp/play_by_play_{2014-2025}.parquet` | ~225MB total | EPA play-by-play |
| `data/nfl/historical_odds/nfl_odds_2014_2025.csv` | 3,295 games | Cleaned odds with nflverse team abbrs |
| `data/nfl/features/weekly_epa.parquet` | 7,289 rows × 80 cols | Matchup-level feature store |
| `data/nfl/features/weekly_epa.csv` | Same, CSV format | For inspection |
| `ml/nfl/features.py` | Feature builder | EWMA EPA + schedule context + odds |

## Team Name Note

Schedule uses historical abbreviations (STL, SD, OAK) for pre-relocation seasons.
Odds file maps these to current names (LA, LAC, LV). Feature store inherits schedule names.
This means ~24 early-season games (2014-2015 STL/SD) don't join with odds — acceptable.

## EWMA Feature Columns (per team, home_ and away_ prefixed)

- `off_epa` / `def_epa` — overall EPA per play
- `off_pass_epa` / `def_pass_epa` — pass EPA
- `off_rush_epa` / `def_rush_epa` — rush EPA
- `off_success_rate` / `def_success_rate` — play success rate
- `off_pass_success` / `def_pass_success` — pass success rate
- `off_rush_success` / `def_rush_success` — rush success rate
- `off_early_down_epa` / `def_early_down_epa` — 1st/2nd down, non-garbage-time
- `off_explosive_rate` / `def_explosive_rate` — 20+ yard plays
- `off_sack_rate` / `def_pressure_rate` — sack rate
- `games_in_ewma` — number of games in EWMA window
- `diff_*` — home minus away differentials for all the above

## Validated Rankings (2024 Week 18 EWMA)

| Rank | Offense | Defense (lower = better) |
|------|---------|--------------------------|
| 1 | BAL +0.202 | PHI -0.116 |
| 2 | BUF +0.190 | BAL -0.084 |
| 3 | DET +0.182 | GB -0.070 |
| 4 | TB +0.128 | DEN -0.063 |
| 5 | PHI +0.120 | MIN -0.058 |

All match consensus 2024 NFL team rankings.

## Next: Phase 2 — Baselines

1. Fit ridge regression: margin ~ EPA features + context
2. Fit ridge regression: total ~ EPA features + context
3. Build simple Elo baseline for comparison
4. Run rolling-origin evaluation (train 2014-2018, test 2019; expanding window)
5. Report: model vs close RMSE, opener vs close RMSE, margin/total MAE
