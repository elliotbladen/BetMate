# Championship 1X2 calibration investigation + T5 injury guardrails

Date: 6 September 2026
Trigger: EFL Championship saved bets running marginally positive on the actual
ledger (17 bets, +2.53u, +14.88% through 31 Aug) but the very-high-EV shortlist
went 0/3 with −3.25% captured CLV in Week 2. Hypothesis to test: the 1X2 tail is
miscalibrated, so large displayed EV is not real.

## What was checked

1. **Is 1X2 calibrated anywhere?** No. `models/calibration.py` defines
   `H2HCalibrator` but nothing calls it. Neither `price_match.py` (production)
   nor `backtest/walk_forward.py` applies it. Only over-2.5 gets isotonic.
   Same for EPL. There is also no market-blending on 1X2 — EV is computed
   straight from raw model prob vs market odds.

2. **Reliability curve** (walk-forward `backtest_results.csv`, 2,205 Championship
   matches, seasons 2021/22–2024/25, vault 2025/26 excluded). The raw
   D-C+Elo 1X2 blend is **already well calibrated**, including the tail:

   | Model prob band | n | Predicted | Actual | Gap |
   |---|---:|---:|---:|---:|
   | 0.15–0.25 | 1025 | 0.216 | 0.217 | −0.00 |
   | 0.25–0.35 | 3123 | 0.289 | 0.291 | −0.00 |
   | 0.35–0.45 | 1267 | 0.398 | 0.395 | +0.00 |
   | 0.45–0.55 | 685 | 0.492 | 0.496 | −0.01 |
   | 0.55–0.70 | 320 | 0.609 | 0.591 | +0.02 |
   | 0.70+ | 34 | 0.740 | 0.735 | +0.00 |

   Only wrinkle: the model slightly over-eggs draws in its 0.28–0.30 band
   (+5–7pp). No systematic tail overconfidence.

3. **EV screen on the backtest** (bet each qualifying outcome at best-of-market
   close; absolute ROI optimistic, relative comparison is the valid part):

   | Screen | n | Strike | ROI |
   |---|---:|---:|---:|
   | EV ≥ 10% | 1610 | 28.1% | +3.3% |
   | EV ≥ 15% | 1213 | 27.3% | +4.0% |
   | EV ≥ 20% | 937 | 26.9% | +6.2% |

   The +20% bucket is the **best** bucket. "Monster EV = fake" is not supported
   historically.

## Candidate change tested and REJECTED: isotonic 1X2 calibration

Wired `H2HCalibrator`-style isotonic maps (one per outcome, fit walk-forward on
accumulated prior test seasons) into both `price_match.py` and `walk_forward.py`,
re-ran the Championship backtest. Result — it **mildly hurts on every metric**:

| Metric | Raw | + isotonic 1X2 |
|---|---:|---:|
| Pooled Brier | 0.2104 | 0.2112 |
| RPS 2022/23 | 0.1473 | 0.1486 |
| RPS 2023/24 | 0.1494 | 0.1504 |
| EV≥10% ROI | +3.3% | −1.5% |
| EV≥20% ROI | +6.2% | +2.2% |

The model was already calibrated, so an isotonic map fit on only 1–3 noisy prior
seasons just injects fitting noise. **Backed out fully** — `price_match.py` and
`walk_forward.py` calibration code reverted, backtest CSVs restored from git.

(An earlier throwaway check suggested isotonic helped at EV≥15%; that version fit
on all prior seasons pooled with mild leakage. The properly wired walk-forward
version does not help. Revisit only end-of-season with 2026/27 added.)

Market-blending toward the no-vig line was also modelled: it destroys real edge
(EV≥20% ROI +6.2% → +3.0% at w=0.7 → −4.9% at w=0.5). Not shipped.

## Change KEPT: T5 injury guardrails

The T5 injury layer is in production `price_match.py` but **completely absent
from the walk-forward** — zero backtest validation. Every large live EV this
season came from injury bumps (GW5: Bolton 20.8→25.1, Sheff Utd 46.8→52.2,
Charlton 31.9→34.5; Lincoln dropped 13.6%→7.0% EV purely on the injury move).
This is the prime suspect for the live pattern. Two conservative guards added
pending a proper T5 backtest:

1. `models/tiers.py`: `MAX_DISRUPTION` **0.25 → 0.15**. A 25% xG swing from
   confirmed absences is not credible.
2. `price_match.py`: **T5 1X2 swing cap `T5_H2H_SWING_CAP = 0.03`**. The match is
   priced a second time with injuries stripped; the injury layer may move each
   1X2 outcome by at most ±3pp from the injury-free price. `price_match` now also
   returns `p_{home,draw,away}_base` / `fair_*_base` and `t5_h2h_swing_capped`
   so the EV screen can require a bet to clear the floor on the pre-injury price
   too (not yet automated — screening is still conversational).

Smoke test (Sheff Utd v Norwich, 3 away injuries ST+AM+CM): raw injury swing
~+5–6pp on the home win, capped to +3.4pp after renormalisation. No-injury calls
are unaffected (`p_*_base == p_*`).

Neither change touches the walk-forward output (T5 has no injury data there), so
no backtest regression. 76 football unit tests pass.

## What the live losses actually point to (not fixed here)

1. **Bet timing / CLV.** Week 2 captured CLV was −3.25% — prices drifted against
   the picks between save and close. The backtest bets at best-of-market *close*
   and is fine. Can't measure save→close drift in the current backtest CSV —
   opening odds aren't captured. **Next data task: add opening odds to
   `backtest_results.csv`** so save→close drift on EV-screened bets is
   measurable.
2. **T5 has no backtest.** Build a minimal historical injury dataset and get
   injury adjustments into the walk-forward. Until then the guards above stand.
3. **5 GW / ~20 bets can't reject the model.** 27% strike at avg odds ~4.5
   throws 0-fers regularly.

## Files changed

- `ml/football/models/tiers.py` — `MAX_DISRUPTION` 0.25 → 0.15
- `ml/football/price_match.py` — T5 1X2 swing cap + base-price fields in return

## Recommended cadence (asked this session)

Not a per-week job. Calibrators refit automatically on `walk_forward.py` runs and
don't move within a season. Weekly = existing refresh + price-the-round + log
CLV. Monthly-ish = 10-min glance at the reliability curve + running CLV. Once at
season end = refit with 2026/27, review static caps + the 10% EV floor. A full
investigation like this one should be evidence-triggered, not scheduled.
