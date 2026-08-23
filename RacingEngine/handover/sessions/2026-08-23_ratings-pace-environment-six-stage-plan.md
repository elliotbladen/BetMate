# Handover: ratings pace/environment six-stage plan

Date: 23 August 2026

## Decision

The project is a Ratings Engine first. It estimates completed-run performance
and sustainable ability and is expected to provide roughly 60–65% of the later
Pricing Engine. Market prices, EV and betting do not enter until Step 6.

Pace/sectionals are a core requirement. The engine must identify pace shape,
contributors, beneficiaries and disadvantaged horses and provide probabilistic
alternative-pace scenarios. It must not claim a counterfactual winner with
certainty.

## Six stages

1. Base Run Figure: clean results, margins, weight/WFA, standards and anchors.
2. Pace/environment: canonical sectionals, race shape, observed race-level
   wind/rain/track/lane/rail/DT-W/stewards and bounded workload adjustments.
3. Collateral back-handicapping: later form revises earlier races in separate
   retrospective and point-in-time modes.
4. Sustainable Ability: repeatable overall/distance/sectional traits with
   recency and uncertainty.
5. Pace counterfactuals: scenario ratings/order/likelihood under alternative
   plausible pace regimes; ratings freeze only after validation.
6. Pricing/market test: add today's time-stamped evidence, calibrate prices and
   test de-vigged opening/closing markets including a predeclared 20%+ EV subset.

## Immediate build position

Step 1 is active. Preserve the accepted V2 clean data layer. Fix elite Race
Strength anchoring and named-race audits before Step 2 rating adjustments.

Step 2 already has a known prerequisite: `canonical-sectionals-v1.0` supports
the old NSW source but not `racing-com-nsw-authorised-v2`. Rebuild canonical
features only on official V2 runner keys. Raw matched coverage currently spans
about 988 NSW and 1,330 Victorian races. No sectional/environment adjustment is
currently active in `form-first-v2.0`.

Historical conditions observed during the completed race belong in Step 2.
Forecast/live conditions available before a future race belong in Step 6.
Prevent double counting across wind exposure, wide/no-cover reports, DT-W,
lane disadvantage and sectional loss.

## Step 2 implementation update

`pace-shape-v2.0-shadow` is materialised in `v2_race_pace_shapes`,
`v2_runner_pace_ratings`, `v2_sectional_quarantine` and
`v2_race_environments`. It covers 1,865 pace-classified races and 18,995
runners. Weather is matched for all 2,720 clean races; 1,079 have official
Victorian steward reports; none has structured lane evidence. Head/crosswind
components are deliberately null pending surveyed course-section bearings.

Named audit findings: Cox Plate = pace collapse; Queen Elizabeth = fast early;
Doncaster = even at 75% runner coverage but no Sheza Alibi personal sectional;
Everest = no matched sectional report. Do not infer missing splits.

No shadow pace adjustment is integrated into official V2 ratings. Next work is
data/validation: course bearings, lane/path source, manual archetype audit,
point-in-time pars and next-run/ablation tests. All 83 tests pass.

## Documents

- `docs/ratings_build_plan.md`
- `docs/ratings_build_notes.md`
- `docs/v2_ratings_architecture.md`
- `handover/sessions/2026-08-23_controlled-v2-ratings-rebuild.md`
