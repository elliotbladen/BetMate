# Expected Tempo Engine — Step 1 dataset

Date: 3 September 2026
Status: Step 1 built; research/shadow only

## Boundary

This is a standalone race-tempo dataset. It does not modify horse ratings,
prices, accepted `form-first-v2.0`, or the V2.10 promotion state.

`feature_*` columns are candidate pre-race inputs. `target_*` columns are
post-race sectional outcomes and are prohibited from live prediction inputs.
Runner pressure profiles use only observations from strictly earlier race
dates; same-day and future observations are excluded.

## Artifacts

- Builder: `racing_engine/expected_tempo_dataset.py`
- Dataset: `reports/expected_tempo/expected_tempo_step1.csv`
- Contract: `reports/expected_tempo/expected_tempo_step1_schema.json`
- Coverage manifest: `reports/expected_tempo/expected_tempo_step1_manifest.json`
- Tests: `tests/test_expected_tempo_dataset.py`

The initial build contains 1,565 races from 26 August 2023 through 15 August
2026: 999 Good, 487 Soft and 79 Heavy. It contains 454 NSW and 1,111 Victorian
races. Pace targets come from `pace-shape-v2.1-pit-shadow`.

## Evidence limits retained explicitly

- Historical official going and rail are included, but their pre-race freeze
  timestamps were not preserved; their verification flags therefore remain 0.
- Timestamp-matched weather is present, but historical observed weather is not
  automatically equivalent to a future weather forecast.
- Wind speed/direction are stored. Headwind and crosswind components remain
  null until surveyed course/section bearings are sourced.
- No synthetic rail, weather, sectional or map values are imputed.
- The current V2.1 pace table ends 15 August 2026 and must be refreshed before
  later August races can enter this dataset.

## Next step

Step 2 should define going/track/distance/class-specific pace targets using
walk-forward, prior-only pars and assess whether thin Heavy and Group samples
need hierarchical pooling rather than isolated buckets.
