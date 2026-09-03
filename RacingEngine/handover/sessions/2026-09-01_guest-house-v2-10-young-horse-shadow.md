# Handover — Guest House audit and V2.10 young-horse shadow

Date: 1 September 2026  
Workspace: `F:\dev\BetMate\RacingEngine`

## User objective

Investigate why Guest House rated 98.46 internally while Daniel O'Sullivan had
the performance around 101 on his scale, determine whether the engine mishandles
three-year-olds, research the methodology difference, and build a safer
research candidate without damaging otherwise sensible ratings.

## Diagnosis

The accepted model `form-first-v2.0` is mathematically operating as coded, but
its architecture compresses lightly raced age-restricted fields.

For Guest House's Rosehill R8 Group 3 win on 29 August 2026:

- Official pre-race rating: 102
- Accepted class standard: 105
- Adjusted top-four collateral anchors: 102.00, 92.26, 101.40 and 77.98
- Median collateral anchor: 96.8282
- Accepted level: `0.80 × 96.8282 + 0.20 × 105 = 98.4626`
- The accepted winner received no positive credit for the 1.25-length margin.
- Valid time and sectionals affected confidence but not rating level.
- There was no age/WFA normalisation in the accepted calculation.

Historical Listed/Group winner audit from September 2023 through August 2026:

| Cohort | Accepted winner rating minus class standard |
|---|---:|
| 2YO only | -20.28 |
| 3YO only | -21.27 |
| Open age | -3.46 |

The difference persisted separately across Listed, G3, G2 and G1 races. The
problem is therefore systematic, although nominal age-restricted and open-age
grades need not have identical strength.

## Research conclusion

Published descriptions of Daniel O'Sullivan's WFA Performance Ratings say they
normalise performances across age, sex, distance and time of year and consider
time, sectionals, margins, previous ratings and carried weight. The accepted
engine is much more collateral-dominant and excludes time, sectionals and
winning margin from the level. The two numerical scales are not directly
interchangeable, but the methodological difference explains the disagreement.

Full audit:
`reports/v2_ratings/guest_house_three_year_old_rating_audit_2026-09-01.md`

Reproducible diagnostic:
`reports/data/diagnose_guest_house_rating.py`

## V2.10 implementation

Added research model:
`racing_engine/achieved_run_young_wfa.py`

Model version:
`achieved-run-v2.10-young-wfa-shadow`

Key behaviour:

- Leaves `form-first-v2.0` unchanged.
- Caps opposition authority at 50% in unambiguous 2YO/3YO-only races and 80%
  otherwise.
- Uses reliability of principals rather than treating row coverage as proof of
  stable collateral.
- Retains 50% of observable winner-margin credit by default, plus 25% for a
  supporting contextual clock and 25% for supporting sectional achievement.
- Audits dated age/sex/WFA profiles where available.
- Does not invent missing age or sex.
- Treats WFA/set-weight allowances as neutral rather than merit.
- Keeps time and sectional values as margin corroboration only because their
  standalone promotion gates have not passed.

Historical build produced:

- 2,732 races
- 29,355 performances
- 11,756 performances with profile coverage
- 17,599 performances without profile coverage

Unit tests:
`tests/test_achieved_run_young_wfa.py`

All 11 relevant V2.10, separated-achievement and WFA tests passed.

## Evidence rebuild

Rebuilt contextual time evidence and hierarchical 200m energy/sectional
evidence through 29 August 2026.

Updated reports:

- `reports/v2_ratings/race_time_context_v2_1.json`
- `reports/v2_ratings/energy_sectionals_v2_5_build.json`
- `reports/v2_ratings/energy_sectionals_v2_5_evaluation.json`

The contextual time model's standalone forward gate remains not promoted. Its
2025-onward improvement was very small and its confidence interval crossed
zero.

## Headline ratings

