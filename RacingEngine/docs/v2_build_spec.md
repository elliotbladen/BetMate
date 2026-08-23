# RacingEngine deferred research note: daily variant, campaign stage, track bias

Date: 2026-08-16. Status audited: 2026-08-20.

> **Deferred; not implemented and not the active V2 build plan.** The agreed
> next modelling step is class prior plus Race Strength Rating, as recorded in
> `project_tracker.md`. The empirical findings and proposed mechanics below are
> retained for later review; they must not be read as current code behavior or
> approved core rating architecture.

---

## Build order and dependencies

```
Item 1: Daily Track Variant
  depends on: existing build_pars(), race_results.official_time_seconds
  modifies:   build_performances() — adds variant_component to each run rating
  new table:  daily_track_variants

Item 2: Campaign Stage Weighting
  depends on: run_performances rows (date-ordered per horse)
  modifies:   build_horse_states() — multiplies each run's weight by stage factor
  new columns: run_performances.campaign_stage, run_performances.days_since_last_run

Item 3: Meeting Pattern / Track Bias
  depends on: Item 1 (variant-adjusted residuals), runner_sectionals.position_at_marker
  modifies:   build_performances() — adds bias_component to each run rating
  new table:  meeting_bias_estimates
```

Items 1 and 2 are independent of each other and can be built in either order. Item 3
depends on Item 1 because bias detection uses variant-adjusted residuals (otherwise a
"fast track" day looks like a leader bias day when it's just the whole surface running
quick).

Recommended build sequence: **1 then 2 then 3**. Daily variant gives the biggest
immediate improvement to run ratings. Campaign stage is the simplest code change. Bias
is the most complex and benefits from clean residuals.

---

## Item 1: Daily Track Variant

### What it does

The current V1 par is a long-run median for (track, distance, going). It doesn't know
whether TODAY's surface played fast or slow relative to that median. A daily track
variant is the difference between how a track SHOULD have played (par) and how it
ACTUALLY played (observed race times), estimated from the day's full card.

This is distinct from the going label ("Good 4") which is a pre-race official
assessment. A Good 4 day can play 2 lengths fast if the rail is out, the weather is dry,
and the surface was prepared a particular way.

### Data available

- 257 meetings, average 8.0 races per meeting with official times
- Rail position text stored on `race_results.rail_position` (varied formats)
- Weather per race stored in `race_weather`
- Going bucket already computed per race

### Math

**Step 1: Per-race time residual**

For each race on the day's card at a given track:

```
race_residual_lengths = (par_time - official_time) / SECONDS_PER_LENGTH
```

where `par_time` is the existing V1 median par for (track, distance_bucket, going_bucket).

A positive residual means the race was run faster than the par (track played fast).
A negative residual means slower than par (track played slow).

**Step 2: Meeting-level variant**

```
raw_variant = median(race_residual_lengths for all races at this track on this date)
```

Use median, not mean — one race with a suicidal pace or a walkover tempo should not drag
the estimate.

Minimum 3 races with valid pars required. If fewer, variant = 0.0 (no adjustment).

**Step 3: Shrinkage toward zero**

The raw variant from a small card is noisy. Apply Bayesian shrinkage:

```
n = number of races used
shrinkage_factor = n / (n + VARIANT_SHRINKAGE_K)
daily_variant = raw_variant * shrinkage_factor
```

where `VARIANT_SHRINKAGE_K = 6.0` (a 9-race card gets ~60% weight; a 4-race card gets
~40%). This is a standard precision-based shrinkage prior toward 0.

**Step 4: Distance-band variant (future enhancement, not V2.0)**

Different distances CAN have different variants on the same day (e.g. sprint course
plays true but staying course is into the wind). V2.0 uses a single whole-meeting
variant. When the dataset grows to 500+ meetings, split into sprint (<=1300m) and
route (>1300m) bands if there's evidence they diverge.

**Step 5: Apply to run ratings**

In `build_performances()`, after computing the existing rating:

