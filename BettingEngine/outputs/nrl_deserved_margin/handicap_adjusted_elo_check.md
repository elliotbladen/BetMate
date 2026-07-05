# NRL Adjusted Elo Handicap Check

## Scope

This checks whether adjusted Elo improves handicap quality through the model margin.

The local 2025 odds import does not contain a usable season-wide handicap market. It has only one handicap match, so this is not a true ATS check versus market lines.

Instead, this checks the model's fair handicap line:

- margin MAE: `abs(actual_margin - ml_margin)`
- RMSE
- bias: `ml_margin - actual_margin`
- within 6 / 10 / 14 points of actual margin
- actual home/away performance versus the model's own fair line

## Results

| Run | Margin MAE | RMSE | Bias | Within 6 pts | Within 10 pts | Within 14 pts | Actual vs model line |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2024 baseline | 14.68 | 18.21 | -0.13 | 53/213 | 92/213 | 124/213 | 104 home / 109 away |
| 2024 label default | 14.51 | 17.98 | -0.15 | 51/213 | 92/213 | 126/213 | 104 home / 109 away |
| 2024 label max | 14.56 | 17.97 | -0.31 | 48/213 | 88/213 | 126/213 | 107 home / 106 away |
| 2024 deserved best | 14.43 | 17.92 | -0.20 | 53/213 | 93/213 | 126/213 | 104 home / 109 away |
| 2025 saved baseline | 14.20 | 18.05 | -1.79 | 54/213 | 97/213 | 123/213 | 114 home / 99 away |
| 2025 label max | 14.05 | 17.92 | -1.87 | 55/213 | 100/213 | 127/213 | 113 home / 100 away |
| 2025 deserved frozen | 14.15 | 18.03 | -1.84 | 53/213 | 98/213 | 124/213 | 114 home / 99 away |

## Read

Adjusted Elo gives a small handicap/margin improvement, but not a major one.

Best 2024 movement:

```text
14.68 -> 14.43 MAE
18.21 -> 17.92 RMSE
```

Best 2025 movement:

```text
14.20 -> 14.05 MAE
18.05 -> 17.92 RMSE
```

That supports the same conclusion as H2H: adjusted Elo has some signal, but it is not enough by itself to transform the handicap model.

For a real handicap betting test, we need season-wide closing handicap lines. Without those, we can only judge whether the model's fair spread became more accurate.
