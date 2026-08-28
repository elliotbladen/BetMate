# Horse Ability distance/going findings

## Outcome

The training-only 5x5 grid selected zero distance adjustment and zero going
adjustment. The no-adjustment training log loss was 2.34058 and every positive
coefficient combination was worse.

The experiment used strictly prior horse runs, four distance bands and three
going buckets. Context residuals required at least two matching runs, were
shrunk toward zero and capped at six points per dimension. Race distance and
going were fully available in the evaluation sample.

## Interpretation

There is no evidence for modifying the general Horse Ability number using this
simple speciality profile. Base ratings therefore remain Natural Fling 99.67,
Sheza Alibi 110.83 and Gringotts 110.28 on initial chronological figures.

Distance and going remain relevant to expected performance in a particular
race. Preserve the profile architecture for the later race-specific layer,
but do not force it into Horse Ability without predictive evidence.

## Decision

Freeze this component at zero and proceed to the final Horse Ability gate.