```
variant_component = -daily_variant
rating = NEUTRAL + time_component + margin_component + sectional_component + variant_component
```

The sign is negative because the variant measures "how fast the track played" — if the
track was 2 lengths fast, every horse got a 2-length gift that isn't intrinsic merit, so
we subtract it.

### Schema

New table `daily_track_variants`:

```sql
CREATE TABLE IF NOT EXISTS daily_track_variants (
    model_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    raw_variant REAL NOT NULL,
    shrunk_variant REAL NOT NULL,
    races_used INTEGER NOT NULL,
    shrinkage_factor REAL NOT NULL,
    method TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (model_version, as_of_date, race_date, track_slug)
);
```

New column on `run_performances`:

```sql
ALTER TABLE run_performances ADD COLUMN variant_component REAL;
```

### Constants

| Name | Value | Rationale |
|------|-------|-----------|
| `VARIANT_SHRINKAGE_K` | 6.0 | 9/15 = 60% weight for a full card; 4/10 = 40% for a short one |
| `VARIANT_MIN_RACES` | 3 | Below this the estimate is noise; default to 0.0 |

### Implementation in performance.py

New function `build_daily_variants()`, called AFTER `build_pars()` and BEFORE
`build_performances()`:

```python
def build_daily_variants(store, as_of_date, pars, *,
                         shrinkage_k=6.0, min_races=3, model_version=MODEL_VERSION):
    """Estimate how fast/slow each meeting's track played vs its long-run par."""
    races = store.connection.execute(
        """SELECT race_date, track_slug, distance_metres, track_condition,
                  official_time_seconds
             FROM race_results
            WHERE race_date < ? AND official_time_seconds IS NOT NULL
              AND distance_metres IS NOT NULL""",
        (as_of_date,),
    ).fetchall()

    # Group by (race_date, track_slug)
    from collections import defaultdict
    grouped = defaultdict(list)
    for race in races:
        key = (race["track_slug"], distance_bucket(race["distance_metres"]),
               going_bucket(race["track_condition"]))
        par = pars.get(key)
        if par is None:
            continue
        residual = (par.time_seconds - float(race["official_time_seconds"])) / SECONDS_PER_LENGTH
        grouped[(race["race_date"], race["track_slug"])].append(residual)

    variants = {}
    for (rd, ts), residuals in grouped.items():
        if len(residuals) < min_races:
            continue
        raw = statistics.median(residuals)
        sf = len(residuals) / (len(residuals) + shrinkage_k)
        shrunk = raw * sf
        variants[(rd, ts)] = shrunk
        # Store to DB...

    return variants
```

Modify `build_performances()` to look up the variant for the run's (race_date,
track_slug) and subtract it.

### Validation

Compare V1 (no variant) vs V2 (with variant) using the existing walk-forward framework:

- **Primary metric:** Brier score on win probability (must improve or be neutral)
- **Secondary:** log loss, mean absolute performance error on next-start rating
- **Diagnostic:** histogram of daily variants — should be roughly symmetric around 0
  with SD ~2-3 lengths. Anything outside [-8, +8] should be flagged for review.

---

## Item 2: Campaign Stage Weighting

### What it does

A horse returning from a spell (first-up) typically runs below its true ability. V1
treats this run at face value, dragging down the horse's current state unfairly. Campaign
stage weighting downweights first-up runs in the horse state calculation so a "pipe
opener" doesn't tank the rating.

This is NOT about predicting whether a horse will improve — it's about how much to trust
each historical run when building the current ability estimate.

### Empirical basis (from our 29,616-runner database)

