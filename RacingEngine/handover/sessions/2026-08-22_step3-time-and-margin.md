# Handover — improvement Step 3: time and margins

Date: 22 August 2026

## Completed

Implemented `racing_engine/time_margin_stage3.py` and evaluated three strengths
of the existing form-anchored margin candidate: 25%, 50% and 100%. The comparison
uses 1,582 common races under frozen `evaluation-v1`.

The research control is `performance-par-v1.0+identity-v1.0`, which isolates
margin information after durable identity. A candidate must also beat accepted
`performance-par-v1.0`; improving only the weaker research control is not enough.

## Result

The 25% blend added statistically detectable margin information:

- validation delta versus identity: `-0.000588`
- validation interval: `[-0.001173, -0.000016]`
- holdout delta versus identity: `-0.001661`

But it was worse than official V1 in both periods. The 100% blend beat official
V1 in validation (`-0.000651`) and holdout (`-0.002831`), but its isolated
validation interval crossed zero. The 50% version also fell between the two
requirements. Therefore no candidate cleared the complete gate.

## Decision

No promotion. Freeze this branch. Keep the full anchored-margin candidate as a
prospective shadow, because its direction versus official V1 remains promising.
Do not select 60%, 70% or another coefficient using these observed results.

Proceed next to the distinct pace/sectional branch. The accepted model remains
`performance-par-v1.0`.

## Outputs

- `data/outputs/stage3_time_margin_2026-08-22.json`
- `data/outputs/stage3_time_margin_2026-08-22.md`
- `tests/test_time_margin_stage3.py`

## Verification

Full suite: 70 passing tests.
