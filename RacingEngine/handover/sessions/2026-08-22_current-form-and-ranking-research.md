# Handover — current form and race-level ranking

Date: 22 August 2026

## Outcome

Implemented Steps 1 and 2 of the improvement plan in
`racing_engine/form_ranking_research.py`. The research uses complete race-level
probability books and only point-in-time information. Coefficients are fitted on
the frozen 2023–24 training period; validation and holdout are scoring-only.

No model was promoted. Every candidate improved log loss and Brier directionally
in train, validation and holdout, but every 95% validation interval included
zero. This is promising evidence, not sufficient evidence.

## Leading candidate

`race-level-conditional-logit-v1.0-core-cv`

- validation log-loss delta: `-0.003060`
- validation Brier delta: `-0.000719`
- validation 95% interval: `[-0.006350, 0.000264]`
- holdout log-loss delta: `-0.005944`
- holdout Brier delta: `-0.001266`
- holdout 95% interval: `[-0.010329, -0.001637]`
- validation top-pick delta: `-0.25pp`
- holdout top-pick delta: `-0.13pp`

Regularization (`0.20`) was selected by a chronological 70/30 split within
training only. Freeze this candidate for prospective confirmation. Do not tune
it further using the already-observed validation or historical holdout.

## Rejected full version

The full race model included prior Race Strength. Although log loss improved,
holdout top-pick strike rate declined by 1.26 percentage points. Prior strength
also received a negative coefficient, which may reflect placement, fatigue or
regression rather than a causal disadvantage. Do not promote this formulation.

## Market boundary

Market comparisons will cover only 2025 through 15 August 2026. The engine is
first and foremost a ratings engine. Future pricing will separately add current
weight, barriers, course/map and race-day context. Once timestamped markets are
available, freeze and report the rule: bet only at 15% or more expected value
against opening price; separately compare outcomes and closing-line value.

## Next action

Switch branches rather than tuning this model again. Recommended next branch is
time and winning-margin interpretation. Alternatively collect Betfair history
and better pre-race cards. Prospective races can later confirm or reject the
frozen race-core candidate.

## Verification

```bash
.venv/bin/python -m racing_engine.form_ranking_research \
  --output data/outputs/current_form_ranking_research_2026-08-22.json
.venv/bin/python -m unittest discover -s tests -v
```