| Finding | Value | Source |
|---------|-------|--------|
| Gap distribution | 42.3% of inter-run gaps > 42 days | Clear bimodal split |
| Campaign boundary | 60 days (gap > 60d = new campaign) | Bimodal trough at ~50-60d |
| First-up correlation with next run | r = 0.508 | Direct measurement |
| Mid-campaign correlation with next run | r = 0.953 | Direct measurement |
| Ratio (trust multiplier) | 0.508 / 0.953 = 0.533 ~ **0.50** | Rounded conservatively |
| Bad first-up (<85) mean improvement second-up | +5.7 points | Regression to mean |
| Good first-up (>105) mean regression second-up | -4.0 points | Regression to mean |
| Prior campaign rating predicting second-up | r = 0.077 (useless) | Don't use last-campaign rating as a substitute |

### Math

**Step 1: Detect campaign stage**

For each horse's runs in chronological order:

```python
CAMPAIGN_BOUNDARY_DAYS = 60

for each consecutive pair of runs:
    gap = (run_date - previous_run_date).days
    if gap > CAMPAIGN_BOUNDARY_DAYS:
        campaign_number += 1
        runs_this_campaign = 0
    runs_this_campaign += 1

campaign_stage:
    1 = first-up   (runs_this_campaign == 1)
    2 = second-up  (runs_this_campaign == 2)
    3 = third-up+  (runs_this_campaign >= 3)
```

**Step 2: Campaign stage multiplier**

Applied to the run's weight in `build_horse_states()`:

```
CAMPAIGN_MULTIPLIER = {1: 0.50, 2: 0.80, 3: 1.00}
```

These values come directly from the correlation ratios:
- First-up: 0.508/0.953 ≈ 0.50 (half the predictive signal of a mid-campaign run)
- Second-up: intermediate value 0.80 (horses are partially wound up)
- Third-up+: 1.00 (full weight, horse is at campaign fitness)

**Step 3: Uncertainty widening for first-up horses**

In the horse state, a horse whose most recent run is first-up should have wider
uncertainty because their current form is less knowable:

```python
most_recent_stage = campaign_stage of the horse's most recent run
if most_recent_stage == 1:
    uncertainty *= 1.30   # 30% wider band
elif most_recent_stage == 2:
    uncertainty *= 1.15   # 15% wider band
```

This flows naturally into the pricing layer: a wider uncertainty = wider fair price band
= less confident about the horse's true probability.

### Schema changes

Two new columns on `run_performances`:

```sql
ALTER TABLE run_performances ADD COLUMN campaign_stage INTEGER;
ALTER TABLE run_performances ADD COLUMN days_since_last_run INTEGER;
```

New columns on `horse_rating_states`:

```sql
ALTER TABLE horse_rating_states ADD COLUMN most_recent_campaign_stage INTEGER;
ALTER TABLE horse_rating_states ADD COLUMN career_campaigns INTEGER;
```

No new tables needed.

### Implementation in performance.py

**In `build_performances()`**: after computing the run rating, look up the horse's
previous run date to determine `days_since_last_run` and `campaign_stage`. Store both
on the `run_performances` row.

```python
# Inside build_performances(), after the existing runner loop:
# Look up previous run for this horse
prev = store.connection.execute(
    """SELECT race_date FROM run_performances
         WHERE horse_key = ? AND model_version = ? AND as_of_date = ?
           AND race_date < ?
         ORDER BY race_date DESC LIMIT 1""",
    (hkey, model_version, as_of_date, race["race_date"]),
).fetchone()

if prev is None:
    days_since = None
    campaign_stage = 1  # debut or no prior data = treat as first-up
else:
    days_since = (date.fromisoformat(race["race_date"]) - date.fromisoformat(prev[0])).days
    if days_since > CAMPAIGN_BOUNDARY_DAYS:
        campaign_stage = 1
    else:
        # Count consecutive runs within this campaign
        # (simplified: just need the stage of THIS run relative to the last gap)
        campaign_stage = _count_campaign_run(store, hkey, race["race_date"], ...)
```

**In `build_horse_states()`**: modify the weight calculation:

```python
# Current V1:
weight = exp(-ln2 * age / 180) * confidence

# V2:
campaign_mult = CAMPAIGN_MULTIPLIER.get(campaign_stage, 1.0)
weight = exp(-ln2 * age / 180) * confidence * campaign_mult
```

