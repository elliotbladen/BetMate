# UCL 2026/27 MD1 — Real Madrid v Inter

**Kickoff:** 8 September 2026, 21:00 CEST (UEFA-confirmed league-phase fixture).

## Market snapshot

Source snapshot: SportyTrader/market comparison, 3 September 2026.

- 1X2: Real Madrid 1.58, Draw 4.34, Inter 5.25.
- O/U 2.5: Over 1.49, Under 2.40.

## Base model

Shared UCL Dixon–Coles + Elo, fit only to historical UCL data through the cutoff:

| Outcome | Model probability | Fair odds | No-vig market probability | Probability edge |
|---|---:|---:|---:|---:|
| Real Madrid | 47.93% | 2.09 | 60.06% | -12.12% |
| Draw | 22.89% | 4.37 | 21.87% | +1.03% |
| Inter | 29.17% | 3.43 | 18.08% | +11.10% |
| Over 2.5 | 77.62% | 1.29 | 61.70% | +15.92% |
| Under 2.5 | 22.38% | 4.47 | 38.30% | -15.92% |

## Tier audit

- **T0 data quality:** FAIL for live promotion. Current-season injury, lineup, referee and verified closing-price feeds are not loaded.
- **T1 structural model:** active historical base price.
- **T2 personnel/player shadow:** shadow framework exists, but no timestamped UCL player events; no adjustment applied.
- **T3 form/continuity:** historical form adjustment applied: Real Madrid +0.048 xG, Inter -0.048 xG.
- **T4 league-phase incentive:** diagnostic only; no adjustment applied.
- **T5 knockout/aggregate state:** not applicable (league phase).
- **T6 referee:** unavailable; no adjustment.
- **T7 schedule/travel/rest:** no live verified adjustment.
- **T8 new-team/competition prior:** no adjustment.
- **T9 manager/emotional/news:** unavailable; no adjustment.

## Decision

The raw model flags Inter and Over 2.5, but both edges are unusually large and the U/O model has not passed live promotion. **No live bet is approved from this snapshot.** If used for a small manual experiment, it must be explicitly recorded as an unvalidated paper/shadow stake, with the final lineup and price rechecked before kickoff.
