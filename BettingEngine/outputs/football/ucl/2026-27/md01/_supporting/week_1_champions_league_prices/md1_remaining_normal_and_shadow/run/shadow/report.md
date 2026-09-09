# Week 1 Champions League — normal and player shadow

Research comparison only. Normal is the saved injury/form/rest price; shadow adds a UCL-trained player residual from the sourced projected XI. Decimal fair odds, 90 minutes.

| Match | Normal H | D | A | Shadow H | D | A |
|---|---:|---:|---:|---:|---:|---:|
| Fenerbahce v AS Roma | — | — | — | — | — | — |
| PSV Eindhoven v Shakhtar Donetsk | 1.97 | 4.36 | 3.81 | — | — | — |
| Bayern Munich v Bodo/Glimt | 1.28 | 7.90 | 10.77 | 1.32 | 7.33 | 9.60 |
| Como v RB Leipzig | — | — | — | — | — | — |
| Manchester United v Sabah FK | — | — | — | — | — | — |
| Slavia Prague v Lens | 1.82 | 3.78 | 5.41 | — | — | — |

## Holdout evidence

Trained on 93 eligible 2024/25 matches; tested on 126 eligible 2025/26 matches. Goal MAE: 1.168107 normal, 1.162342 shadow. 1X2 RPS: 0.198773 normal, 0.194995 shadow. Lower is better. No production approval.

## Tiers

T0 validates inputs/cutoffs and blocks missing strengths or player identities. T1 is the frozen converged DC/Elo strength. T2 now uses identified projected players, rolling statistics and minutes, alongside the baseline positional absences. T3 retains domestic form/rest and records player workload. T4 is neutral for MD1. T5 is not applicable. T6 referee/weather, T7 market disagreement and T8 confluence remain diagnostic/unpopulated; they do not change prices.

## Limits

- Predicted lineups are not confirmed XIs.
- Baseline remains the saved researched 1X2 price, including positional injuries and domestic form/rest.
- Positional injury effects and player residuals can overlap; chronological baseline lacks historical injury input.
- O/U 2.5 is carried through from whatever totals the baseline published, shifted by the shadow Poisson odds ratio; it is not the separate market-anchored U/O challenger and inherits the baseline totals calibration warning in full.
- Referee/weather, pressing/travel/rotation, market quotes and confluence are not numerical adjustments.
- No market EV, betting signals, stakes or placements.
- One UCL holdout season; no live betting promotion.
- Training uses final historical XIs; live use of projected XIs is a different information regime.
- Domestic history currently starts January 2026, so feature coverage differs between seasons.
- Historical baseline form/rest is UCL-only; live researched baseline has domestic form/rest and positional injuries.
- ID-based nominal minutes replace inherited 65/25 fallbacks; same 56 features, Ridge alpha/solver and additive cap.

Per-player IDs, rolling-history counts, expected-minute estimates, workload, sources, blockers and all 56 inputs are saved in prices.json.
