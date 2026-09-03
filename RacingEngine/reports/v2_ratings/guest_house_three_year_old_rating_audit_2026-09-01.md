# Guest House and three-year-old rating audit — 1 September 2026

## Verdict

The accepted `form-first-v2.0` figure of **98.46** for Guest House's San
Domenico win is not a reliable expression of the merit of that run. The input
data is now present and the arithmetic is operating as coded, but the model
architecture compresses lightly raced age-restricted fields. This is a model
specification problem, not a missing-times problem and not a one-horse data
error.

It is also not safe to mechanically replace 98.46 with Daniel O'Sullivan's
101. The two scales are different. The defensible conclusion is that Guest
House belongs above the accepted figure. Existing internal shadows put the run
between **102.00 and 104.30**, with the separated achieved-run model at
**104.30**. That range is consistent with the owner's suggested conversion of
O'Sullivan's 101, but no production rating should be overwritten until the
age-restricted fix passes historical and untouched validation.

## Exact Guest House calculation

Rosehill R8 on 29 August 2026 was a three-year-old Group 3 over 1100m. Guest
House won by 1.25 lengths carrying 58.5kg. The database contains a valid
official 62.41-second clock, individual runner clocks and sectionals.

The accepted engine assigns every Group 3 a class standard of 105. It then
constructs four adjusted prior-form anchors:

| Principal | Prior selected by engine | Adjusted anchor |
|---|---:|---:|
| Guest House | official 102 | 102.00 |
| Blue Door | official 81 | 92.26 |
| Music Time | official 92 | 101.40 |
| Half Pipe | official 64 | 77.98 |

The median is 96.83. With complete anchor coverage, the model gives that
collateral median 80% weight and the G3 standard only 20%:

`0.80 × 96.8282 + 0.20 × 105 = 98.4626`

The winner then receives zero margin credit. Consequently, Guest House can
start the race with an official 102, beat the field by 1.25 lengths, and be
assigned only 98.46. The result is internally consistent with the code, but it
is not a sensible achieved-run update.

The same compression affected the Golden Slipper: the accepted engine rated
that Group 1 win only 96.11. Therefore the issue predates the San Domenico and
cannot be explained by the recently missing Rosehill clock alone.

## Systematic cohort audit

Winner runs from 1 September 2023 through 31 August 2026 were classified from
the stored race descriptions. The comparison below is accepted winner rating
minus the engine's class standard.

| Grade | 3YO-only races | Mean gap | Open-age races | Mean gap | Difference |
|---|---:|---:|---:|---:|---:|
| Group 1 | 41 | -18.37 | 118 | -1.58 | -16.79 |
| Group 2 | 68 | -23.38 | 120 | -4.57 | -18.82 |
| Group 3 | 83 | -22.38 | 176 | -4.81 | -17.57 |
| Listed | 67 | -19.52 | 117 | -2.18 | -17.34 |
| **All four grades** | **259** | **-21.27** | **531** | **-3.46** | **-17.81** |

That pattern persists within every grade, so it is not caused merely by a
different mix of G1, G2, G3 and Listed races. Two-year-old-only races are also
compressed (114 winners averaged 20.28 points below their class standard).

This does not mean an age-restricted G3 must equal an open-age G3; nominal race
grades vary in actual strength. However, a consistent 17–19 point separation
at every grade means the accepted figures are not on one comparable
performance scale. It is especially damaging when assessing whether a young
horse can graduate to open-age company.

## What is wrong in the build

1. **Immature priors receive maximum authority.** Full top-four coverage is
   treated as strong evidence and immediately gives collateral 80% weight.
   Coverage is not reliability. Four lightly raced horses with unstable or
   stale priors can provide complete but weak evidence.
2. **The median lets a low immature rival pull the whole race down.** Half
   Pipe's adjusted 77.98 pushes the median below Guest House's own 102 prior.
   The model has no rule preventing a decisive winner from being downgraded by
   fragile beaten-horse anchors.
3. **Official rating always overrides internal history when available.** The
   engine does not blend the official figure with recency, number of starts,
   dispersion or progression. This is particularly unsuitable for rapidly
   developing horses.
