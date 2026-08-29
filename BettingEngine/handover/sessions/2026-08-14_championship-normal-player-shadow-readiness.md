# 2026-08-14 — Championship normal engine and player shadow

## Normal engine repairs

- Configured current season `2026/27` ingestion. Football-Data had not yet
  published its E1 CSV; the downloader safely retained the completed history.
- Added explicit Matchweek-1 priors for the six division changes:
  - PL relegated: Burnley, West Ham, Wolves (+180 Elo prior).
  - L1 promoted: Bolton, Cardiff, Lincoln (-180 Elo prior).
- Returning teams no longer reuse ancient Championship D-C attack/defence/HFA
  parameters. They reset to neutral before the bounded T8 prior is applied.
- Rest/form older than 45 days and corners older than 180 days are no longer
  presented as current context.
- Corrected the reversed CLI value label.
- Added a machine-readable round pricer and output.

Wolves v Blackburn normal price (Matchweek 1): $2.27 / $3.51 / $3.65.
This remains a large disagreement with the market and should not be treated as
an automatic wager; current-season league results do not exist before kickoff.

## Player shadow work

- Championship roster: 719 current players.
- Added an official-XI ESPN collector, polling every 30 minutes and preserving
  final snapshots. At the audit time, Wolves–Blackburn line-ups were not yet
  published.
- Backfilled official starters:
  - 2023/24: 10,186 starter rows, 463 matches.
  - 2024/25: 10,890 starter rows, 495 matches.
  - 2025/26: 11,550 starter rows, 525 matches; retained as the sealed vault.
- Built a genuine ridge starter-residual shadow with a ±0.20 goal cap.
- Honest time split: train 2023/24, test 2024/25.

## Player test result

| Metric | Base | Player adjusted |
|---|---:|---:|
| Goal MAE | 0.847649 | 0.848123 |

The player layer worsened MAE by 0.000474 and was rejected. No model artifact
was promoted. The round output correctly reports `ABSTAIN` rather than inventing
a player price.

## Next player iteration

Add expected-minutes/availability inputs, position-aware pooling, rolling player
attacking/defensive statistics and multiple training seasons. Retest on 2024/25,
then use 2025/26 exactly once as the sealed promotion vault.

## Files

- `ml/football/price_match.py`
- `ml/football/price_championship_round.py`
- `ml/football/player_layer/fetch_espn_match_snapshots.py`
- `ml/football/player_layer/backfill_espn_lineups.py`
- `ml/football/player_layer/train_starter_shadow.py`
- `ml/football/data/championship/player_layer/starter_shadow_eval.json`
- `outputs/football/championship/round_price_2026-08-14.json`

