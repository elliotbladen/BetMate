# Football season-to-date — PAPER selections (not staked)

**Through 2026-09-06** · flat 1u unless a stake is recorded · losing bet returns zero  
**Odds:** football-data consensus averages (open `AvgH/AvgD/AvgA`,`Avg>2.5`; close `AvgC*`)  
**Driver:** `scripts/football_season_bet_ledger.py`

> **These were paper bets.** User confirmed 2026-09-08 that none of these 21
> selections were staked. They are model/paper performance only and must not be
> presented as a betting record. Real-money football tracking starts from zero on
> the site's Football Model tab.

## Scope — what is included

Only the two graded records that carry **both a taken price and a result**:

1. `epl_efl_saved_20pct_ev_results_2026-09-02.csv` — EPL W2 (6), EFL W3 (3)
2. `epl_efl_saved_bets_clv_roi_2026-09-08.csv` — EPL GW3 (7), EFL GW5 (5)

**Excluded:** `outputs/results/all model results/*` and the GW1 CLV backtests — those
are full model portfolios (every side of every game), not bets. Also excluded is the
23-bet "previous weekend" in `epl_efl_combined_performance_through_2026-08-31.md`:
no underlying graded bet file exists for it and that report labels its own cumulative
figure mixed-rule preliminary, so merging it would inflate the count on faith.

---

### EPL — COMBINED

| Measure | Value |
|---|---:|
| Bets | 13 (4W / 9L, 30.8% strike) |
| Staked | 13.00u |
| P&L | **-4.41u** |
| **ROI** | **-33.92%** |
| **CLV (vs close)** | **+7.78%** — beat the close 10/13 |
| vs open | +7.13% — beat the open 12/13 |

| Week | Bets | W-L | P&L | ROI | CLV |
|---|---:|---:|---:|---:|---:|
| EPL GW3 | 7 | 3-4 | -1.73u | -24.71% | +5.68% |
| EPL W2 | 6 | 1-5 | -2.68u | -44.67% | +10.22% |

Cross-league write-up: `outputs/results/football_season_bet_ledger_2026-09-08.md`
