# Champions League Step 9 — format-aware backtest harness

The backtest harness now scores match H/D/A forecasts with RPS, Brier score,
log loss and accuracy, and scores league-phase top-eight/top-24 probabilities
with Brier and calibration error. Modern 36-team league-phase seasons
(2024/25 onward) are kept separate from older group-stage seasons.

The production status now has 1,997 sourced openfootball match rows loaded, but
predictions are still pending. Openfootball dates are date-only and contain no
odds or xG, so those limitations remain explicit. Only
expanding-window forecasts may enter the evaluation; final standings, later
lineups and closing odds remain prohibited inputs.
