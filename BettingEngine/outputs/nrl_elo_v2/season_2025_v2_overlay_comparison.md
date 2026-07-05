# NRL 2025 ML v1 vs Elo v2 Overlay

## Setup

- Baseline reference: saved ML shadow engine models in `ml/models`.
- Target season: 2025.
- V2 method: replayed 2025 round by round, using pre-game Elo features for predictions and applying dampened Elo updates only after each match.
- Labels: `outputs/nrl_elo_v2/season_2025_labels.csv`.
- V2 Elo feature file: `ml/results/features_elo_v2_overlay_2025.csv`.
- Very-soft V2 Elo feature file: `ml/results/features_elo_v2_overlay_2025_very_soft.csv`.
- Max V2 Elo feature file: `ml/results/features_elo_v2_overlay_2025_max.csv`.

## Results

| Run | H2H | High confidence | Medium confidence | Toss-up | Margin MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Historical saved report (`results/2025_ml_backtest.txt`) | 135/213 = 63.4% | n/a | n/a | n/a | n/a |
| Regenerated saved-model baseline | 134/212 = 63.2% | 65/93 = 69.9% | 47/82 = 57.3% | 22/37 = 59.5% | 14.20 |
| Default V2 overlay | 133/212 = 62.7% | n/a | n/a | n/a | n/a |
| Very-soft V2 overlay | 134/212 = 63.2% | 64/92 = 69.6% | 48/83 = 57.8% | 22/37 = 59.5% | 14.15 |
| Max V2 overlay | 136/212 = 64.2% | 66/95 = 69.5% | 48/84 = 57.1% | 22/33 = 66.7% | 14.05 |

The regenerated reports exclude one drawn match from the H2H denominator, which is why the comparable baseline is 134/212 rather than the older 135/213 line.

## Changed Picks

Very-soft V2 changed only two H2H picks against the saved-model baseline:

| Date | Match | Actual winner | Baseline pick | V2 pick | Net |
| --- | --- | --- | --- | --- | --- |
| 2025-05-17 | Dolphins vs New Zealand Warriors | New Zealand Warriors | New Zealand Warriors | Dolphins | V2 wrong |
| 2025-09-06 | Gold Coast Titans vs Wests Tigers | Gold Coast Titans | Wests Tigers | Gold Coast Titans | V2 right |

## Conclusion

The gentle round-by-round Elo v2 overlays did not beat the 2025 saved-model baseline, but the max setting did improve overall H2H to 136/212. This is +2 picks over the regenerated saved-model baseline and +0.8 percentage points over the older 63.4% historical report.

This means the labelled "hard done by / lucky winner" adjustment has some signal, but the gain came from an aggressive setting and only six changed picks. The next viable test is to keep original Elo and add the v2 information as extra features, such as adjusted Elo diff, Elo adjustment amount, and luck/context flags, then train a true ML v2 model instead of only swapping Elo inputs.
