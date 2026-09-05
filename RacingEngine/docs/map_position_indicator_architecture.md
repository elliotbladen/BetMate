# Map Position Indicator — Review Architecture

Date: 4 September 2026  
Proposed version: `map-position-shadow-v1`  
Status: architecture only; no prices or ratings may consume it yet

## 1. Product boundary

The Map Position Indicator predicts where every runner will settle after the
field has established order. It does not predict the winner and it does not
replace the standalone Expected Tempo Engine.

The primary output is a probability distribution, not one deterministic map:

```text
leader | outside-leader | leaders-back | one-one | midfield-covered
midfield-wide | rear-covered | rear-wide
```

For display these may be compressed to `leader`, `on_pace`, `midfield` and
`backmarker`. The detailed states remain available to the simulator and future
Pricing Engine.

```text
historical runner behaviour   today's race context     live race-day context
sectionals + positions        barriers + geometry     scratchings + tactics
stewards + reliability        field competitors       rail + going + wind
            \                       |                       /
             +------ runner intent/location model --------+
                                      |
                         constrained field simulation
                                      |
                    position probabilities + uncertainty
                                      |
            Expected Tempo Engine (separate, two-way exchange)
                                      |
                    future Pricing Engine (after promotion)
```

## 2. Source inventory

### Already stored

- `runner_sectionals`: 235,621 observations, including sectional time,
  position at marker, distance travelled and speed where supplied.
- `canonical_sectionals`: early-to-800 and 800/600/400/200 positions where
  available.
- `v2_vic_200m_sectionals`: official Victorian 200m splits and positions.
- `runner_results`: barriers, jockeys, trainers, finish time and result status.
- `steward_events`: 6,774 structured events, currently predominantly Victoria.
- `race_weather`: timestamped Meteostat weather.
- `v2_race_pace_shapes`: completed-race early/middle/late pace and pressure.
- Existing Expected Tempo V0/live infrastructure and Supabase/Railway design.

### New or expanded sources

| Data | Primary source | Collection timing |
|---|---|---|
| NSW steward reports | Racing NSW official stewards archive | Historical backfill, then after each meeting |
| Fields, barriers, riders, gear | Racing NSW and Racing.com official cards | Nominations, acceptances and regular race-day polls |
| Scratchings | Official race cards/scratchings | Five-minute polls inside race-day window |
| Rail and going | Official meeting information | Acceptances, race morning and every reported change |
| Change of tactics | Official steward/race-day notification | Poll to jump; immutable timestamped events |
| Sectionals/positions | ATC timing PDFs and Racing.com official feed | After each completed race |
| Weather | Meteostat plus available official live observations | Nearest causal observation before jump |

All source records require `source_url`, `observed_at`, `effective_at`,
`collected_at`, payload hash and parser version. Missing evidence stays null.

## 3. Deriving early time correctly

The missing `early_to_800_seconds` value can be reconstructed when all required
evidence exists.

If `marker_metres` means metres remaining to the finish:

```text
time_start_to_800_remaining
    = official_finish_time
    - cumulative_time_from_800_remaining_to_finish

cumulative_time_from_800_remaining_to_finish
    = split(800→600) + split(600→400)
    + split(400→200) + split(200→finish)
```

Example: in a 1,200m race this produces the runner's time for the opening 400m.
For a 1,600m race it produces the opening 800m. The feature must therefore also
store the distance actually travelled before the 800m-remaining marker and be
normalized by track/distance/going; raw seconds are not comparable between the
two races.

Derivation is allowed only when:

1. the official runner finish time is available;
2. every interval from 800m remaining to the finish is observed;
3. the intervals are non-overlapping and use the same split/cumulative meaning;
4. runner, race and source identities agree;
5. the sum is positive and not greater than finish time; and
6. split-sum tolerance and source-specific sanity checks pass.

Store both observed and derived values, never overwrite the source:

```text
early_time_seconds
early_time_origin = observed | derived_finish_minus_late | unavailable
late_chain_seconds
late_chain_coverage
derivation_formula_version
quality_status
```

This will materially increase usable early-speed coverage, but it cannot repair
a missing finish time, a missing late interval, or an ambiguous sectional feed.

## 4. Historical runner profile

Create one point-in-time observation after every run, using only evidence known
after that run. A live card may use only observations strictly before its jump.

### Core features

- Early velocity and early rank relative to that field.
- Position at the first reliable call and at 800m/600m.
- Leader/on-pace/midfield/rear state.
- Rail/one-off/wide state only when supported by path or steward evidence.
- Barrier percentile after scratchings.
- Distance, track, turn configuration, going and field size.
- Jockey, trainer, gear and preparation stage.
- Slow-start, awkward-start, over-racing, restrained and wide/no-cover events.

### Reliability outputs

For each horse and comparable regime calculate:

- posterior probability for each map state;
- early-speed mean and uncertainty;
- slow-start probability;
- position entropy/volatility;
- sample size and recency-weighted effective sample size;
- evidence coverage and source quality.

A partial-pooling hierarchy prevents lightly raced horses being treated as
certain:

```text
horse history
  -> horse × distance band
  -> trainer/jockey/context priors
  -> age/experience cohort prior
  -> population prior
```

## 5. NSW stewards pipeline

Build a separate official Racing NSW adapter rather than mixing NSW text into
the Victorian parser.

```text
official meeting/report index
        -> download immutable PDF/HTML
        -> identify race and horse
        -> preserve exact evidence excerpt
        -> deterministic category parser
        -> confidence + human-review flag
        -> append steward_events
```

Required new categories include:

- `change_tactics_forward`
- `change_tactics_back`
- `slow_start`
- `began_awkwardly`
- `failed_to_muster`
- `restrained_for_cover`
- `overraced`
- `barrier_fractious`
- `wide_no_cover`
- `unexpected_position`