### Constants

| Name | Value | Rationale |
|------|-------|-----------|
| `CAMPAIGN_BOUNDARY_DAYS` | 60 | Bimodal gap distribution trough |
| `CAMPAIGN_MULTIPLIER[1]` | 0.50 | r=0.508 / r=0.953 |
| `CAMPAIGN_MULTIPLIER[2]` | 0.80 | Intermediate (can be refined with more data) |
| `CAMPAIGN_MULTIPLIER[3]` | 1.00 | Full weight for fit horses |
| `UNCERTAINTY_MULT_FIRST_UP` | 1.30 | Conservative 30% wider uncertainty |
| `UNCERTAINTY_MULT_SECOND_UP` | 1.15 | Moderate 15% wider |

### Validation

- **Primary:** walk-forward Brier score (must improve or neutral)
- **Diagnostic:** compare next-start prediction error for first-up horses under V1 vs V2.
  V1 should systematically overreact to bad first-up runs and underreact to good ones.
  V2 should show less bias in both directions.
- **Segment test:** split walk-forward results by campaign stage. V2 should improve
  most on first-up horses, neutral on third-up+.
- **Calibration:** plot model win probability vs actual win rate, binned by campaign
  stage. V1 should underrate first-up horses coming off a bad pipe opener; V2 should
  be flatter.

---

## Item 3: Meeting Pattern / Track Bias

### What it does

On some days at some tracks, leaders win every race. On others, backmarkers dominate.
On some days, the inside rail is dead and wide runners outperform. This is track bias —
a within-meeting pattern caused by rail position, surface preparation, weather during
the day, and venue geometry.

The model detects bias by looking at whether horses in particular running positions or
barrier zones systematically outperformed or underperformed their expected ratings,
AFTER adjusting for the daily variant (Item 1).

### Data available

- 21,968 runners with 800m and/or 400m position data (primarily VIC)
- Barrier on 85% of runner_results rows
- Rail position text on race_results (needs parsing)
- Per-race residuals (from Item 1) available after variant adjustment

### Math

**Step 1: Compute variant-adjusted run residual**

For each finished runner on a given day:

```
expected_rating = horse_state.overall_rating  (prior to this race)
actual_rating = run_performance.performance_rating  (with variant applied from Item 1)
residual = actual_rating - expected_rating
```

A positive residual = horse ran better than expected. Negative = worse.

Only use horses with rated_runs >= 3 and reliability >= 0.50 (otherwise the expected
rating is too uncertain to produce meaningful residuals).

**Step 2: Group residuals by running position**

Map each runner's 800m settling position to a position bucket:

```
position_bucket:
    "leader"     = position_at_800m <= 2
    "on_pace"    = position_at_800m in [3, 4]
    "midfield"   = position_at_800m in [5, 6, 7]
    "back"       = position_at_800m >= 8
```

For each bucket on this meeting:

```
raw_bias_position[bucket] = mean(residuals for runners in this bucket)
```

**Step 3: Group residuals by barrier zone**

Map each runner's barrier to a third of the field:

```
field_size = number of starters in race
barrier_zone:
    "inside"  = barrier <= field_size / 3
    "middle"  = barrier <= 2 * field_size / 3
    "outside" = barrier > 2 * field_size / 3
```

For each zone on this meeting:

```
raw_bias_barrier[zone] = mean(residuals for runners in this zone)
```

**Step 4: Progressive evidence weighting through the card**

A bias detected from 1 race is noise. From 8 races it's signal. Apply progressive
shrinkage:

```
n = number of residuals contributing to this bucket on this meeting
evidence_weight = n / (n + BIAS_SHRINKAGE_K)
bias_estimate = raw_bias * evidence_weight
```

where `BIAS_SHRINKAGE_K = 8.0` (need ~8 data points before the estimate carries
roughly 50% weight).

**Step 5: Cap the adjustment**