| Horse/run | Accepted | V2.10 achieved run | Notes |
|---|---:|---:|---|
| Guest House, Rosehill R8, 29 Aug | 98.46 | **104.30** | 100.76 strength + 3.54 margin; time and sectionals both supported full margin |
| Oliveanotherday, Caulfield R6, 29 Aug | 110.46 | **110.36** | 107.17 strength + 3.19 margin; strong +1.61 MAD clock |
| Natural Fling, Caulfield R6, 15 Aug | 83.53 | **98.55** | 92.89 strength + 5.67 margin; retained 50% because adjusted clock and late-achievement evidence did not corroborate full margin |

Performance ordering is sensible: Oliveanotherday 110.36, Guest House 104.30,
Natural Fling 98.55.

Natural Fling is an important review case. The earlier full-margin V2.6 shadow
was approximately 104.22, while V2.10 is 98.55. This must be assessed through
future form rather than manually selected.

Generic horse query helper:
`reports/data/query_horse_weekend_rating.py`

## Validation result

V2.10 reduced mean young Group/Listed compression:

| Cohort | Accepted gap to standard | V2.10 gap to standard |
|---|---:|---:|
| 2YO only | -20.28 | -5.37 |
| 3YO only | -21.28 | -8.42 |
| Open age | -3.45 | -2.36 |

However, the full achieved-run uplift is not suitable as an automatic
next-start forecast. Shrinkage was selected before 1 January 2025 and tested on
2025 onward:

| Group/Listed cohort | Accepted MAE | Full V2.10 MAE | Selected carry | Shrunk MAE |
|---|---:|---:|---:|---:|
| 2YO | 11.71 | 19.43 | 0% | 11.71 |
| 3YO | 8.36 | 10.16 | 15% | **7.68** |
| Open age | 6.39 | 6.75 | 40% | 6.41 |

This validates separation of completed-run achievement from current/next-start
ability. Guest House can have a 104.30 achieved run without automatically
becoming a 104.30 next-start forecast.

Detailed findings:
`reports/v2_ratings/achieved_run_v2_10_young_wfa_findings.md`

Machine-readable results:
`reports/v2_ratings/achieved_run_v2_10_young_wfa.json`

## Current operating status

- Accepted production model: `form-first-v2.0`
- V2.10 status: **SHADOW_ONLY_AMBER**
- Betting/pricing continues to use the accepted model.
- No production switch is authorised.
- Suggested reviews: three-month safety, six-month restricted-promotion and
  twelve-month full-promotion review.

Persistent instructions and policy were added so later sessions do not depend
on conversation memory:

- `AGENTS.md`
- `handover/CURRENT_RATINGS_STATE.md`
- `config/v2_10_promotion_policy.json`

Future sessions working inside RacingEngine must read the current state and
policy before changing or reporting ratings.

## Exact next implementation

Build deterministic prospective monitoring; a permanent autonomous agent is
not required.

Required workflow:

1. Create an append-only snapshot table/command run after each meeting.
2. Freeze accepted rating, V2.10 achieved rating, V2.10 next-start state,
   evidence availability, model versions and calculation timestamp.
3. Never overwrite a frozen prospective snapshot.
4. When a horse next runs, attach its outcome to the earlier prediction.
5. Generate monthly green/amber/red scorecards covering next-start MAE,
   race-ranking/log loss, false breakouts, data coverage, NSW/Victoria, sex,
   age, grade and open-age safety.
6. Apply the fixed gates in `config/v2_10_promotion_policy.json`.
7. Record formal decisions at three, six and twelve months.

Do not claim monitoring is automatic until the snapshot, matching and scheduled
scorecard workflow has actually been built and run.

## Worktree caution

The wider BetMate worktree contains extensive unrelated user changes across
football, NFL, tipping and racing ingestion. Preserve them. This session added
or updated only the V2.10 research, reports, evidence outputs, diagnostics and
persistent RacingEngine instructions described above.