Intent and outcome remain separate. “To be ridden forward” is pre-race intent;
“settled back” is the observed result. Intent shifts probabilities but does not
force a map position.

## 6. Course geometry and barrier model

Create a small manually verified registry for each Sydney and Melbourne
track/distance configuration:

```text
track_slug, course_variant, distance_metres, start_lat, start_lon,
first_turn_distance_metres, turn_direction, first_turn_radius,
straight_distance_metres, nominal_track_width_metres,
rail_position_raw, effective_width_adjustment, source_url, verified_at
```

The barrier model consumes barrier percentile after scratchings, run to first
turn, field size, turn direction and competitors' speed. It must learn choices,
not simplistic barrier bias: press forward, hold, seek cover, race wide, or
restrain.

## 7. Whole-field constrained simulator

Independent horse classifications are not enough because multiple runners
cannot occupy the same lane and rank. For every race, run at least 10,000
Monte Carlo starts:

1. Draw each horse's jump quality and intended early effort.
2. Apply barrier, geometry, jockey/stable-intent and going effects.
3. Simulate the run to the first bend in short distance/time steps.
4. Resolve crossing, rail occupancy, cover and width conflicts.
5. Apply pressure feedback: competing leaders may force restraint or greater
   early expenditure.
6. Record rank, lane, cover, distance travelled and early energy at the map
   checkpoint.

The checkpoint should be geometry-aware: normally established order around
300–400m after the start, but never after a very early first turn where position
must be resolved sooner.

### Interaction with Expected Tempo

The products stay separate:

- Map Engine asks: **where will each horse be?**
- Tempo Engine asks: **how fast will the race phases be?**

V1 flow is map-to-tempo: simulated leader competition and early effort become
field-pressure features for Expected Tempo. Later, a bounded fixed-point pass
may feed tempo back into position probabilities once. Iteration stops after one
pass until stability is validated.

## 8. Race-day automation

Extend the existing Railway/Supabase tempo worker rather than create a second
uncoordinated scheduler.

```text
T-48h/T-24h  card + initial barrier + gear snapshot
T-6h         rail/going/weather + scratchings + baseline map
T-90m        enter five-minute polling window
T-30m        tactics, jockey, gear, scratching and weather refresh
T-5m         freeze auditable pre-jump map snapshot
Race N end   collect result/sectionals/positions
             update meeting bias and tempo state
             recompute only races N+1 onward
Meeting end  ingest official stewards report and score predictions
```

Race-day bias must use causal earlier races only. It should estimate uncertainty
for leader advantage, rail/lane use and wide-run cost. Finishing positions alone
must not manufacture a lane bias; lane claims require observed path/position or
official evidence.

## 9. Storage additions

Proposed append-only tables:

- `map_course_configurations`
- `map_source_snapshots`
- `map_tactical_events`
- `map_runner_history_features`
- `map_pre_race_runner_features`
- `map_simulation_runs`
- `map_runner_predictions`
- `map_field_predictions`
- `map_observed_outcomes`
- `map_evaluations`

Every prediction stores `as_of`, card version, field hash, model version,
simulation seed, feature hashes and the latest permissible evidence timestamp.
Scratchings generate a new prediction; they never mutate an older snapshot.

## 10. User-facing indicator

Each runner receives:

```text
Most likely: on pace, one-off (42%)
Leader: 23% | On pace: 51% | Midfield: 20% | Back: 6%
Expected settling rank: 3.8 of 12
Wide/no-cover risk: 18%
Slow-start risk: 7%
Map confidence: 74/100
Key reasons: barrier 4; consistently top-four at first call; two other leaders
```

The race view shows several sampled maps or a probability heatmap so uncertainty
is visible rather than hidden behind one fixed graphic.

## 11. Validation and promotion gates

Build chronologically and keep V1 shadow-only. Test separately for NSW/Victoria,
track, distance band, going, field size, age/experience and prediction horizon.

Primary metrics:

- multiclass log loss and Brier score;
- accuracy within ±1 and ±2 settling ranks;
- calibration of leader/on-pace/back probabilities;
- slow-start calibration;
- lane/cover accuracy where outcome labels exist;
- performance versus naive last-start position and median-last-three baselines.

No Pricing Engine integration until the model:

1. beats both baselines out of sample overall and in NSW/Victoria;
2. remains calibrated by distance and going;
3. passes leakage and timestamp audits;
4. survives at least 500 genuinely live runner forecasts; and
5. demonstrates incremental pricing or ranking value when added after the
   existing horse-ability and Expected Tempo components.

## 12. Recommended build sequence

1. Implement audited early-time derivation and coverage report.
2. Backfill and parse three years of Racing NSW stewards reports.
3. Build and manually verify Sydney/Melbourne course configurations.
4. Build historical runner-state labels and reliability profiles.
5. Train chronological baseline and probabilistic runner model.
6. Add constrained Monte Carlo whole-field simulation.
7. Extend the cloud worker and run live in shadow mode.
8. Score 500+ live runner forecasts before considering price integration.

## External methodology references

- HKJC describes speed maps as forecasts of position roughly 300–400m after the
  start using historical running style, actual early pace and barrier position:
  https://www.hkjc.com/english/formguide/formstudy_help.asp
- Racing NSW reports distinguish notified tactical intent from the position
  actually obtained and record failure to muster, awkward starts and related
  evidence: https://www.racingnsw.com.au/wp-content/uploads/stewards_reports/23082017W_FM.pdf
- Betfair's Australian barrier guide emphasizes interactions between barrier,
  track, distance, condition and running style rather than a universal draw
  effect: https://www.betfair.com.au/hub/education/racing-strategy/barrier-positions/
