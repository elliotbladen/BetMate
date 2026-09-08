# Football season-to-date — actually saved/placed bets

**Through 2026-09-06** · flat 1u unless a stake is recorded · losing bet returns zero  
**Odds:** football-data consensus averages (open `AvgH/AvgD/AvgA`,`Avg>2.5`; close `AvgC*`)  
**Driver:** `scripts/football_season_bet_ledger.py`

## Scope — what counts as a placed bet

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


### EFL Championship — COMBINED

| Measure | Value |
|---|---:|
| Bets | 8 (0W / 8L, 0.0% strike) |
| Staked | 8.50u |
| P&L | **-8.50u** |
| **ROI** | **-100.00%** |
| **CLV (vs close)** | **+6.67%** — beat the close 4/8 |
| vs open | +7.60% — beat the open 4/8 |

| Week | Bets | W-L | P&L | ROI | CLV |
|---|---:|---:|---:|---:|---:|
| EFL GW5 | 5 | 0-5 | -5.50u | -100.00% | +12.61% |
| EFL W3 | 3 | 0-3 | -3.00u | -100.00% | -3.25% |

---

### Both leagues

| Measure | Value |
|---|---:|
| Bets | 21 (4W / 17L, 19.0% strike) |
| Staked | 21.50u |
| P&L | **-12.91u** |
| **ROI** | **-60.05%** |
| **CLV (vs close)** | **+7.35%** — beat the close 14/21 |
| vs open | +7.31% — beat the open 16/21 |

> 2 EPL rows carry verification warnings from the 2026-09-02 report (Aston Villa win
> at 6.50 flagged `price_verification_required`; Tottenham/Newcastle Over 2.5 flagged
> `matrix_verification_required`). Excluding both: **19 bets, −10.91u, ROI −55.95%**.

## Read

**Both leagues show positive CLV and deeply negative ROI.** EPL +7.78% CLV on −33.92%
ROI; EFL +6.67% CLV on −100.00% ROI. Over 21 bets that is not a contradiction, it is
variance — but it is the single most important number to keep watching, because a
persistent gap between the two eventually means one of them is lying.

**EPL is the healthier book.** 4 wins from 13, beat the open 12/13 and the close 10/13.
Its GW3 O/U 2.5 leg went 3-for-3, and the independent round-level scoring had the model
beating the closing market on totals outright. That is three measures agreeing.

**EFL has not won a bet yet — 0 from 8.** Its CLV is positive but built almost entirely
on one price (Millwall/Bolton at 6.00 into a 3.78 close). Week 3 was actually *negative*
CLV at −3.25%. Combined with the full-round model-vs-market work, where the Championship
engine lost to the market on every metric, the EFL side looks genuinely mispriced rather
than unlucky.
