# EPL/EFL opening and closing audit — Weeks 1 and 2

Generated: 2 September 2026  
Market reference: Football-Data average opening and average closing odds  
Probabilities: market odds de-vigged within 1X2 or O/U 2.5

Definitions:

- **Model edge at open/close:** model probability minus no-vig market
  probability, in percentage points.
- **Market-move CLV:** opening odds divided by closing odds minus one. Positive
  means the selected side shortened.
- **Reference-price CLV:** saved/reference price divided by average closing odds
  minus one. Positive means the recorded price beat the average close.

## Week 1 — broader 10%+ EV report

| League | Bets | Model edge at open | Model edge at close | Avg market move | Shortened | Reference price vs close | Beat close |
|---|---:|---:|---:|---:|---:|---:|---:|
| EPL | 9 | +9.02pp | +9.36pp | -0.99% | 5/9 | +1.93% | 6/9 |
| EFL Championship | 14 | +8.82pp | +8.38pp | +3.19% | 6/14 | 0.00% | Not independent |
| **Combined** | **23** | **+8.90pp** | **+8.76pp** | **+1.56%** | **11/23** | **+0.75%** | **6/23*** |

`*` The combined beat-close count is not a fair captured-price score. Week 1's
EFL reference prices were the same average closing quotes used by the earlier
grading report, so their 0% is mechanical. There is no independent placement
ledger for those 14 rows.

Week 1 interpretation:

- The model showed a large theoretical edge at both open and close.
- The market gave weak confirmation: only 11 of 23 selections shortened.
- EFL selections shortened by 3.19% on average, but fewer than half shortened.
- EPL's recorded reference quotes beat the current average close on 6 of 9,
  averaging +1.93%; source/book differences mean this is indicative, not a
  verified placement-ledger result.

## Week 2 — frozen 20%+ EV lists

| League | Bets | Model edge at open | Model edge at close | Avg market move | Shortened | Saved price vs close | Beat close |
|---|---:|---:|---:|---:|---:|---:|---:|
| EPL | 6 | +11.89pp | +11.99pp | -1.44% | 3/6 | **+10.22%** | **5/6** |
| EFL Championship | 3 | +17.13pp | +18.22pp | -3.40% | 2/3 | **-3.25%** | **1/3** |
| **Combined** | **9** | **+13.64pp** | **+14.07pp** | **-2.09%** | **5/9** | **+5.73%** | **6/9** |

Week 2 interpretation:

- The nine saved/reference prices beat the average close 6 times and averaged
  +5.73% price CLV.
- EPL price capture was strong: 5 of 6 beat the average close, +10.22% mean.
- EFL price capture was poor overall: only Wrexham beat the close; the three
  selections averaged -3.25%.
- Norwich v Burnley was the largest EFL warning: saved Burnley 2.83 versus an
  average close of 3.43, or **-17.49% price CLV**.
- The market itself did not broadly confirm the selections: only 5 of 9
  shortened and selection odds drifted 2.09% on average.
- The model's theoretical edge becoming larger at close is not automatically a
  positive. Alongside the -63.11% result, persistent 14pp closing edges may
  indicate probability overconfidence or a structural disagreement with the
  market.

## Week 2 individual saved-price CLV

| League | Selection | Saved | Average open | Average close | Saved vs close |
|---|---|---:|---:|---:|---:|
| EPL | Fulham win v Sunderland | 3.46 | 2.96 | 3.28 | +5.49% |
| EPL | Brentford win v Leeds | 2.94 | 2.67 | 2.48 | +18.55% |
| EPL | Everton win v Bournemouth | 3.85 | 3.41 | 3.24 | +18.83% |
| EPL | Newcastle win v Tottenham | 3.32 | 2.88 | 3.06 | +8.50% |
| EPL | Aston Villa win v Arsenal | 6.50 | 5.99 | 6.54 | -0.61% |
| EPL | Tottenham–Newcastle Over 2.5 | 1.769 | 1.64 | 1.60 | +10.56% |
| EFL | Burnley win v Norwich | 2.83 | 3.00 | 3.43 | -17.49% |
| EFL | Wrexham win v Birmingham | 2.38 | 2.20 | 2.18 | +9.17% |
| EFL | Preston win v Charlton | 3.45 | 3.55 | 3.50 | -1.43% |

The Aston Villa price remained flagged as requiring source verification, and
the Tottenham Over remained matrix-verification-required. The three EFL rows
were frozen selections, but their final +6 matrix qualification was not
preserved.

## Bottom line

- Week 1 was profitable but offered only weak market-movement confirmation.
- Week 2 lost heavily despite positive EPL captured-price CLV.
- The EPL price-taking process looks better than the latest results.
- The EFL prices and displayed probability edges require closer calibration
  review, particularly Burnley at Norwich.
- Continue separating realised ROI, price CLV, market movement and model edge;
  none should be presented as interchangeable evidence.
