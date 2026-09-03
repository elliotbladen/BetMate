# All football model results

This directory contains all frozen normal-engine EPL and Championship Week 1-2
predictions matched to results and de-vigged Football-Data opening/closing
markets.

League reports:

- `epl_all_model_results.md`
- `efl_championship_all_model_results.md`
- `epl_clv_roi_all_model_results.md`
- `efl_championship_clv_roi_all_model_results.md`

Machine-readable summary:

- `summary_all_model_results.csv`
- `clv_roi_summary_all_model_results.csv`
- `opening_edge_portfolio_all_predictions.csv`

Detailed files are split by league, week and market. Each 1X2 file contains all
three outcome probabilities per match. Each O/U file contains both Over and
Under probabilities. `match_scores` files contain RPS/Brier, log loss and
accuracy comparisons against opening and closing markets.

Coverage gaps are preserved rather than backfilled after results:

- EPL Week 2: Coventry v Hull missing frozen prediction.
- Championship Week 2: Derby v Cardiff missing frozen prediction.

Player-shadow outputs are excluded. These reports evaluate only the normal
engines used for production decisions.
