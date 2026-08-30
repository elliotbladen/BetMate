# NFL Step 2 — Baseline models

## Outcome

Step 2 now has reproducible Elo, ridge-margin and ridge-total baselines. The
evaluation is expanding-season rolling origin: train through the prior season,
predict the next season, then expand. Tests cover 2019–2024 (1,599 games). The
2025 final vault was not fitted, predicted, scored or inspected.

## Development scoreboard

| Predictor | Games | MAE | RMSE |
|---|---:|---:|---:|
| EPA ridge margin | 1,599 | 10.31 | 13.26 |
| Elo margin | 1,599 | 10.58 | 13.55 |
| Closing spread | 1,595 | 9.83 | 12.79 |
| Opening spread | 1,595 | 10.00 | 12.99 |
| EPA ridge total | 1,599 | 10.77 | 13.63 |
| Closing total | 1,595 | 10.35 | 13.06 |
| Opening total | 1,595 | 10.54 | 13.28 |

The EPA margin baseline improves on Elo by 0.27 MAE, so play efficiency adds
signal beyond a win/loss strength tracker. It does not beat the market. The
ridge fair margin is 2.84 points from the close on average, versus 1.44 points
for the opener. The ridge total is 2.69 points from the close, versus 1.69 for
the opener. These models are reference hurdles, not betting engines.

## Inputs and leakage controls

Only information knowable before kickoff is used: shifted home/away offensive
and defensive passing/rushing EPA, success, early-down efficiency, explosive
rate, sack rate, rest, division status, week and fixed rule-era flags. The
regression learns the opposing offense/defence relationship from paired home
and away inputs. Scores and betting prices are labels/evaluation fields only.

The 2025 rule allowing a trailing team to declare an onside kick at any time is
encoded from 2025 onward. The 2026 onside alignment revision has its own flag.
Actual declarations, attempts and recoveries are prohibited pre-game features.
Because development ends in 2024, these new flags do not manufacture historical
evidence; they become measurable through frozen prospective predictions.

## Frozen artefacts

- Code: `ml/nfl/baselines.py`, `ml/nfl/rule_eras.py`
- Configuration: `ml/nfl/config.yaml` under `step2_baselines`
- Machine report: `ml/nfl/reports/step2_baselines.json`
- Fold predictions: `data/nfl/predictions/step2_rolling_origin.csv`
- Feature store: 3,151 unique regular-season games, 2014–2025
- Verification: 15 architecture tests pass; the data contract passes

## Interpretation and next gate

The baseline gives later tiers something honest to beat. Quarterback/personnel,
continuity, venue, schedule, weather and matchup components must improve these
out-of-sample results through an ablation, not merely fit historical noise. No
staking or production promotion is authorised by Step 2.
