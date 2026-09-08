# Model vs market — full round, 1X2 and Over/Under 2.5

**Run:** 2026-09-08 · **Rounds:** EPL GW3 (4–6 Sep) and EFL Championship GW5 (5–6 Sep)  
**Driver:** `scripts/model_vs_market_football_round.py`

Lower is better on every metric. RPS is the engine's headline 1X2 metric
(3-season EPL walk-forward benchmark = 0.1335; academic reference = 0.1925).

**Model side.** EPL uses the genuinely prospective prices saved on 3 Sep
(`gw3_normal_shadow_prices_2026-09-03.json`). EFL had to be regenerated with
`scripts/price_efl_week4_2026.py` at `as_of=2026-09-05`, because the original
full-round prices were printed to stdout and never written to a file.
`price_match` filters `Date < as_of`, so there is **no lookahead** — but the
regenerated fit now includes the 1–2 Sep midweek round that football-data had
not published when the 3 Sep originals were made. Qualifier probabilities
therefore differ slightly from the saved bet file (Sheffield United 0.507 now
vs 0.522 then). Treat the EFL model column as a faithful pre-round
reconstruction, not the exact model that produced the bets.

**Market side.** football-data.co.uk consensus averages, de-vigged by
normalising 1/odds. Opening = `AvgH/AvgD/AvgA`, `Avg>2.5`; closing =
`AvgCH/AvgCD/AvgCA`, `AvgC>2.5`.

---

## EPL GW3

| Match | Score | Model RPS | Open | Close | 1X2 winner | Mdl P(Over) | Cls P(Over) | O/U winner |
|---|---:|---:|---:|---:|:--:|---:|---:|:--:|
| Ipswich v Liverpool | 0-2 | 0.1229 | 0.0832 | 0.1048 | market | 0.673 | 0.647 | market |
| Newcastle v Bournemouth | 2-2 | 0.1541 | 0.1434 | 0.1427 | market | 0.778 | 0.595 | **MODEL** |
| Brentford v Sunderland | 1-1 | 0.1530 | 0.1845 | 0.1767 | **MODEL** | 0.558 | 0.524 | market |
| Brighton v Leeds | 1-1 | 0.1499 | 0.1461 | 0.1505 | **MODEL** | 0.558 | 0.533 | market |
| Fulham v Crystal Palace | 2-3 | 0.3737 | 0.3197 | 0.3534 | market | 0.558 | 0.511 | **MODEL** |
| Man City v Coventry | 1-0 | 0.0227 | 0.0208 | 0.0236 | **MODEL** | 0.673 | 0.681 | **MODEL** |
| Nott'm Forest v Tottenham | 0-0 | 0.1372 | 0.1307 | 0.1297 | market | 0.522 | 0.511 | market |
| Hull v Aston Villa | 0-0 | 0.1386 | 0.1555 | 0.1527 | **MODEL** | 0.558 | 0.521 | market |
| Everton v Man United | 2-2 | 0.1453 | 0.1407 | 0.1556 | **MODEL** | 0.673 | 0.599 | **MODEL** |
| Arsenal v Chelsea | 2-1 | 0.1057 | 0.1172 | 0.1186 | **MODEL** | 0.673 | 0.548 | **MODEL** |

**EPL GW3 — 10 matches**

| Metric | Model | Market open | Market close | Verdict |
|---|---:|---:|---:|---|
| 1X2 RPS | **0.1503** | 0.1442 | 0.1508 | model |
| 1X2 log loss | 1.0890 | — | 1.0728 | market |
| 1X2 Brier | 0.6531 | — | 0.6516 | market |
| O/U log loss | **0.7053** | — | 0.7448 | model |
| O/U Brier | 0.2573 | — | 0.2744 | model |

Model beat the close: **6/10** on 1X2, **5/10** on O/U 2.5.

---

## EFL Championship GW5

