# EPL regression/progression study — Step 1 data audit

## Scope

The study will train on 2021/22–2024/25 and keep 2025/26 as a locked holdout. This file records the Step 1 inventory before any model fitting.

## Existing local coverage

| Dataset | Local file | Coverage | Use |
|---|---|---:|---|
| Results, goals, shots, cards, corners and archived prices | `data/epl/matches/epl_matches.csv` | 2014/15–2026/27 | Match outcomes, context and market joins |
| Understat xG | `data/epl/xg/understat_xg.csv` | 2014/15–2024/25 | xG, goals and process/output gaps |
| PPDA/style | `data/epl/style/ppda_dated.csv` | 2014/15–2024/25 | Process context and robustness checks |
| Existing model features | `data/epl/clv/features_all_seasons.csv` | 2017/18–2023/24 | Reference only; not assumed sufficient for this study |
| Existing model backtest | `data/epl/clv/backtest_results.csv` | 2021/22–2023/24 | Reference benchmark only |

The match file already includes 2025/26 and early 2026/27 rows, while the local Understat and PPDA files stop at 2024/25. Therefore 2025/26 process statistics must be sourced and archived before it can be used as the holdout.

## External source plan

1. Understat: xG, npxG and shot-level process data. The repository already has a fetcher at `ml/football/fetch/fetch_understat_xg.py`.
2. Sofascore: match statistics, shots, big chances, box touches, lineups and event context. Use the documented API endpoint and save raw JSON snapshots with retrieval timestamps.
3. FotMob (FootballMob): independent cross-check for xG, shots, lineups and team/player match statistics. Store it as a separate source, never silently overwrite Understat values.
4. Official competition/club feeds: confirm fixtures, lineups and player availability where third-party feeds disagree.

## Data rules

- Every raw download receives a retrieval timestamp, URL and checksum.
- Team names are normalised through one alias table.
- Duplicate matches are resolved by date plus home/away identity.
- Conflicting xG/stat values are retained by source and audited before a canonical value is selected.
- No post-match field may be present in a pre-match feature row.
- 2025/26 remains untouched while the feature design and model weighting are selected.

## Step 1 status

Inventory complete. Existing Understat and match data are usable for the historical foundation. SofaScore/FotMob coverage and 2025/26 Understat coverage still need to be downloaded and validated before Step 2 feature construction.
