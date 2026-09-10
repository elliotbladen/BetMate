# Step 1 review: raw-time race strength

Status: implemented research candidate, awaiting owner review. This change
adds `race-strength-raw-v0.1-shadow`; it does not replace an accepted rating.
Steps 2 (WFA coverage/normalisation) and 3 (rating-quality validation) remain
separate work. There are no application, pricing or production data changes.

## Problem and resulting behaviour

The checked-in v3 calculation only permits speed to lift the collateral figure,
and fits its speed alignment across all available runs. A high collateral
figure can therefore survive a weak clock; later data can also change the
historical alignment. The pending two-way blend in the shared workspace is
unfinished and has not been copied into this branch.

The new completed-race estimator builds one level from raw official time,
earlier comparable form and a weak class prior. Time can move that level down
or up. A weighted Huber estimator limits the influence of a disagreeing channel.
The stored ledger shows each input, its initial reliability, its effective
weight and the disagreement in points. Disagreement is a diagnostic, not a
calibrated uncertainty interval.

Individual at-the-weights figures then equal that race level minus beaten
margin times the race's points-per-length factor. The winner's beaten margin
is always zero, including feeds that put the winning margin in that field.
Missing loser margins are excluded, not treated as zero. These are achieved
run figures, not WFA-normalised ratings or current horse ability estimates.

## Exact first-version choices

- Raw clocks are taken from the identity-resolved clean race table. Both its
  clock-status gate and the existing distance-specific physical gate must pass.
  No wind, daily track variant, rail correction or synthetic clock is applied.
- Clock comparisons use only **earlier dates**, exact track/distance and the
  same going bucket, over the preceding 730 days. At least five are required.
  Unknown going contributes no par observations. Current-day races never
  update another race's pars or form history.
- To express seconds in existing points, each prior race contributes
  `prior_class_standard + (prior_time - current_time) / 0.17 * distance_ppl`.
  The clock channel is the median of those values, capped at 20 points either
  side of the prior races' median class standard. There is no fitted affine
  alignment. **This class-based clock calibration is provisional**, not an
  independent learned scale. Class evidence and clock calibration are partly
  related; channel weights are not probability estimates.
- Form uses the median of up to three earlier candidate runs within 365 days,
  within 20% of today's distance (minimum allowance 200m). More observations
  and more recent form carry more weight. Principals finishing in the top four
  anchor the completed race; their margin credit is capped at six lengths.
  Those anchors are themselves combined with Huber weights, so stale or
  thinly supported form cannot outvote reliable recent evidence.
  Wide disagreement between those anchors reduces form reliability. Class-only
  holding figures never become supposedly proven form on the next start.
- Sectional parsing reuses the source-aware parser: NSW supplies 200m intervals,
  Victoria supplies different blocks. The opening-versus-final-400 contrast
  is measured relative to earlier comparable races. This accounts for the
  standing start in the comparison instead of calling every faster finish a
  tactical race. This version uses the final-400 contrast, not a full segment
  vector or individual trip allowances.
- A slower-than-usual opening reduces clock reliability. The margin multiplier
  varies smoothly by up to 15%: larger for a slow/bunched pattern and smaller
  for a strong/spread pattern. There is **no fast-late bonus**. Both choices are
  explicit research assumptions to test in step 3.
- Huber residuals are bounded at six points. Clock and form reliability are each
  at most 0.85; the class prior has weight 0.15. All constants are fixed in the
  versioned implementation, not fitted to the example horses.

A missing clock stays missing. If neither measured time nor earlier form is
usable, the output is explicitly `class_only`. That is a holding estimate,
not evidence of performance quality.

## Historical review

Built locally through the exclusive cutoff **2026-09-06** from a read-only
connection to the corrected local database. Outputs live in a new disposable
SQLite file, not the source database. The committed JSON report contains the
input digest, state coverage and full component ledgers for the examples.

| Coverage | NSW | VIC | Total |
|---|---:|---:|---:|
| Rated races | 1,391 | 1,359 | 2,750 |
| Usable clock channel | 1,022 | 872 | 1,894 |
| Earlier form channel | 1,244 | 1,202 | 2,446 |
| Sectional context | 1,006 | 871 | 1,877 |
| Class-only holding estimates | 94 | 98 | 192 |
| Clock channel capped | 190 | 138 | 328 |

29,478 runs were rated; 27 clean-layer races were ineligible. This is coverage
of the existing clean dataset, not completeness against an external calendar.

| Run | Candidate at-the-weights figure |
|---|---:|
| Tempted, Randwick 5 Sep 2026 | 107.1 |
| Lindermann, Randwick 5 Sep 2026 | 92.3 |
| Ceolwulf, Randwick 5 Sep 2026 | 88.1 |
| Via Sistina, Cox Plate 26 Oct 2024 | 108.2 |
| Prognosis, same Cox Plate | 95.4 |

Tempted's raw-clock channel is 108.0 and her form channel 103.2. Lindermann's
are 88.2 and 95.6. Their class prior is the same (110); it cannot by itself
hold both races at Group 2 merit. These examples show the mechanism, not proof
that their absolute ratings are correct. They must not be equated with the
older WFA shadow or a published Dan rating.

## Material limitations for approval

**This is ready to review as an implementation, not to promote as a validated
horse rating.** The clock cap is reached in 328 races (11.9%). Via Sistina's
Cox Plate clock channel is capped at 108, showing that the provisional scale
can suppress a genuinely exceptional run. The highest candidate run is
Boldinho at Caulfield, 16 Dec 2023 (119.2); the scale requires investigation.
These findings are recorded rather than tuning coefficients to the examples.

The source is today's corrected historical dataset. Event chronology is
protected, but no claim is made to recreate historical source revisions or
when each imported fact was first available. The complete same-row baseline,
repeatability, margin-calibration, scale and ablation studies are step 3.

Raw times retain day-specific surface and environmental effects. Going buckets
are coarse. Prior candidate at-the-weights figures also retain carried-weight
and age/sex differences until the WFA work in step 2. The candidate only reads
its own chronological history, not existing v3, franking or weather tables.

## Verification and reproduction

13 new tests cover bidirectional clock effects, bounded outlier influence,
sectional semantics and missing splits, no clock imputation, future-data and
same-day isolation, exclusive cutoffs, impossible/quarantined clocks, distinct
track/going pars, winner/missing-margin handling, read-only inputs and output
freeze protection, and stale-anchor downweighting. The 17 existing tests for pre-race strength, sectionals,
Dan calibration and accepted v2 also passed: **30 tests total**.

A second historical build stopping before 2025-01-01 reproduced all 1,264 earlier race ledgers and 13,596 run figures exactly. Appending the later history did not revise them. This checks event chronology, not source-ingestion vintages.

From `RacingEngine/`:

```sh
python3 -m unittest discover -s tests -p 'test_*race_strength.py'
python3 -m unittest discover -s tests -p test_sectional_features.py
python3 -m unittest discover -s tests -p test_dan_aligned.py
python3 -m unittest discover -s tests -p test_v2_ratings.py
python3 -m racing_engine.raw_race_strength \
  --database /path/to/source.sqlite \
  --output /path/to/new-review.sqlite \
  --as-of 2026-09-06
```

The CLI requires explicit paths, opens the source read-only and refuses an
existing output path. Accepted ratings, the existing pre-race strength module,
frozen snapshots and application consumers are unchanged. No UI check applies.
