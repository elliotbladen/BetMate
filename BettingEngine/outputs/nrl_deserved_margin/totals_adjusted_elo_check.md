# NRL Adjusted Elo Totals Check

## Scope

This checks whether the adjusted Elo overlays changed the ML total prediction quality.

There is no market totals line in these season backtest CSVs, so this is not betting over/under accuracy versus market. It is only:

- total MAE: `abs(actual_total - ml_total)`
- total bias: `ml_total - actual_total`
- actual over/under versus the model's own total line

## Results

| Run | Total MAE | Bias | Within 6 pts | Within 10 pts | Actual O/U vs ML line |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024 baseline | 11.31 | -1.92 | 77/213 | 109/213 | 118 over / 95 under |
| 2024 label default | 11.32 | -1.94 | 78/213 | 109/213 | 119 over / 94 under |
| 2024 label max | 11.25 | -1.93 | 76/213 | 111/213 | 119 over / 94 under |
| 2024 deserved best | 11.26 | -1.95 | 76/213 | 110/213 | 120 over / 93 under |
| 2025 saved baseline | 11.34 | -2.33 | 73/213 | 117/213 | 107 over / 106 under |
| 2025 label max | 11.35 | -2.31 | 71/213 | 117/213 | 107 over / 106 under |
| 2025 deserved frozen | 11.37 | -2.36 | 73/213 | 115/213 | 107 over / 106 under |

## Read

Adjusted Elo did not materially improve totals.

The best 2024 total MAE change was tiny:

```text
11.31 -> 11.25
```

The 2025 total MAE got slightly worse:

```text
11.34 -> 11.35 / 11.37
```

The model total line also has a consistent low bias in both seasons, meaning the ML total is generally too low:

```text
2024 baseline bias: -1.92
2025 baseline bias: -2.33
```

For totals, the better next test is likely not adjusted Elo. It is a direct totals correction layer using pace, weather, referee, team attack/defence form, and recent scoring environment.
