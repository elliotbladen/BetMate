# Achieved Run V2.1 recovery — findings

Date: 28 August 2026  
Version: `achieved-run-v2.1-margin-weight-shadow`  
Decision: **REVISE — not promoted**

## What was tested

The accepted `form-first-v2.0` table was left unchanged. A separate component
ledger tested two previously identified defects:

1. bounded positive evidence for a dominant winner; and
2. race-condition-aware weight semantics. Handicap burden remains explicit,
   while WFA/set-weight age and sex allowances are not treated as merit bonuses.

The lightly raced breakout rule reduces stale collateral authority only when a
winner has no more than eight prior runs, wins by at least three lengths and has
a prior rating at least ten points below the class standard. Time/variant,
sectional and retrospective collateral components remain explicit zeroes marked
`not_promoted`; missing evidence is not manufactured.

## Named audits

- Natural Fling, Caulfield 15 August: **106.94** (accepted base 83.53). The
  candidate race level is 95.61 and bounded four-length evidence adds 11.33.
  This passes the predeclared 100–110 plausibility band.
- Sheza Alibi, Randwick 22 August: **116.44**.
- Gringotts, Randwick 22 August: **112.57**.

The latter pair now has zero WFA weight component for both horses. Sheza Alibi's
smaller beaten margin therefore places her above Gringotts. This is a semantic
audit, not a fitted target or proof of predictive improvement.

## Gates that failed

- Official-classification audit Spearman: **0.402**, required at least 0.50.
- Frozen breakout cohort, 90-day future-peak MAE: candidate **11.386**,
  class-only **9.108**, official prior **12.307**. The candidate beats the
  official prior but not class-only.
- At 180 days the candidate MAE is 10.185 versus class-only 8.972; at 365 days
  9.619 versus 9.428. It therefore does not solve the broad cohort.
- False-discovery rates are 46.7%, 40.5% and 34.4% at 90/180/365 days.

Natural Fling is fixed as a sanity case, but the general rule overstates enough
other dominant lightly raced winners to fail. The named result must not be used
to justify promotion.

## Stage 2 rerun

`sectional-adjustment-v2.2-shadow` was rerun against the restored/up-to-date
database. No variant passed. The combined candidate improved overall log loss
and next-start MAE, but failed the both-jurisdictions ranking gate. Achievement,
trip and steward variants each failed at least one overall or jurisdiction gate.

Report: `sectional_adjustment_v2_2_evaluation_rerun_20260828.json`.

## Consequence for stages 2 and 3

Retrospective collateral promotion remains locked behind the sectional gate.
Horse Ability V2.1 was not rerated or promoted on these figures because both
the achieved-run cohort gate and sectional gate failed. Doing so would merely
aggregate a known-bad upstream candidate.

## Next controlled experiment

Keep the corrected weight semantics. Replace the binary breakout anchor relief
and broad winner-margin addition with training-only reliability calibration
using independent clock/meeting-variant and energy-efficiency support. Fit on
pre-2025 data, then rerun the unchanged elite, NSW/Victoria, false-breakout and
future-peak gates. Natural Fling remains evaluation-only.

All 109 RacingEngine tests pass, with one expected skip. SQLite accepted V2
ratings were not overwritten.
