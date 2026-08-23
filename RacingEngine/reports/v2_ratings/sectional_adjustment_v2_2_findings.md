# Step 2 adjustment recovery — V2.2 findings

Date: 2026-08-23
Status: frozen shadow; Step 3 remains blocked

## What changed

1. Added prior-only track/distance/exact-condition residuals.
2. Added leave-one-race-out meeting-speed residuals.
3. Split sectional achievement, trip compensation and steward evidence.
4. Recalculated trip workload from the corrected race shape.
5. Fitted coefficients independently for NSW and Victoria with zero included.
6. Tested every component alone and combined on 2025+ races.
7. Applied the strict rule that both jurisdictions must improve in next-start error and race-ranking log loss.

## Learned coefficients

| Candidate | NSW | Victoria |
|---|---:|---:|
| Achievement | 0.0 | 0.0 |
| Trip compensation | 1.0 | 0.3 alone / 0.4 combined |
| Steward evidence | 0.0 | 1.0 |

Zero achievement is a valid result, not a software failure. The initial weighted relative-split formula did not predict repeatable rating strength after controlling through the base rating.

## Holdout findings

- Base next-start MAE: 8.05433 across 6,108 pairs.
- Trip-only MAE: 8.05008. It improved both jurisdictions, but worsened overall and NSW ranking log loss.
- Combined MAE: 8.05034 and overall log loss 2.49324 versus 2.49414 base. NSW log loss worsened from 2.52165 to 2.52520.
- Steward-only improved ranking log loss in both jurisdictions indirectly through cross-jurisdiction history, but NSW next-start MAE was unchanged because the present steward feed is Victorian.
- No candidate passed every gate.

## Elite audit

The split architecture is better behaved conceptually. In the 2024 Cox Plate, Via Sistina records strong achievement `+1.75` and a small favourable-trip signal `-0.48`; Pride Of Jenni records achievement `-1.22` but compensation `+1.66`. The joint fitted rating adjustment would be `-0.19` and `+0.66` respectively. Achievement is visible separately even though its learned rating coefficient remains zero.

## Research diagnosis

The literature indicates that the missing concept is energy efficiency rather than a generic fast-final-sectional bonus. Thoroughbreds cannot sustain maximum speed throughout a race; optimal profiles vary with distance, and drafting materially changes energy expenditure. Track condition, geometry and incline also affect observed speed. Therefore V2.3 should model deviation from a distance-specific efficient speed curve and treat position/drafting as exposure, instead of using a fixed 20/30/50 split blend.

## Freeze decision

- Accepted horse rating: unchanged.
- Achievement candidate: rejected at zero.
- Trip candidate: frozen as promising, not promoted.
- Steward candidate: frozen as Victoria-only supporting evidence.
- Step 3: blocked by project decision until a Step 2 adjustment passes.

## Next Step 2 experiment

Build an energy-efficiency candidate from 200m velocity curves: normalize phase distance, estimate distance/track/condition optimal profiles chronologically, measure excess early energy and late deceleration, add leader/drafting exposure, and validate suitable-pace next starts by distance band. Preserve V2.2 unchanged as the comparator.
