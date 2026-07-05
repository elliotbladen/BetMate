# NRL 2024 ML v1 vs Elo v2 Overlay

## Baseline

- Model: ML v1 feature set
- Train: 2009-2023
- Test: 2024
- Result: 130/212 = 61.3%
- Draws excluded: 1
- High confidence: 96/145 = 66.2%

## Elo v2 Overlay

Only the 2024 live Elo-derived features were replaced:

- `elo_diff`
- `home_elo_win_prob`
- `elo_predicted_margin`

The model was still trained on 2009-2023 v1 features. The 2024 season was replayed with dampened Elo updates on the 36 labelled v2 games.

Default multipliers:

- `stat_reversal`: 0.50
- `margin_exaggeration`: 0.70
- `close_game_tension`: 0.80
- `report_context_tension`: 0.80

Result:

- H2H: 131/212 = 61.8%
- Gain vs v1: +1 correct pick, +0.5 percentage points
- High confidence: 92/138 = 66.7%
- Margin MAE: 14.51 pts, improved from 14.68

## Multiplier Sweep

| Variant | H2H | Hit Rate | High Conf | Multipliers |
| --- | ---: | ---: | ---: | --- |
| default | 131/212 | 61.8% | 92/138 = 66.7% | stat=0.50, margin=0.70, close=0.80, report=0.80 |
| balanced | 131/212 | 61.8% | 92/138 = 66.7% | stat=0.40, margin=0.65, close=0.75, report=0.75 |
| soft | 130/212 | 61.3% | 95/142 = 66.9% | stat=0.70, margin=0.85, close=0.90, report=0.90 |
| aggressive | 130/212 | 61.3% | 92/136 = 67.6% | stat=0.25, margin=0.50, close=0.65, report=0.65 |
| max | 129/212 | 60.8% | 91/135 = 67.4% | stat=0.00, margin=0.25, close=0.50, report=0.50 |
| reversal only | 129/212 | 60.8% | 92/137 = 67.2% | stat=0.40, margin=1.00, close=1.00, report=1.00 |

## Pick Changes

The default v2 overlay changed five H2H picks:

| Date | Match | Actual | v1 Pick | v2 Pick | Result |
| --- | --- | --- | --- | --- | --- |
| 2024-03-31 | Sharks vs Raiders | Sharks | Sharks | Raiders | v2 lost one |
| 2024-04-11 | Knights vs Roosters | Roosters | Knights | Roosters | v2 gained one |
| 2024-06-14 | Raiders vs Cowboys | Cowboys | Raiders | Cowboys | v2 gained one |
| 2024-06-22 | Titans vs Warriors | Titans | Titans | Warriors | v2 lost one |
| 2024-09-14 | Storm vs Sharks | Storm | Sharks | Storm | v2 gained one |

Net: +3 gained, -2 lost = +1 pick.

The max v2 overlay also changed five H2H picks:

| Date | Match | Actual | v1 Pick | Max v2 Pick | Result |
| --- | --- | --- | --- | --- | --- |
| 2024-03-31 | Sharks vs Raiders | Sharks | Sharks | Raiders | v2 lost one |
| 2024-04-11 | Knights vs Roosters | Roosters | Knights | Roosters | v2 gained one |
| 2024-06-14 | Raiders vs Cowboys | Cowboys | Raiders | Cowboys | v2 gained one |
| 2024-06-22 | Titans vs Warriors | Titans | Titans | Warriors | v2 lost one |
| 2024-06-29 | Storm vs Raiders | Storm | Storm | Raiders | v2 lost one |

Net: +2 gained, -3 lost = -1 pick.

## Read

The signal is positive but small at the default setting. The default overlay beats the 2024 v1 baseline by one game without retraining the model on v2 features, but the max setting drops one game below baseline. That makes 2024 different from 2025: aggressive correction helped 2025, but overcorrected 2024.
