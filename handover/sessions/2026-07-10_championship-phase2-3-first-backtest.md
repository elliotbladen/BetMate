# 2026-07-10 — Championship Phases 2–3: data, constants, first backtest + CLV test

## Data saga (morning)
Work FortiGate **blocks football-data.co.uk** (gambling category — cert re-signed by
`FG101FTK25001007`). Interim solution: Internet Archive fallback in the fetcher +
results-only patch for 2023/24 H2. Then the user switched to a hotspot → **pristine
direct refetch: 12 complete seasons (2014/15–2025/26), 6,624 matches, full Pinnacle
open+close odds coverage in every season.** 2025/26 vault is complete and untouched.
The archive fallback stays in the fetcher (works from the office network).

## Constants derived from E1 data (vault excluded) — `leagues/championship.yaml`
- Draws 26.9% (web research said "1 in 3" — data says less), goals 2.540, O2.5 47.4%
- Home wins 43.2% vs EPL 44.6% → **home advantage NOT stronger; research claim disproven**
- `short_rest_days: 3` — median E1 rest is 4d and 50.3% of games are ≤4d; EPL's ≤4
  threshold would penalise half the league. ≤3d = 27.9% (real midweek turnarounds)
- T6 `league_ref_goals: 1.416` (127 refs); T7 corners 5.641 home / 4.624 away
- Elo `draw_base: 0.27` confirmed by data (26.9%)
- Test seasons: **2021/22–2024/25 (four)**, vault 2025/26 never touched

## First backtest — goals-fed D-C+Elo, EPL constants otherwise (2,205 matches)
| Season | Model RPS | Market RPS (Pinnacle close) | Gap |
|---|---|---|---|
| 2021/22 | 0.1496 | 0.1445 | +3.5% |
| 2022/23 | 0.1473 | 0.1470 | **+0.2%** |
| 2023/24 | 0.1494 | 0.1417 | +5.4% |
| 2024/25 | 0.1384 | 0.1384 | **0.0% — market parity** |
| **AGG** | **0.1462** | **0.1429** | **+2.3%** |

Accuracy 45.8% looks low vs EPL's 54% but is expected in a draw-heavy league — RPS is
the meaningful metric. **+2.3% behind Pinnacle closing is BETTER relative position than
the EPL engine (+5.0% behind its market)** — a strong v1 for a goals-fed model with
zero tuning (decay/rho still EPL values).

## CLV backtest — the money question (`backtest/clv_backtest.py`, new)
Simulated bets vs Pinnacle OPENING where model edge ≥ threshold, scored on CLV vs close
+ flat-stake ROI, 4 seasons:
- **Overall CLV NEGATIVE at every threshold** (−0.9% to −1.1%; only 43–44% of bets beat
  the close). **The raw v1 model does NOT have a proven market edge.** Bet volumes
  (1,200–2,400 over 4 seasons) say the model is overconfident vs the market.
- **Home-side slice is the lead:** CLV −0.51%, 48% beat close, ROI +6.2% → +11.0%
  monotonically rising with edge threshold (608 bets at ≥8%: +9.5% ROI). BUT positive
  ROI with flat-negative CLV = unproven; could be variance or a real closing-line home
  bias in this league. NOT bettable yet per house CLV discipline.
- Draw bets toxic everywhere (−7% to −13% ROI). Away bets negative.

## Interpretation + what comes next
1. The model's H2H probabilities are **uncalibrated** (walk_forward only calibrates
   totals — true for EPL too). Isotonic H2H calibration should shrink overconfident
   edges, cut bet volume, and is the first Phase 5 improvement.
2. T8 season-reset prior (ClubElo + parachute) is Phase 4 — the August-window edge
   hypothesis is still untested.
3. Tier ablations need `--apply-tiers` in walk_forward (found: tiers don't affect
   backtest prices, EPL included) — Phase 5.
4. Decay/rho grid search — Phase 5.

## Status vs plan
- Phase 2 ✅ (data, yaml, goals-fed core, constants)
- Phase 3 ✅ with scope notes (T6/T7 refit from data; T3 retuned to ≤3d; T2 deferred
  pending ablation capability)
- Phase 4 next: ClubElo T8 prior + T9 manager flag
- New scripts: `backtest/market_baseline.py`, `backtest/clv_backtest.py` (both leagues)
