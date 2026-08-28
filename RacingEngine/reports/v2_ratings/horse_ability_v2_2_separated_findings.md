# Horse Ability V2.2 separated-achievement findings

Date: 28 August 2026  
Version: `horse-ability-v2.2-separated-achievement-shadow`  
Input: `achieved-run-v2.7-breakout-separated-shadow`  
Decision: **revise or freeze; not promoted**

## Current named states

- Natural Fling: achieved run **104.22**, sustainable ability **99.17**,
  uncertainty 10.50, two rated runs.
- Autumn Glow: 115.85.
- Gringotts: 112.32.
- Sheza Alibi: 107.76.

Natural Fling is no longer blocked upstream. The ability layer appropriately
shrinks a single exceptional run rather than erasing it or carrying it forward
at full value.

## Chronological evaluation

| Period | Candidate log loss | vs rejected V2 | vs V1 | vs uniform |
| --- | ---: | ---: | ---: | ---: |
| Validation | 2.33281 | -0.01443 | -0.00041 | -0.00721 |
| Historical holdout | 2.32740 | +0.00061 | -0.00752 | -0.01337 |
| Observed prospective diagnostic | 2.24473 | -0.03352 | -0.03282 | -0.00474 |

Negative deltas favour V2.2. Compared with the first Horse Ability candidate,
validation versus V1 moved from a 0.00094 loss to a 0.00041 improvement, and
the historical-holdout deficit to rejected V2 narrowed from 0.00127 to 0.00061.

Promotion still fails because the historical holdout does not beat rejected
V2, while validation intervals against V1 and uniform include zero. The
prospective period contains only 19 races and was already observed, so its
strong direction is diagnostic rather than promotion evidence.

## Next candidate

Do not tune V2.2 against validation or holdout. The registered next family is
explicit history-depth and uncertainty calibration selected using training
data only. It should decide how quickly one/two-run breakouts approach their
achieved figure, without changing V2.7 achieved runs.
