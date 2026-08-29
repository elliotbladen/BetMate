# AFL halftime margin formula audit — 2026-08-15

## Finding

The AFL model has the same baseline defect found in NRL. It currently calculates
`0.55 × halftime margin + 0.45 × pregame full-game margin`. This allows points
already scored to regress away. The correct structure forecasts remaining margin:
`current margin + expected margin over the remaining game`.

The AFL model's H2H simulation does consume its expected final margin, so H2H and
handicap are internally more coherent than the pre-fix NRL implementation. Its
uncertainty is nevertheless too narrow: the archive's second-half margin residual
SD after pregame strength is 23.93 points, while the current simulation typically
implies only about 11 points.

## Leave-one-season-out test

Dataset: 874 valid AFL matches, 2022–2026. Pregame exchange probabilities were
devigged. For every held-out season, training seasons mapped pregame log-odds to
expected full-game margin and fitted remaining second-half margin. No live deep
stats were available historically.

| Model | MAE | RMSE | Brier | Log loss | Winner accuracy |
|---|---:|---:|---:|---:|---:|
| Current fixed blend | 20.429 | 25.994 | 0.1683 | 0.5124 | 75.40% |
| Current margin + 50% pregame margin | 19.253 | 24.004 | 0.1626 | 0.4918 | 75.63% |
| Current margin + fitted remaining margin | 19.186 | 23.923 | 0.1619 | 0.4909 | 75.29% |
| Halftime exchange benchmark | — | — | 0.1627 | 0.4968 | 75.06% |

The fitted remaining-strength share was stable at approximately 0.60–0.64 of
the mapped pregame full-game margin across held-out seasons, rather than the
naive 0.50 share.

## Round 22 indicative replays

Using the current code's live adjustments but replacing only the baseline:

| Match | HT margin | Current expected margin | Corrected simple margin |
|---|---:|---:|---:|
| Melbourne–Fremantle | Melbourne -3 | Melbourne -5.1 | Melbourne -7.9 |
| GWS–Gold Coast | GWS -10 | GWS -1.0 | GWS -4.8 |
| West Coast–Collingwood | West Coast -6 | West Coast -14.4 | West Coast -18.4 |

These are diagnostic replays, not replacement saved prices.

## Additional defects

1. Inside-50, clearance and clanger signals affect the dynamic regression factor
   and are then added directly again, creating double counting.
2. Accuracy comments acknowledge near-zero H1-to-H2 persistence, yet the engine
   still projects a 15% accuracy trend. Current points must remain; future kicking
   should not receive an unvalidated continuation adjustment.
3. Process-stat coefficients and the six-point cap have not been fitted on
   historical halftime deep stats.
4. The uncertainty distribution must be empirically calibrated; the current
   simulation is materially overconfident.

## Research alignment

- O'Shaughnessy's AFL match-equity framework uses current margin, time remaining,
  field position and possession state.
- The Matter of Stats in-running model predicts remaining margin from remaining
  fraction and pregame margin, then adds it to current margin; it is calibrated
  on 2,879 V/AFL matches using held-out years.
- Published AFL performance-indicator research supports relative inside-50,
  metres-gained, possession and turnover features, but not arbitrary duplicated
  weights.

