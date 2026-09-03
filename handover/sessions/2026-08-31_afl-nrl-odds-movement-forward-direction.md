# AFL/NRL odds-movement direction for next season

Date: 31 August 2026

## Agreed direction

Use the saved research assignment as the forward design brief:

- `research/afl_nrl_odds_movement_ml_and_next_season_plan.md`
- Recover and preserve the raw Mac odds-snapshot archive.
- Resume reliable collection before Round 1 and monitor freshness/API failures.
- Keep three layers separate: fundamental pricing, market/movement forecasting, and betting decisions.
- Use the normal production engine as the owner of live betting probabilities.
- Keep experimental/player/ML shadows comparison-only until they pass prospective promotion gates.
- Build movement ML first around closing-line prediction, expected CLV and entry timing—not direct match-result mining from repeated snapshots.
- Split every train/test evaluation by match and chronologically to prevent snapshot leakage.
- Rebuild AFL's margin/H2H spine around one calibrated margin distribution.
- Retain the useful NRL core, repair H2H calibration and residual uncertainty, and enforce disciplined singles-only staking rules.
- Follow the NFL-style approach to explicit player availability, uncertainty, immutable point-in-time data and evidence-based feature promotion.

This is the baseline for next-season AFL and NRL planning unless the user explicitly changes it.

## 3 September 2026 extension

The market-timing backtest and timestamped news-snapshot design are saved in `handover/sessions/2026-09-03_afl-nrl-bet-timing-and-news-snapshots.md`. That handover extends this direction with the agreed news sources, source hierarchy, point-in-time schema, leakage controls, backtest targets and implementation sequence.
