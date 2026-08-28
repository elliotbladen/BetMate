# Handicap weight rematch calibration findings

Date: 28 August 2026  
Version: `handicap-weight-rematch-v1`  
Decision: **25% initial response; later collateral revision remains separate**

## Method

For each pair of horses meeting in a handicap, compare their adjusted
performance gap with their first subsequent WFA/set-weight rematch within 365
days. Fit on pre-2025 handicap races only. Sheza Alibi, Gringotts and Tropicus
are excluded from fitting.

## Broad result

There are 860 training pairs and 649 later validation pairs. Training selects
25% of the parent weight component: MAE 9.981 versus 10.125 at zero and 10.854
at full response. On validation, 25% records 9.215 versus 9.295 at zero and
10.592 at full response. The direction repeats, although the effect is modest.

Group 1 training pairs select 15% (218 pairs); Group 1 miles select zero (122
pairs). This does not support a universal 50% elite-handicap coefficient.

## Sheza Alibi and Gringotts

Their 4 April Doncaster gap under the later 22 August WFA result implies a
55.91% response. That maps Gringotts' Doncaster run to approximately **109.62**
relative to Sheza's 113.49, matching the later WFA gap of 3.87 rating points.

The global initial 25% rule would rate Gringotts about **103.15** and predicts a
10.35-point deficit; it is too low for this named rematch. Full response rates
him 118.85 and is too high both broadly and relative to the rematch.

## Architecture decision

Use the training-supported 25% only as an initial generic handicap response.
When a genuine later level-weight rematch becomes available, store a separate
retrospective collateral revision rather than changing the global coefficient.
For this Doncaster, the evidence-supported revised figure is about 109.62.
This is retrospective race interpretation and must never leak into predictions
made before 22 August.
