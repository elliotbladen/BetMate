# Handover — handicap weight V2 audit

Tested 0/25/50/75/100% of the parent 2.2046-points-per-kg relative-to-winner
handicap adjustment on training only. Log loss worsened monotonically with more
weight, selecting zero. This rejects the current formulation, not the physical
effect of weight.

Gringotts' Doncaster run falls 118.85 -> 97.91 after removing +20.94 weight
points. Tropicus' Oakleigh Plate win remains 111.35 at 58.5 kg and Jigsaw's
3.5L open win remains 121.88 at 61 kg; both winners had zero weight bonus.

Horse Ability now has Sheza Alibi 110.83 above Gringotts 109.79. Validation and
historical holdout headline log loss beat rejected V2, V1 and uniform, but the
validation interval versus V1 still crosses zero. Keep V2.8/V2.4 shadow-only.
Next weight work needs allocated weight, claims and race/distance-specific
bounded response rather than mechanically restoring the rejected coefficient.