| Match | Score | Model RPS | Open | Close | 1X2 winner | Mdl P(Over) | Cls P(Over) | O/U winner |
|---|---:|---:|---:|---:|:--:|---:|---:|:--:|
| Lincoln v Southampton | 1-1 | 0.1519 | 0.1640 | 0.1675 | **MODEL** | 0.559 | 0.571 | **MODEL** |
| Preston v Blackburn | 2-1 | 0.2689 | 0.2336 | 0.2251 | market | 0.450 | 0.499 | market |
| Stoke v Charlton | 4-0 | 0.2422 | 0.1901 | 0.1703 | market | 0.355 | 0.429 | market |
| Burnley v Bristol City | 1-2 | 0.3413 | 0.4157 | 0.3928 | **MODEL** | 0.450 | 0.519 | market |
| Millwall v Bolton | 4-0 | 0.1946 | 0.1515 | 0.1663 | market | 0.355 | 0.507 | market |
| Portsmouth v Cardiff | 2-0 | 0.2464 | 0.2371 | 0.2442 | market | 0.450 | 0.568 | **MODEL** |
| QPR v Middlesbrough | 0-1 | 0.2157 | 0.2054 | 0.2258 | **MODEL** | 0.476 | 0.567 | **MODEL** |
| Sheffield United v Norwich | 1-3 | 0.4279 | 0.2762 | 0.2695 | market | 0.476 | 0.557 | market |
| West Brom v Watford | 1-0 | 0.1661 | 0.1491 | 0.1220 | market | 0.450 | 0.523 | **MODEL** |
| West Ham v Derby | 3-0 | 0.2120 | 0.0550 | 0.0514 | market | 0.476 | 0.611 | market |
| Swansea v Wrexham | 0-0 | 0.1390 | 0.1353 | 0.1317 | market | 0.476 | 0.475 | market |
| Birmingham v Wolves | 2-2 | 0.1366 | 0.1277 | 0.1312 | market | 0.476 | 0.505 | market |

**EFL Championship GW5 — 12 matches**

| Metric | Model | Market open | Market close | Verdict |
|---|---:|---:|---:|---|
| 1X2 RPS | **0.2286** | 0.1951 | 0.1915 | market |
| 1X2 log loss | 1.0825 | — | 0.9592 | market |
| 1X2 Brier | 0.6546 | — | 0.5682 | market |
| O/U log loss | **0.7671** | — | 0.7120 | market |
| O/U Brier | 0.2860 | — | 0.2594 | market |

Model beat the close: **3/12** on 1X2, **4/12** on O/U 2.5.

---


**COMBINED — 22 matches**

| Metric | Model | Market open | Market close | Verdict |
|---|---:|---:|---:|---|
| 1X2 RPS | **0.1930** | 0.1719 | 0.1730 | market |
| 1X2 log loss | 1.0855 | — | 1.0108 | market |
| 1X2 Brier | 0.6539 | — | 0.6061 | market |
| O/U log loss | **0.7390** | — | 0.7269 | market |
| O/U Brier | 0.2730 | — | 0.2662 | market |

Model beat the close: **9/22** on 1X2, **9/22** on O/U 2.5.

---

## Model CLV — full round

For every match the model's **best-EV side at the opening price** is taken as the
notional bet, then measured against the closing price.
`CLV% = opening_odds / closing_odds − 1`; positive means the price shortened after
we would have taken it. Odds are de-vigged-basis consensus averages (`AvgH/D/A`,
`Avg>2.5`) against their closing counterparts. This is a **notional round-wide**
CLV over all 22 matches — not the 12 bets that were actually saved.

### EPL GW3

| Match | 1X2 pick | Open | Close | CLV | Won | O/U pick | Open | Close | CLV | Won |
|---|:--|---:|---:|---:|:--:|:--|---:|---:|---:|:--:|
| Ipswich v Liverpool | HOME | 5.48 | 4.86 | +12.76% | — | UNDER | 2.99 | 2.66 | +12.41% | ✅ |
| Newcastle v Bournemouth | AWAY | 3.19 | 3.22 | -0.93% | — | OVER | 1.55 | 1.58 | -1.90% | ✅ |
| Brentford v Sunderland | AWAY | 5.29 | 4.89 | +8.18% | — | OVER | 1.82 | 1.79 | +1.68% | — |
| Brighton v Leeds | AWAY | 3.68 | 3.73 | -1.34% | — | OVER | 1.85 | 1.76 | +5.11% | — |
| Fulham v Crystal Palace | HOME | 2.32 | 2.16 | +7.41% | — | OVER | 1.89 | 1.84 | +2.72% | ✅ |
| Man City v Coventry | AWAY | 13.85 | 12.96 | +6.87% | — | UNDER | 3.17 | 2.95 | +7.46% | ✅ |
| Nott'm Forest v Tottenham | HOME | 2.40 | 2.64 | -9.09% | — | OVER | 1.91 | 1.84 | +3.80% | — |
| Hull v Aston Villa | HOME | 4.04 | 3.92 | +3.06% | — | OVER | 1.83 | 1.80 | +1.67% | — |
| Everton v Man United | HOME | 3.21 | 3.65 | -12.05% | — | OVER | 1.67 | 1.57 | +6.37% | ✅ |
| Arsenal v Chelsea | HOME | 1.69 | 1.70 | -0.59% | ✅ | OVER | 1.73 | 1.71 | +1.17% | ✅ |

