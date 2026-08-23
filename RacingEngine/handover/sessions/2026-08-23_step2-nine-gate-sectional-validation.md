# Handover — Step 2 nine-gate sectional validation

All nine requested gates were executed. The new candidate is `pace-shape-v2.1-pit-shadow`; it remains shadow-only.

## Produced

- Prior-only pars in `racing_engine/pace_shape.py`.
- Chronological next-start and race-ranking ablation in `racing_engine/pace_evaluation.py`.
- Frozen reports in `reports/v2_ratings/pace_shape_v2_1_pit_shadow.json`, `pace_shape_v2_1_evaluation.json`, and `step2_manual_pace_audit.md`.
- Sourced environment policy in `config/course_environment_evidence.json`.
- Persistent named-gap registry `v2_sectional_data_gaps`.

## Findings

1. Representative sprint homes/collapses are directionally detectable; clustered whole-meeting extremes expose inadequate meeting-speed control.
2. Official live wind systems exist, but the required historical track-point archive and surveyed phase bearings were not reproducibly available. No wind adjustment was manufactured.
3. True lane measurement is missing. There are 4,048 clean runners with admissible official steward path events, retained separately.
4. All pars are now point-in-time. Scored coverage is 1,565 races and 15,973 runners.
5. Disadvantaged horses improved +1.39 next run versus -0.18 neutral, but selection/confounding prevents a causal claim.
6. Overall forecast log loss moved only 2.53106 to 2.53098 and strike rate declined.
7. NSW log loss worsened; Victoria improved. The sign disagreement fails promotion.
8. Cox Plate 2024 is very fast early. Pace context correctly recognises Pride Of Jenni's workload, but a negative Via Sistina context adjustment must not diminish the achievement rating.
9. Everest 2025 and Sheza Alibi's Doncaster 2026 sectionals are explicitly permanent current-snapshot gaps; no imputation.

## Next controlled experiment

Freeze V2.1. Build a meeting-speed residual and separate two outputs: (a) achievement sectional ability and (b) trip/pace compensation. Retest both coefficients from zero using the same chronological/jurisdiction gates. Do not move to market EV testing while the underlying accepted ratings and context semantics remain unresolved.
