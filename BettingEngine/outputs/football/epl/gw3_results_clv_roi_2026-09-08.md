# EPL GW3 — saved selections graded vs the opening and closing lines

**Graded:** 2026-09-08  
**Selections from:** `gw3_10pct_ev_candidates_2026-09-03.csv`  
**Odds:** football-data.co.uk consensus averages — opening `AvgH/AvgD/AvgA`, `Avg>2.5`; closing `AvgCH/AvgCD/AvgCA`, `AvgC>2.5`  
**Stake:** the `stake_units` on the saved row · losing bet returns zero  
**Driver:** `scripts/score_football_saved_bets.py`

| Match | Selection | Open | Took | Close | vs OPEN | vs CLOSE | Market drift | Result | P&L |
|---|---|---:|---:|---:|---:|---:|---:|:--:|---:|
| Ipswich v Liverpool | Ipswich win | 5.48 | 5.50 | 4.86 | +0.36% | +13.17% | -11.31% | ❌ | -1.00 |
| Brentford v Sunderland | Sunderland win | 5.29 | 5.50 | 4.89 | +3.97% | +12.47% | -7.56% | ❌ | -1.00 |
| Hull v Aston Villa | Hull win | 4.04 | 4.10 | 3.92 | +1.49% | +4.59% | -2.97% | ❌ | -1.00 |
| Everton v Man United | Everton win | 3.21 | 3.10 | 3.65 | -3.43% | -15.07% | +13.71% | ❌ | -1.00 |
| Newcastle v Bournemouth | Over 2.5 | 1.55 | 1.57 | 1.58 | +1.29% | -0.63% | +1.94% | ✅ | +0.57 |
| Everton v Man United | Over 2.5 | 1.67 | 1.70 | 1.57 | +1.80% | +8.28% | -5.99% | ✅ | +0.70 |
| Arsenal v Chelsea | Over 2.5 | 1.73 | 2.00 | 1.71 | +15.61% | +16.96% | -1.16% | ✅ | +1.00 |

| Measure | Value |
|---|---:|
| Bets | 7 (3W / 4L, 42.9%) |
| Staked / P&L | 7.00u / **-1.73u** |
| ROI | **-24.71%** |
| **vs OPEN** | **+3.01%** — beat the open 6/7 |
| **vs CLOSE (CLV)** | **+5.68%** — beat the close 5/7 |

Full cross-league write-up: `outputs/results/epl_efl_saved_bets_clv_roi_2026-09-08.md`