```
BIAS_CAP = 3.0  # lengths
bias_component = clamp(position_bias + barrier_bias, -BIAS_CAP, +BIAS_CAP)
```

The two biases (position and barrier) are additive but the total is capped. A horse
that led from an inside barrier on a leader-friendly, inside-friendly day gets a
combined adjustment, but never more than 3.0 lengths — this prevents the model from
retroactively claiming a 6-length winner "should have won by 12" because of bias.

**Step 6: Apply to run ratings**

In `build_performances()`:

```
rating = NEUTRAL + time_component + margin_component + sectional_component
         + variant_component + bias_component
```

Note: the bias_component is SUBTRACTED from the performance rating because it
represents "free lengths" from the track pattern, not intrinsic merit. If leaders got
+2.0 free lengths and this horse led, we subtract 2.0 to get the horse's true merit.

Actually, let me be precise about the sign convention. If leaders outperformed by +2.0
residual (ran better than expected), and this horse was a leader, then:

```
bias_component = -estimated_leader_advantage
```

The horse's performance was inflated by the bias, so we deflate it back to true merit.

### Schema

New table `meeting_bias_estimates`:

```sql
CREATE TABLE IF NOT EXISTS meeting_bias_estimates (
    model_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    dimension TEXT NOT NULL,       -- 'position' or 'barrier'
    bucket TEXT NOT NULL,          -- 'leader', 'on_pace', etc. or 'inside', 'middle', 'outside'
    raw_bias REAL NOT NULL,
    shrunk_bias REAL NOT NULL,
    sample_size INTEGER NOT NULL,
    evidence_weight REAL NOT NULL,
    method TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (model_version, as_of_date, race_date, track_slug, dimension, bucket)
);
```

New column on `run_performances`:

```sql
ALTER TABLE run_performances ADD COLUMN bias_component REAL;
```

### Position data handling

VIC data has `position_at_marker` for 800m and 400m markers (21,968 rows). NSW has
limited position data. When position data is missing, skip bias estimation for that
runner — do not impute.

```python
def _get_settling_position(store, source, race_date, track_slug, race_number, runner_number):
    """Get 800m position as the settling/racing position indicator."""
    row = store.connection.execute(
        """SELECT position_at_marker FROM runner_sectionals
             WHERE source = ? AND race_date = ? AND track_slug = ?
               AND race_number = ? AND runner_number = ? AND marker_metres = 800
               AND position_at_marker IS NOT NULL""",
        (source, race_date, track_slug, race_number, runner_number),
    ).fetchone()
    return row[0] if row else None
```

### Meeting-level bias accumulation

Bias must be estimated across the full card, not per-race. A single race where all
three leaders placed is not evidence of bias — it could be a slow-pace race. But if
leaders outperform across 7 of 9 races on the card, that IS a track pattern.

The implementation accumulates residuals from ALL races at a (race_date, track_slug)
before computing the bias estimate. This is a post-hoc adjustment to historical runs,
not a live prediction during the meeting.

### Constants

| Name | Value | Rationale |
|------|-------|-----------|
| `BIAS_SHRINKAGE_K` | 8.0 | 8 data points = 50% weight; conservative given noisy residuals |
| `BIAS_CAP` | 3.0 | 3 lengths max total (position + barrier). Prevents extreme retroactive claims |
| `BIAS_MIN_RELIABILITY` | 0.50 | Only use residuals from horses with >= 50% reliability in their state |
| `BIAS_MIN_RATED_RUNS` | 3 | Horses with fewer runs have too-uncertain expected ratings |

### Validation

- **Primary:** walk-forward Brier score (must improve or neutral)
- **Diagnostic:** plot per-meeting bias estimates. Expect most meetings to be near zero
  (no strong bias) with occasional outliers of +-2 lengths.
- **Key test:** on meetings where estimated leader bias > +1.5 lengths, do backmarkers
  in the NEXT meeting at that track (same rail position) still underperform? If yes, the
  bias is persistent and predictive. If no, it's meeting-specific and should only adjust
  historical ratings (still useful for cleaning the horse state).
