# AFL halftime totals architecture study — 2026-08-15

## Dataset and validation

875 valid AFL matches, 2022–2026. Every season was held out in turn. Target was
the final total; all candidate models used halftime score information only,
because the archive contains no historical pregame total, deep halftime stats or
halftime totals prices.

| Model | MAE | RMSE | Bias | Within 6 | Within 12 |
|---|---:|---:|---:|---:|---:|
| Current five bins | 15.480 | 19.738 | +0.109 | 29.0% | 48.9% |
| Continuous score-only mean | 15.499 | 19.785 | +0.089 | 27.3% | 47.3% |
| Compact score/shots/accuracy ridge | 15.457 | 19.726 | +0.092 | 25.7% | 48.2% |
| Conditional empirical median | 15.484 | 19.811 | -0.485 | 29.1% | 48.5% |

The compact ridge improves MAE by only 0.023 points, which is immaterial and not
stable enough to replace the current bins.

## Relationships

- H1 total versus H2 total correlation: +0.111.
- H1 scoring shots versus H2 total correlation: +0.151.
- H1 goal accuracy versus H2 total correlation: +0.003.
- H2 points: mean 84.94, median 84.0, SD 19.85.

AFL does not show the NRL-style low-score bounce-back assumption. Higher first-
half pace weakly persists. Shot volume is more useful than accuracy, while
accuracy has effectively zero predictive relationship with second-half scoring.

## Decision

Do not discard the current five-bin score-state baseline. It is competitive with
all score-only challengers. Do adopt the useful parts of the NRL v3 architecture:

1. retain the score-state baseline;
2. blend a genuine pregame total prior once archived;
3. use an empirical conditional distribution to price over/under probability and
   distinguish the mean from the 50/50 betting line;
4. add capped pace/opportunity evidence from scoring shots, inside-50s, repeat
   entries, turnovers, injuries and weather;
5. capture 10/20/30/HT stats and market totals for forward calibration;
6. promote process weights only after out-of-sample improvement over both the
   current bins and captured market line.

This is an architectural upgrade, not evidence for a complex model today. The
historical score-only evidence does not justify replacing the bins, and the
absence of historical pregame/live/closing totals prevents a defensible CLV or
probability-calibration test.

