# Champions League matchday 1 — the six remaining fixtures

Sydney 2026-09-11. Normal mode and player-shadow mode, 1X2 and O/U 2.5, decimal fair odds over 90 minutes. Research prices: no market was captured, no EV was computed, and nothing here is a bet signal.

## 1X2

| Match | Kick-off (UTC) | Normal H | D | A | Shadow H | D | A |
|---|---|---:|---:|---:|---:|---:|---:|
| Fenerbahce v AS Roma | 16:45 | — | — | — | — | — | — |
| PSV Eindhoven v Shakhtar Donetsk | 16:45 | 1.97 | 4.36 | 3.81 | — | — | — |
| Bayern Munich v Bodo/Glimt | 19:00 | 1.28 | 7.90 | 10.77 | 1.32 | 7.33 | 9.60 |
| Como v RB Leipzig | 19:00 | — | — | — | — | — | — |
| Manchester United v Sabah FK | 19:00 | — | — | — | — | — | — |
| Slavia Prague v Lens | 19:00 | 1.82 | 3.78 | 5.41 | — | — | — |

## O/U 2.5

From the same score matrix as the 1X2 price. `Over`/`Under` are the raw matrix numbers; `Over (iso)` is the archived isotonic calibration applied to them.

| Match | Normal Over | Under | Over (iso) | Shadow Over | Under | Over (iso) |
|---|---:|---:|---:|---:|---:|---:|
| Fenerbahce v AS Roma | — | — | — | — | — | — |
| PSV Eindhoven v Shakhtar Donetsk | 1.33 | 4.05 | 1.81 | — | — | — |
| Bayern Munich v Bodo/Glimt | 1.17 | 6.91 | 1.61 | 1.18 | 6.50 | 1.66 |
| Como v RB Leipzig | — | — | — | — | — | — |
| Manchester United v Sabah FK | — | — | — | — | — | — |
| Slavia Prague v Lens | 2.96 | 1.51 | 1.83 | — | — | — |

## What could not be priced

| Match | Normal | Shadow |
|---|---|---|
| Fenerbahce v AS Roma | blocked — no Champions League history for Fenerbahce | blocked — incomplete_player_features; missing_cross_league_baseline_strength; projected_lineup_unresolved |
| PSV Eindhoven v Shakhtar Donetsk | priced | blocked — incomplete_player_features; projected_lineup_unresolved |
| Bayern Munich v Bodo/Glimt | priced | priced |
| Como v RB Leipzig | blocked — no Champions League history for Como | blocked — missing_cross_league_baseline_strength |
| Manchester United v Sabah FK | blocked — no Champions League history for Sabah FK | blocked — incomplete_player_features; missing_cross_league_baseline_strength; projected_lineup_unresolved |
| Slavia Prague v Lens | priced | blocked — incomplete_player_features |

## Strength coverage

| Match | Warning |
|---|---|
| PSV Eindhoven v Shakhtar Donetsk | Shakhtar Donetsk: stale_history_last_archive_match_596_days_ago |
| Bayern Munich v Bodo/Glimt | Bodo/Glimt: thin_history_12_archive_matches |
| Slavia Prague v Lens | Lens: stale_history_last_archive_match_1086_days_ago; Lens: thin_history_6_archive_matches; Slavia Prague: thin_history_14_archive_matches |

## Totals calibration

On 378 held-out 2024/25 and 2025/26 matches the raw matrix O/U 2.5 probability scored Brier 0.24398, with a mean Over of 70.45% against an actual 65.87% — it runs 4.58 percentage points too high on Over. The archived isotonic calibration improves Brier to 0.22964 but flattens the output: across these three fixtures it returns a narrow band regardless of how different the matches are, so it is reported as evidence about the calibration route, not as a competing price.

Model fit: 1997 Champions League matches to 2026-05-30, converged in 680 iterations.

