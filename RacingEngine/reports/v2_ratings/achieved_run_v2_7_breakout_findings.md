# Achieved Run V2.7 separated breakout findings

Date: 28 August 2026  
Version: `achieved-run-v2.7-breakout-separated-shadow`  
Decision: **achieved-run gates pass; retain shadow pending Horse Ability test**

## Architecture

V2.6 demonstrated that completed-run achievement must be separated from future
repeatability, but applying its class/opposition blend universally damaged the
elite audit. V2.7 therefore preserves V2.4 except for an independently defined
breakout subset:

- winner by at least three lengths;
- no more than eight strictly prior starts; and
- point-in-time opposition reliability below 0.50.

Eligible winners receive the separated achieved figure: class standard blended
with opposition according to evidence reliability, plus the full bounded
distance-scaled winning margin. Only 75 winners qualify across 2,712 races.

## Results

- Natural Fling: **104.22**. Her race level is 92.89 from a 105 Group 3 prior,
  77.53 opposition anchor and 0.441 opposition reliability; four lengths adds
  11.33 points.
- Elite official-classification Spearman: **0.540**, above the 0.50 gate.
- Sheza Alibi: **116.24**; Gringotts: **112.37**, with correct WFA semantics.
- Accepted ratings remain unchanged.

The old 90-day future-peak gate fails, as do 180 and 365 days. That is not
ignored: it proves the achieved figure must not be carried forward at full
weight. It is now a downstream Horse Ability shrinkage/uncertainty test rather
than a reason to erase what was achieved in the completed race.

## Next gate

Keep V2.7 shadow-only while rerunning Horse Ability on two distinct inputs:
completed-run achievement and recurrence/reliability. Require the ability layer
to improve chronological ranking, log loss, calibration and future-peak MAE.
Natural Fling's achieved 104.22 is not automatically her sustainable ability.
