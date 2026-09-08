# EPL GW3 — saved selections graded vs the closing line

**Graded:** 2026-09-08  
**Selections from:** `gw3_10pct_ev_candidates_2026-09-03.csv`  
**Closing odds:** football-data.co.uk average closing (`AvgCH/AvgCD/AvgCA`, `AvgC>2.5`)  
**Stake:** the `stake_units` on the saved row · losing bet returns zero  
**CLV:** `saved_price / closing_odds − 1`  
**Driver:** `scripts/score_football_saved_bets.py`

| Match | Selection | Took | Close | CLV | Score | Result | P&L (u) |
|---|---|---:|---:|---:|---:|:--:|---:|
| Ipswich v Liverpool | Ipswich win | 5.50 | 4.86 | +13.17% | 0-2 | ❌ | -1.00 |
| Brentford v Sunderland | Sunderland win | 5.50 | 4.89 | +12.47% | 1-1 | ❌ | -1.00 |
| Hull v Aston Villa | Hull win | 4.10 | 3.92 | +4.59% | 0-0 | ❌ | -1.00 |
| Everton v Man United | Everton win | 3.10 | 3.65 | -15.07% | 2-2 | ❌ | -1.00 |
| Newcastle v Bournemouth | Over 2.5 | 1.57 | 1.58 | -0.63% | 2-2 | ✅ | +0.57 |
| Everton v Man United | Over 2.5 | 1.70 | 1.57 | +8.28% | 2-2 | ✅ | +0.70 |
| Arsenal v Chelsea | Over 2.5 | 2.00 | 1.71 | +16.96% | 2-1 | ✅ | +1.00 |

## Summary

- Bets: **7** (3W / 4L, 42.9% strike)
- Staked: 7.00u — P&L: **-1.73u**
- **ROI: -24.71%**
- **Average CLV: +5.68%** — beat the close on 5/7

Full cross-league write-up, including the 0-for-9 1X2 draw pattern:
`outputs/results/epl_efl_saved_bets_clv_roi_2026-09-08.md`
