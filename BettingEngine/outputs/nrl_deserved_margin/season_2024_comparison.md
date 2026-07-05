# NRL Deserved-Margin Elo Overlay

## Method

The deserved-margin model trains on detailed match stats and predicts the margin supported by the underlying stat profile.

For the 2024 test:

- Training seasons: 2022-2023.
- Training rows: 414.
- Target season: 2024.
- Target games replayed: 213.
- Matched stat files: 213/213.
- Model: standardized ridge regression.
- Inputs: process stat differentials only, excluding direct scoring fields such as points, tries, goals and field goals.

The season is replayed round by round. Before each match, the ML shadow engine receives the current pre-game Elo features. After the match, Elo is updated using a blended result:

```text
blended_score = (1 - blend_weight) * actual_result + blend_weight * deserved_result
```

The best 2024 setting from the first sweep was:

```text
blend_weight = 0.50
margin_scale = 6
```

## 2024 Results

| Run | H2H | High confidence | Margin MAE |
| --- | ---: | ---: | ---: |
| ML v1 baseline | 130/212 = 61.3% | 96/145 = 66.2% | 14.68 |
| Label Elo v2 default | 131/212 = 61.8% | 92/138 = 66.7% | 14.51 |
| Deserved-margin best | 133/212 = 62.7% | 93/136 = 68.4% | 14.43 |

The deserved-margin overlay improved 2024 by:

- +3 picks over ML v1 baseline.
- +2 picks over the label-based Elo v2 overlay.
- +2.2 percentage points in high-confidence accuracy versus ML v1 baseline.
- 0.25 points better margin MAE versus ML v1 baseline.

## 2024 Pick Changes

The best deserved-margin overlay changed seven H2H picks:

| Date | Match | Actual winner | Baseline pick | Deserved-margin pick | Result |
| --- | --- | --- | --- | --- | --- |
| 2024-03-31 | Sharks vs Raiders | Sharks | Sharks | Raiders | lost one |
| 2024-05-11 | Storm vs Sharks | Sharks | Storm | Sharks | gained one |
| 2024-06-14 | Raiders vs Cowboys | Cowboys | Raiders | Cowboys | gained one |
| 2024-06-29 | Storm vs Raiders | Storm | Storm | Raiders | lost one |
| 2024-08-03 | Sharks vs Rabbitohs | Sharks | Rabbitohs | Sharks | gained one |
| 2024-08-04 | Bulldogs vs Raiders | Bulldogs | Raiders | Bulldogs | gained one |
| 2024-08-10 | Dragons vs Bulldogs | Bulldogs | Dragons | Bulldogs | gained one |

Net: +5 gained, -2 lost = +3 picks.

## Blend Sweep

| Blend / scale | H2H |
| --- | ---: |
| w0.50 / scale 6 | 133/212 = 62.7% |
| w0.40 / scale 6 | 132/212 = 62.3% |
| w0.50 / scale 8 | 132/212 = 62.3% |
| w0.20 / scale 6 | 131/212 = 61.8% |
| w0.30 / scale 6 | 131/212 = 61.8% |
| w0.50 / scale 10 | 131/212 = 61.8% |

The broader sweep showed that lower margin scales worked better. That means the model benefited when strong deserved margins were allowed to move the Elo result update materially.

## 2025 Sanity Check

Using the 2024-best setting frozen:

- Training seasons: 2022-2024.
- Target season: 2025.
- Saved ML models used for fair comparison.
- Result: 134/212 = 63.2%.

That ties the regenerated saved-model 2025 baseline and does not beat the old 63.4% reference.

## Read

This is the first Elo adjustment that gave a meaningful 2024 lift. It did not transfer cleanly to 2025 with the first frozen setting, so it should not be treated as solved. The signal is still useful: deserved margin gives a continuous "scoreboard lied by this many points" measure, which is better information than binary lucky-winner labels.

The next step should be to add deserved-margin fields as ML features alongside original Elo, rather than using deserved margin only to replace Elo updates.
