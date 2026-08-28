# Handicap weight V2 findings

Date: 28 August 2026  
Run version: `achieved-run-v2.8-handicap-weight-shadow`  
Ability version: `horse-ability-v2.4-handicap-weight-shadow`  
Decision: **full relative-weight response rejected; zero selected; retain shadow**

## Training selection

The parent formula awards 2.2046 rating points per kilogram carried relative to
the winner in handicaps. Fractions 0, 0.25, 0.50, 0.75 and 1.0 were tested on
979 training races with the frozen responsive Horse Ability state. Training log
loss worsened monotonically from 2.34053 at zero to 2.34089 at full response.
The selected coefficient is **0.0**.

This does not prove weight has no effect. It rejects this specific mechanical
relative-to-winner adjustment, which can double count field/race-strength
anchors and award very large figures to well-beaten topweights.

## Named audit

- Gringotts, Doncaster: 118.85 becomes **97.91**. The removed component is
  +20.94 for carrying 58.5 kg against the lightweight winner while beaten 6.29L.
- Tropicus, Oakleigh Plate: remains **111.35** after winning by 1.25L carrying
  58.5 kg. Winners had no relative-to-winner bonus in either version.
- Jigsaw, 14 March open race: remains **121.88** after winning by 3.5L carrying
  61 kg. His figure is dominance/race-level driven, not a weight bonus.

Tropicus' current evidence is consistent with a high-quality WFA sprinter: the
Oakleigh Plate 111.35 sits alongside 112.67 in a Group 3 win and 109.59 in a
Group 2 second. Middle-distance ability is not established by the stored races
and should remain uncertain rather than inferred.

## Horse Ability result

Sheza Alibi is now **110.83**, above Gringotts **109.79** by 1.04 points. Natural
Fling remains 99.67 and Autumn Glow 117.84.

Validation improves every headline baseline: -0.01901 versus rejected V2,
-0.00499 versus V1 and -0.01179 versus uniform. Historical holdout also beats
all three. Validation uncertainty versus V1 still crosses zero, so promotion is
withheld. A new weight model must use allocated weight/claims where available
and fit a bounded response by distance/race type rather than restore this full
mechanical adjustment.
