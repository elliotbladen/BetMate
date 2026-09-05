# Championship 1X2 calibration investigation + T5 injury guardrails

Date: 6 September 2026
Scope: BettingEngine football stack (EPL / EFL Championship). No BetMate frontend
or racing changes.

## Why

The EFL Championship saved-bet ledger is marginally positive (17 bets, +2.53u,
+14.88% through 31 Aug) but the very-high-EV shortlist went 0/3 with −3.25%
captured CLV in Week 2. Question raised: is the 1X2 tail miscalibrated, making
large displayed EV untrustworthy? Instruction: backtest before changing anything.

## Findings

- **1X2 is uncalibrated everywhere** (production and backtest) — `H2HCalibrator`
  exists but is dead code; only over-2.5 gets isotonic.
- **But the model is already well calibrated**, tail included. Walk-forward
  reliability curve over 2,205 Championship matches: pooled predicted-vs-actual
  gap ≤0.02 across the whole probability range. The EV≥20% bucket is the *best*
  backtest bucket (+6.2% ROI at close, 937 bets). The "monster EV = fake"
  hypothesis is not supported historically.
- **Isotonic 1X2 calibration: tested and rejected.** Wired in, re-ran the
  backtest — it mildly hurt every metric (Brier 0.2104→0.2112, EV≥20% ROI
  +6.2%→+2.2%). Fully reverted. Market-blending toward the no-vig line also
  modelled and rejected (destroys real edge).
- **The real live signal is bet timing / CLV**, not calibration — prices drifted
  against the picks between save and close.

## Changes kept (BettingEngine)

The T5 injury layer is in production but has **zero walk-forward validation**,
and every large live EV this season came from injury bumps. Two conservative
interim guards:

- `ml/football/models/tiers.py` — `MAX_DISRUPTION` 0.25 → **0.15**/axis.
- `ml/football/price_match.py` — **±3pp cap** on how far T5 may move each 1X2
  outcome vs an injury-free re-price; `price_match` now returns
  `p_*_base` / `fair_*_base` / `t5_h2h_swing_capped`.

76 football unit tests pass; no backtest regression (T5 isn't in the
walk-forward). Docs updated: `ml/football/ARCHITECTURE.md`,
`ml/football/CHAMPIONSHIP_PLAN.md`, `BettingEngine/CLAUDE.md`,
`BettingEngine/handover/PROJECT_DIARY.md`.

## Next

1. Add opening odds to `ml/football/data/*/clv/backtest_results.csv` so save→close
   drift on EV-screened bets can be measured — this is the question the live data
   is actually raising.
2. Get T5 injury adjustments into a backtest, then revisit the guard values.
3. Revisit 1X2 isotonic end-of-season with 2026/27 added to the training seasons.

Full detail: `BettingEngine/handover/sessions/2026-09-06_championship-1x2-calibration-t5-cap.md`
