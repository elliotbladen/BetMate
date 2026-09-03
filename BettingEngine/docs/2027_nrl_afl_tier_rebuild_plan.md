# 2027 NRL and AFL tier-model rebuild decision

## Decision

The 2027 NRL and AFL model rebuilds will adopt the tier-development framework
proved during the 2026 NFL build. This is an architectural commitment, not an
instruction to copy NFL coefficients or point values into another sport.

Each code will retain sport-specific features and independently learned effects,
while sharing the following controls:

1. Preserve an immutable core team-strength prediction (T1).
2. Keep player availability, continuity, venue, scheduling, weather, matchup
   and market information in separately measurable tier families.
3. Timestamp every live input and forbid information published after the model
   cutoff.
4. Test each tier with expanding-window or walk-forward season folds.
5. Compare each real tier with a within-season shuffled negative control.
6. Freeze core, individual-tier and combined predictions before results and
   closing prices are known.
7. Measure result error, probability calibration, closing-line value and ROI at
   genuinely obtainable archived prices.
8. Promote tiers from shadow to paper-active and then betting-active only after
   prospective evidence; implementation alone is not proof of value.
9. Reject generic manual player or injury points unless they beat a learned,
   point-in-time alternative out of sample.
10. Retain an active data-health gate that forces abstention when mappings,
    timestamps, team news or market coverage are incomplete.

## Intended sport-specific translation

For NRL, the personnel layer should separately test spine availability,
halfback/hooker/fullback combinations, middle rotation and edge combinations.
For AFL, it should separately test ruck, midfield, key-position and defensive
unit availability. Both codes should model continuity and injuries separately
so weak injury counts cannot hide useful unit-continuity signal.

The rebuilds should reuse shared snapshot, audit, ablation and promotion
infrastructure, but all feature weights, adjustment caps and tier promotion
decisions must be learned independently for NRL and AFL.