| Market | Avg CLV | Beat the close | Picks that won |
|---|---:|---:|---:|
| 1X2 | **+1.43%** | 5/10 | 1/10 |
| O/U 2.5 | **+4.05%** | 9/10 | 6/10 |

### EFL Championship GW5

| Match | 1X2 pick | Open | Close | CLV | Won | O/U pick | Open | Close | CLV | Won |
|---|:--|---:|---:|---:|:--:|:--|---:|---:|---:|:--:|
| Lincoln v Southampton | HOME | 4.06 | 4.11 | -1.22% | — | OVER | 1.68 | 1.64 | +2.44% | — |
| Preston v Blackburn | AWAY | 2.93 | 3.00 | -2.33% | — | UNDER | 1.79 | 1.86 | -3.76% | — |
| Stoke v Charlton | AWAY | 3.49 | 3.86 | -9.59% | — | UNDER | 1.70 | 1.64 | +3.66% | — |
| Burnley v Bristol City | AWAY | 3.93 | 3.67 | +7.08% | ✅ | UNDER | 1.95 | 1.94 | +0.52% | — |
| Millwall v Bolton | AWAY | 4.19 | 3.78 | +10.85% | — | UNDER | 1.75 | 1.89 | -7.41% | — |
| Portsmouth v Cardiff | DRAW | 3.50 | 3.53 | -0.85% | — | UNDER | 2.07 | 2.17 | -4.61% | ✅ |
| QPR v Middlesbrough | HOME | 3.14 | 2.89 | +8.65% | — | UNDER | 2.03 | 2.16 | -6.02% | ✅ |
| Sheffield United v Norwich | HOME | 2.53 | 2.56 | -1.17% | — | UNDER | 1.97 | 2.11 | -6.64% | — |
| West Brom v Watford | DRAW | 3.56 | 3.75 | -5.07% | — | UNDER | 1.88 | 1.96 | -4.08% | ✅ |
| West Ham v Derby | AWAY | 8.01 | 7.97 | +0.50% | — | UNDER | 2.12 | 2.40 | -11.67% | — |
| Swansea v Wrexham | HOME | 2.17 | 2.24 | -3.13% | — | UNDER | 1.81 | 1.78 | +1.69% | ✅ |
| Birmingham v Wolves | HOME | 2.87 | 2.85 | +0.70% | — | OVER | 2.06 | 1.85 | +11.35% | ✅ |

| Market | Avg CLV | Beat the close | Picks that won |
|---|---:|---:|---:|
| 1X2 | **+0.37%** | 5/12 | 1/12 |
| O/U 2.5 | **-2.04%** | 5/12 | 5/12 |

### Combined

| Market | Avg CLV | Beat the close | Picks that won |
|---|---:|---:|---:|
| 1X2 | **+0.85%** | 10/22 | 2/22 |
| O/U 2.5 | **+0.73%** | 14/22 | 11/22 |
| **Both markets** | **+0.79%** | 24/44 | — |

**Read.** Round-wide CLV is mildly positive (+0.79% over 44 notional picks) — the
model leans the same way the market later moves slightly more often than not, but
the edge is small and well inside noise at this sample size. The strong cell is
**EPL O/U 2.5 at +4.05%, beating the close 9 times in 10**, which is the same market
the round-level scoring showed the model winning outright. The weak cell is **EFL
O/U at −2.04%** — the model sat on UNDER in 10 of 12 Championship games and the
market drifted the other way.

**The 1X2 picks won 2 of 22.** That is not a like-for-like failure rate: the
best-EV side at the open is usually a draw or a longshot, so a low strike rate is
expected by construction. It does mean round-wide 1X2 CLV of +0.85% is being earned
on selections that almost never land, which is worth remembering before reading it
as an edge.
