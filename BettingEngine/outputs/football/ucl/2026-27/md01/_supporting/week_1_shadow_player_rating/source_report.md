# Week 1 Champions League — normal and player shadow

Research comparison only. Normal is the saved injury/form/rest price; shadow adds a UCL-trained player residual from the sourced projected XI. Decimal fair odds, 90 minutes.

| Match | Normal H | D | A | Shadow H | D | A |
|---|---:|---:|---:|---:|---:|---:|
| AEK Athens v LASK | — | — | — | — | — | — |
| Club Brugge v Aston Villa | 2.57 | 3.30 | 3.24 | 2.53 | 3.51 | 3.12 |
| Borussia Dortmund v Villarreal | 1.67 | 4.13 | 6.27 | 1.68 | 4.29 | 5.77 |
| Porto v Manchester City | 3.66 | 3.54 | 2.25 | 4.07 | 3.68 | 2.07 |
| Lille v Real Betis | — | — | — | — | — | — |
| Real Madrid v Inter | 3.01 | 3.59 | 2.57 | 2.59 | 3.59 | 2.99 |
| Barcelona v Feyenoord | 1.46 | 5.62 | 7.19 | 1.48 | 5.69 | 6.73 |
| Stuttgart v Viking | — | — | — | — | — | — |
| Liverpool v Atlético de Madrid | 1.63 | 4.46 | 6.11 | 1.65 | 4.60 | 5.71 |
| Paris Saint-Germain v Slovan Bratislava | 1.17 | 10.97 | 19.11 | 1.15 | 11.91 | 21.26 |
| Sporting CP v Galatasaray | 1.59 | 4.74 | 6.21 | 1.59 | 4.59 | 6.49 |
| Napoli v Arsenal | 4.22 | 4.07 | 1.93 | 5.17 | 4.29 | 1.74 |

## Holdout evidence

Trained on 93 eligible 2024/25 matches; tested on 126 eligible 2025/26 matches. Goal MAE: 1.168107 normal, 1.162342 shadow. 1X2 RPS: 0.198773 normal, 0.194995 shadow. Lower is better. No production approval.

## Tiers

T0 validates inputs/cutoffs and blocks missing strengths or player identities. T1 is the frozen converged DC/Elo strength. T2 now uses identified projected players, rolling statistics and minutes, alongside the baseline positional absences. T3 retains domestic form/rest and records player workload. T4 is neutral for MD1. T5 is not applicable. T6 referee/weather, T7 market disagreement and T8 confluence remain diagnostic/unpopulated; they do not change prices.

## Limits

- Predicted lineups are not confirmed XIs.
- Baseline remains the saved researched 1X2 price, including positional injuries and domestic form/rest.
- Positional injury effects and player residuals can overlap; chronological baseline lacks historical injury input.
- Totals withheld: the separate live U/O champion has not been integrated.
- Referee/weather, pressing/travel/rotation, market quotes and confluence are not numerical adjustments.
- No market EV, betting signals, stakes or placements.
- One UCL holdout season; no live betting promotion.
- Training uses final historical XIs; live use of projected XIs is a different information regime.
- Domestic history currently starts January 2026, so feature coverage differs between seasons.
- Historical baseline form/rest is UCL-only; live researched baseline has domestic form/rest and positional injuries.
- ID-based nominal minutes replace inherited 65/25 fallbacks; same 56 features, Ridge alpha/solver and additive cap.

Per-player IDs, rolling-history counts, expected-minute estimates, workload, sources, blockers and all 56 inputs are saved in prices.json.
