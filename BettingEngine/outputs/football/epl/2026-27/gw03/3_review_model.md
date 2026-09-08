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

## EPL

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

**EPL — 10 matches**

| Metric | Model | Market open | Market close | Verdict |
|---|---:|---:|---:|---|
| 1X2 RPS | **0.1503** | 0.1442 | 0.1508 | model |
| 1X2 log loss | 1.0890 | — | 1.0728 | market |
| 1X2 Brier | 0.6531 | — | 0.6516 | market |
| O/U log loss | **0.7053** | — | 0.7448 | model |
| O/U Brier | 0.2573 | — | 0.2744 | model |

Model beat the close: **6/10** on 1X2, **5/10** on O/U 2.5.

Combined cross-league write-up: `outputs/results/epl_efl_model_vs_market_round_2026-09-08.md`

---

## Model CLV — full round

Model's best-EV side at the opening price, measured to the close.
`CLV% = opening_odds / closing_odds − 1`.

### EPL

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