4. **Winning margin is discarded.** Guest House's 1.25-length margin contributes
   zero. At the engine's 1100m conversion it represents 3.54 points of
   observable separation before any conservative shrinkage.
5. **Time and sectionals do not set the level.** The valid 62.41 clock increases
   confidence, but the accepted rating explicitly records that neither time nor
   sectionals affects performance level. The historical shadow rows still say
   `no_valid_clock` because they have not been rebuilt after the timing backfill.
6. **There is no age/WFA normalisation.** Age is absent from the accepted
   calculation. Weight differences within the race are adjusted, but there is
   no normalisation that makes performances directly comparable across age,
   sex and time of year.

This explains why many older-horse ratings can look correct. In an established
open field, principals have longer, steadier rating histories and collateral
anchoring works much better. The defect becomes conspicuous where the field is
young, lightly raced and improving.

## Comparison with O'Sullivan's method

Published descriptions of WFA Performance Ratings say they are normalised to
weight-for-age so performances can be compared regardless of age, sex,
distance and time of year. They use race times, sectional times, margin spread,
previous ratings and weights carried. O'Sullivan has also specifically written
that this multi-dimensional method is intended to recognise talented lightly
raced horses earlier than traditional ratings.

Our accepted engine currently does almost the inverse in this case: it gives
dominant authority to previous collateral, ignores time and sectionals for the
level, gives the winner no margin credit, and has no WFA normalisation. The
101-versus-98.46 disagreement is therefore unsurprising.

## Existing shadows and why not to promote blindly

| Candidate | Guest House figure | Explanation |
|---|---:|---|
| Accepted form-first v2.0 | 98.46 | 80% collateral, no winner margin |
| v2.1 margin/weight shadow | 102.00 | adds full 3.54 margin component |
| v2.3 calibrated shadow | 99.70 | adds only 35% of margin update |
| v2.4 opposition shadow | 99.19 | weak opposition revises level down |
| v2.6 separated achieved run | **104.30** | reliability-adjusted strength 100.76 plus full margin |
| v2.7/v2.9 shadows | 99.19 | breakout rule requires a margin of at least 3L |

V2.6 gives the most conceptually appropriate answer for this particular case:
separate the strength of opposition from what the winner demonstrably achieved.
But earlier broad testing found unacceptable false positives from generous
winner-margin treatment, and later models imposed a blunt three-length gate.
Neither extreme is ready for production.

## Recommended repair and validation

Build a targeted research candidate, leaving `form-first-v2.0` frozen:

1. Calculate a true achieved-run layer using WFA/sex normalisation, margin
   spread, meeting-variant-adjusted time and pace-normalised sectionals.
2. Estimate principal-anchor reliability from starts, recency, prior dispersion,
   age and progression. Four weak anchors must not equal four established ones.
3. Separate achieved run, current latent ability and future development. Age
   should control uncertainty and expected development, not become a crude
   bonus added to every three-year-old.
4. Give winning margin positive but shrinkable credit. Let independent time,
   sectional and subsequent collateral evidence determine how much survives.
5. Rebuild the time/pace/energy shadows now that Rosehill timing is populated;
   do not interpret the stale `no_valid_clock` shadow as evidence against the
   run.
6. Validate by age (2YO/3YO/4YO+), sex, number of prior starts, grade, state and
   distance. Test future-rating error, rank calibration and false-breakout rate,
   not whether Guest House alone reaches a preferred number.
7. Preserve the 2026 live cohort as an untouched final test and require the fix
   to improve young-horse cohorts without inflating established open-age races.

## Bottom line

Something is wrong, and it is primarily the accepted model's treatment of
young, lightly raced fields. Guest House's raw inputs are now adequate. The
98.46 arises because fragile beaten-horse priors own 80% of the race level,
while the win margin, valid time, sectionals and WFA development context own
none of it. Treat **102–104.3** as the credible internal research interval for
this run, with **about 104** a reasonable working interpretation on our scale;
retain 98.46 only as the frozen accepted-model output until the targeted rebuild
passes cohort validation.
