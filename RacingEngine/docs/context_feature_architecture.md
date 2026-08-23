# Point-in-time context architecture

Status: implemented 22 August 2026.

## Purpose

This layer prepares historical evidence for future training without changing
the accepted rating. It prevents three common errors: treating every kilogram
as the same type of information, confusing official benchmark points with
internal performance points, and allowing the target result to leak into its
own pre-race feature row.

## Flow

```text
immutable results + race classifications + horse profiles
        |
        +--> runner_weight_contexts (post-race interpretation evidence)
        |      carried / allocated / claim / overweight / penalty
        |      official WFA / field-relative burden
        |      changes from the horse's strictly previous run
        |
        +--> contextual evidence (kept separate)
               daily variant / going / canonical sectionals / DT-W
               steward events / campaign stage / Race Strength
                       |
                       v
              point_in_time_features
              one target runner row; history cutoff < target date
                       |
                       v
              future training and chronological ablation only
```

## Scale policy

- Official Australian benchmark interpretation remains `1 point = 0.5kg`.
- Internal performance points remain length-style performance units.
- WFA is an official schedule reference, not a universal bonus.
- Any distance-sensitive kilogram response is a candidate learned/tested in
  shadow. No `1kg = 1 point` or `1kg = 2 internal points` shortcut is active.

## Evidence timing

`runner_weight_contexts` describes completed races. Its carried weight comes
from the result record and is labelled post-race/result evidence. Allocated
weight, claim, overweight and penalty remain NULL unless directly supplied.

`point_in_time_features` may summarize only races strictly earlier than the
target race date. It explicitly excludes the target result's carried weight.
The availability JSON records the exclusive cutoff and missing-as-unknown rule.

## Current tables and versions

- `runner_weight_contexts`: `weight-context-v1.0`
- `point_in_time_features`: `point-in-time-context-v1.0`
- baseline: `performance-par-v1.0`, frozen
- weight candidates: shadow only

## Promotion rule

This feature layer is infrastructure, not proof of forecasting gain. A future
candidate must beat the frozen baseline on the same chronological fields and
survive Brier, log-loss, calibration, segment, uncertainty and untouched
holdout checks. A failure produces a diagnosis and revised feature/data plan;
it does not produce a coefficient change by opinion.
