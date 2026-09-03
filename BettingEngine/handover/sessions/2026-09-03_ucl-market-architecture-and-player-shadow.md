# UCL market architecture handover — 2026-09-03

## Final market design

The UCL system uses one shared football foundation, with separate market-specific prediction layers:

- **1X2 model:** home win, draw and away win probabilities.
- **U/O 2.5 model:** direct total-goals probability and Over/Under selection.
- **Corner-enhanced U/O challenger:** the U/O model with rolling corner-for and corner-against features.

These are not one combined bet model. They share fixture identity, team-strength, xG and timing controls, but each market is calibrated and evaluated separately. A signal in one market must not automatically create a bet in another.

## Current U/O implementation

The rebuilt challenger uses strictly pre-match rolling xG, rolling corners, a knockout indicator, de-vigged market probabilities and a conservative 35% model / 65% market blend. The two-season archive has 378 total fixtures; SofaScore statistics currently cover 342 of them. The 2025/26 corner-enhanced test covered 186 games: Brier 0.21538 versus 0.21258 for market-only, with a small 5% edge paper result of +7.31% ROI (64 bets). This is not enough for promotion; corners remain a challenger feature.

## Player shadow status

Yes, a UCL player-shadow framework exists and mirrors the EPL/EFL design, including availability, expected minutes, player impact, replacement level and suspension fields. It is **shadow-only** and cannot alter production prices. Current status is pending data: `ml/football/reports/ucl_player_shadow.json` records 0 timestamped UCL player events. The next gate is a timestamped player-event/appearance backfill followed by a walk-forward residual test against the team-only baseline.

## Important handover rules

Do not merge 1X2 and U/O into a single probability model. Do not promote corners or player effects based on one season or a small high-edge subset. Keep static bookmaker archives labelled `unverified_static_close` until timestamp-verified closing data is available.

Key files:

- `ml/football/ucl_recent_two_season_backtest.py` — 1X2 market backtest
- `ml/football/ucl_ou25_challenger.py` — xG-only U/O challenger
- `ml/football/ucl_ou25_corner_challenger.py` — corner-enhanced U/O challenger
- `data/ucl/xg/ucl_sofascore_match_stats.csv` — normalized corners and match statistics
- `ml/football/reports/ucl_ou25_corner_challenger_backtest.json` — latest corner test
- `ml/football/reports/ucl_player_shadow.json` — player-shadow readiness