- **Negative test:** rail positions that differ between meetings at the same track should
  show different bias patterns. If "Out 7m" and "True" show the same bias, the estimate
  is capturing noise not signal.

---

## Pipeline integration

The updated `run_pipeline()` function becomes:

```python
def run_pipeline(store, as_of_date, *, min_par_sample=5, model_version=MODEL_VERSION):
    # Phase 1: build pars (unchanged)
    pars = build_pars(store, as_of_date, min_sample=min_par_sample,
                      model_version=model_version)

    # Phase 2: daily track variants (NEW)
    variants = build_daily_variants(store, as_of_date, pars,
                                    model_version=model_version)

    # Phase 3: run performances with variant adjustment (MODIFIED)
    performances = build_performances(store, as_of_date, pars=pars,
                                      variants=variants,
                                      min_par_sample=min_par_sample,
                                      model_version=model_version)

    # Phase 4: meeting bias estimates (NEW)
    #   Requires horse states from a PRIOR as_of_date for expected ratings.
    #   On the first run, skip bias (no prior states). On subsequent runs,
    #   use the most recent prior horse_rating_states.
    biases = build_meeting_biases(store, as_of_date, model_version=model_version)

    # Phase 5: re-run performances with bias adjustment (if biases computed)
    if biases:
        performances = build_performances(store, as_of_date, pars=pars,
                                          variants=variants, biases=biases,
                                          model_version=model_version)

    # Phase 6: horse states with campaign stage weighting (MODIFIED)
    states = build_horse_states(store, as_of_date, model_version=model_version)

    return {"performances": performances, "horse_states": states}
```

Note: Phase 4 (bias) requires prior horse states to compute expected ratings. On a
cold start (no prior evaluation date), bias is skipped. The walk-forward evaluator
already rebuilds for each date, so prior states are always available after the first
few dates.

The double `build_performances()` call (Phase 3 then Phase 5) is deliberate: the first
pass produces variant-adjusted residuals needed for bias detection; the second pass
applies the detected biases back onto the run ratings. This is one pass more than V1
but the cost is acceptable (the database upserts handle re-runs cleanly via ON CONFLICT).

---

## Model version

Bump `MODEL_VERSION` to `"performance-par-v2.0"` when all three items are implemented.
This ensures V1 and V2 run_performances and horse_rating_states coexist in the database
and can be compared directly.

---

## Walk-forward evaluation protocol

For each enhancement, run the walk-forward evaluator twice: once with V1 and once with
the enhancement active. Compare:

| Metric | Must improve | Diagnostic |
|--------|-------------|------------|
| Brier score | Yes (lower is better) | Primary quality metric |
| Log loss | Yes (lower is better) | Penalises confident wrong answers |
| Rank of winner | Neutral ok | Does the model rank the winner higher? |
| Calibration | Neutral ok | Plot predicted vs actual win rate in 10 bins |

Segment by:
- Track (Randwick vs Flemington vs Rosehill vs Caulfield)
- Going (Good vs Soft/Heavy)
- Field size (<10, 10-14, 15+)
- Campaign stage (first-up, second-up, third-up+) — for Item 2 validation

An enhancement that improves Brier by 0.001 or more is worth keeping. An enhancement
that degrades Brier by any amount is rejected regardless of theoretical appeal.

---

## What is NOT in this spec

These are deferred to later build phases per the project tracker:

- **Class and race strength** — build order item 1 in project_tracker.md
- **Weight / weight-for-age** — build order item 2
- **Full sectional pace-shape and trip** — build order item 3
- **Steward ablation** — build order item 4
- **Projected-race map and pricing** — build order item 5
- **Market comparison** — build order item 6

The three items in this note (daily variant, campaign stage, track bias) are
sub-items within later build phases. They are deferred until the class prior and
Race Strength work is specified, implemented and evaluated. Their empirical
support and proposed math remain useful inputs, not implementation authority.
