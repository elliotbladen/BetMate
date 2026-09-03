# Champions League Step 10 — first real expanding-window backtest

The imported openfootball match history is now connected to an expanding-window
Elo/score baseline. Each match is forecast using only earlier rows in the
archive; ratings and scoring rates update only after the observed result.

The run covers 1,997 matches from 2011/12 through 2025/26. Modern league-phase
seasons (2024/25 and 2025/26) are reported separately from legacy group-stage
seasons. H/D/A RPS, Brier, log loss and accuracy are calculated without odds,
xG or future standings.

This is the first genuine UCL result, but it is a baseline—not the finished
cross-league model. The source has date-only timestamps and no xG or bookmaker
prices. Qualification and knockout-state calibration still require their own
walk-forward layers.
