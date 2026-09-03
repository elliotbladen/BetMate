# Champions League reworked architecture and five-step backtest plan

The UCL build is now data-first. Openfootball supplies public-domain UEFA
fixtures, stages and results; Football-Data UK supplies domestic results,
statistics and available odds. The two sources are archived separately and
joined only through the canonical club registry.

The immediate target is an honest match-market backtest. Qualification and
outright markets come after the league-phase graph and standings simulator have
passed their own checks. Modern league-phase seasons (2024/25 onward) are never
mixed with legacy group-stage seasons for qualification evaluation.

## Five steps

1. **Ingest and archive:** retrieve UEFA and domestic files, save raw copies,
   checksums, source dates and coverage notes.
2. **Normalize and join:** resolve club aliases, stages, seasons, scores and
   format eras; quarantine unresolved rows.
3. **Fit match forecasts:** produce expanding-window H2H, Asian handicap and
   totals prices using cross-league strength, with odds excluded from features.
4. **Validate tournament state:** validate modern draw graphs and compare table
   and knockout simulations with observed UEFA standings and ties.
5. **Publish backtest:** produce row-level predictions and metrics, opening/
   closing comparisons and CLV where available, then freeze a prospective card.

No staking decision is part of this five-step build.
