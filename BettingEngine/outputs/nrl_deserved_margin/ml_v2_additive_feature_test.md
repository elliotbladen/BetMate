# NRL ML v2 Additive Feature Test

## Goal

Test whether the adjusted-Elo learnings should be incorporated into the ML shadow engine as extra model features.

The additive feature matrix preserves every v1 feature and appends:

- deserved-margin Elo fields
- differences between deserved-margin Elo and original Elo
- rolling luck-debt fields

Feature matrix:

```text
ml/results/features_ml_v2.csv
```

Builder:

```text
scripts/build_nrl_ml_v2_features.py
```

## Result

Adding the new columns directly to the XGBoost model did not work.

| Run | H2H |
| --- | ---: |
| 2024 v1 baseline | 130/212 = 61.3% |
| 2024 additive all v2 features | 123/212 = 58.0% |
| 2024 dm core only | 127/212 = 59.9% |
| 2024 dm deltas only | 127/212 = 59.9% |
| 2024 luck only | 123/212 = 58.0% |
| 2024 pred delta + luck diff | 123/212 = 58.0% |
| 2024 dm pred only | 126/212 = 59.4% |

For 2025, retraining itself was unstable:

| Run | H2H |
| --- | ---: |
| 2025 saved-model baseline | 134/212 = 63.2% |
| 2025 scratch v1 trained through 2024 | 126/212 = 59.4% |
| 2025 additive all v2 features trained through 2024 | 124/212 = 58.5% |

## Read

The adjusted-Elo signal is useful when it changes the Elo timeline before prediction:

- 2024 deserved-margin Elo overlay improved to 133/212.
- 2025 label max Elo overlay improved to 136/212.

But the same signal does not work as raw additive columns in the current XGBoost setup. The likely issue is sparse history: these features only have real stat-derived history from 2023 onward, while the model trains across 2009 onward.

## Recommendation

Do not replace the production ML v1 feature set with the additive v2 columns yet.

The safe incorporation path is:

1. Keep ML v1 as the baseline production model.
2. Keep adjusted-Elo overlays as an optional v2 experiment/report layer.
3. For a true ML v2, first build a longer historical stats dataset or train a smaller specialist calibration model on 2022 onward only.
