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
