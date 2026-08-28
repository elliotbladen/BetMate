# Handover — Horse Ability V2.2 separated achievement

Reran Horse Ability on `achieved-run-v2.7-breakout-separated-shadow` as
`horse-ability-v2.2-separated-achievement-shadow`. Natural Fling's achieved
104.22 becomes sustainable ability 99.17 with uncertainty 10.50 from two runs.
This is the intended separation; her upstream audit now passes.

Validation log loss is 2.33281 and directionally beats rejected V2, V1 and
uniform. Historical holdout beats V1 and uniform but trails rejected V2 by
0.00061. Required validation uncertainty versus V1/uniform still crosses zero.
The observed 19-race prospective diagnostic improves all baselines but is not
an untouched promotion set. Decision: revise/freeze, not promote.

Next build: training-only history-depth/uncertainty calibration. Do not retune
the sustainable-peak blend against the already observed validation/holdout.
Accepted run ratings and Horse Ability remain unchanged.
