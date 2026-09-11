# Dan O'Sullivan alignment research and blend plan

**Date:** 10 September 2026  
**Scope:** Australian flat-race run ratings, with the current BetMate research chain (`performance-par-v2.0` -> `form-first-v3.0`) compared with Daniel O'Sullivan / The Rating Bureau's published WFA Performance Rating philosophy.

## What the published method says

The public material describes a WFA Performance Rating (WPR) as a run-level measure normalised to weight-for-age so performances can be compared across age, sex, distance and time of year. It uses a custom scale; the published guide says elite world-class performances are generally 108+, while Winx's peak figures were 115.5, 115 and 113.5. The published practical conversion is about two points per length, with the exact conversion varying by conditions and distance. ([Racing.com methodology note](https://www.racing.com/news/2021/09/06/news-review-dan-osullivans-ratings-wrap-6921), [TopRate WFA explanation](https://toprate.helpscoutdocs.com/article/226-wfa-performance-ratings-an-explanation))

The central decision is **race strength first, individual adjustment second**. TopRate says each race is treated as a unique event and assessed with a nonlinear combination of recent and peak ratings, margin spread, overall time, sectional times, market expectations and race incidents. It explicitly says no single input, including a fast time or a large margin, determines race strength. Once the race level is set, each runner is adjusted for beaten margin and carried weight to produce a WFA-normalised figure. ([TopRate WFA explanation](https://toprate.helpscoutdocs.com/article/226-wfa-performance-ratings-an-explanation))

Dan's published explanation also matters for pace treatment. Subjective adjustments for an individual horse's luck, track pattern, pace or bias are not added directly to that horse's WPR. Those factors may affect the assessment of the race's overall strength, while the individual figure remains based on fundamental evidence. The stated reason is reproducibility: adding a separate subjective allowance to every runner makes the rating opaque and inconsistent at scale. ([TopRate WFA explanation](https://toprate.helpscoutdocs.com/article/226-wfa-performance-ratings-an-explanation))

Time and sectionals are used together, not as interchangeable bonuses. TopRate calls this the race's “True Speed Merit”: overall time is checked against standards and conditions, then interpreted with the balance of early and late sectionals. Its sectional guide warns against upgrading a horse merely because it recorded the fastest last 600m; a horse that conserved energy early is entitled to run home faster. Sectionals should explain the performance and its likely suitability to a future setup, while the WPR remains the primary measure of what was achieved. ([TopRate sectional explanation](https://toprate.helpscoutdocs.com/article/257-sectional-time-ratings-an-explanation))

The older Racing.com description is consistent: WPRs use race times, sectional times, margin spread, previous ratings and weights, with a variable point-per-length scale; subjective pace and track-pattern adjustments are excluded from the individual number. ([Racing.com methodology note](https://www.racing.com/news/2021/09/06/news-review-dan-osullivans-ratings-wrap-6921))

The British Horseracing Authority's public handicapping description gives a useful independent cross-check. It adjusts time for distance, carried weight, WFA, rail, wind and the ability of the horses involved; it uses speed figures to identify falsely run races and changes the margin multiplier when steady or overly strong pace distorts the spread. Sectionals are used to decide whether races with different pace patterns are comparable. ([BHA handicapping tools](https://www.britishhorseracing.com/regulation/handicapping-tools/))

Independent research supports keeping pace as a contextual variable rather than a universal winner bonus. Radio-tracked racing data found that pacing strategy and drafting materially affect speed and outcome, with the useful strategy depending on race duration and running style. ([BMC Biology / Royal Society study](https://pmc.ncbi.nlm.nih.gov/articles/PMC3391435/))

## What our current chain does

The current accepted `form-first-v2.0` was deliberately form-first and did **not** use the clock or sectionals to set the race level. The research `performance-par-v2.0` now creates a positive speed run figure from time versus par, daily track variant, weight merit, pace treatment, a thin-field class anchor, last-400 evidence and a winner ceiling. `form-first-v3.0` then computes a collateral/form figure, fits an affine speed-to-form alignment, and blends the two with a base speed weight of 0.50 and tempo-dependent trust. Missing speed is imputed from the form channel.

That is why the model does use time and sectionals, but it is not yet Dan-shaped in the way the inputs are combined:

* **Race strength is still too additive.** A par figure, collateral strength, pace adjustment and sectional component are each calculated as separate increments. Dan's public description says the factors interact nonlinearly and that no one factor determines the race level.
* **The upper scale is being stretched by the alignment layer.** The latest v3 build fitted `speed_aligned = -56.829 + 1.35 * speed_raw`. The slope is at the permitted ceiling. This preserves useful ordering but allows a very fast raw clock to create an elite number before race strength has been fully stabilised.
* **Pace is partly being treated as a runner-level correction.** The current chain can add or subtract a race term and a runner term. Dan's stated method uses pace/track-pattern information to judge the race and to explain a run, while avoiding an automatic individual add-back.
* **The weight treatment is not yet a true WFA layer.** We currently use a small WFA factor or a handicap merit factor around the field median. Dan's public method compares carried weight with an explicit, season- and distance-dependent WFA scale, then normalises every run to that scale.
* **Sectional coverage is uneven.** The new fallback improves coverage, but the model still gives special influence to the last 400m and to broad pace labels. Dan's material describes the full balance of early, middle and late segments and checks them against the entire field and the meeting.
* **Collateral anchors can be stale.** Official marks are useful evidence, but a prior-run rating should be an effective-dated performance state with shrinkage, not a permanent truth. This is especially relevant to the Lindermann/Tempted case.

The observed output confirms the calibration issue. In the three-year v3 leaderboard, Via Sistina's 2024 Cox Plate is 122.2 versus Dan's published 116; Prognosis is 113.8 versus 104; and Without A Fight's 2023 Caulfield Cup is 113.3 versus Dan's published 104.7. Via's 2025 Queen Elizabeth is 108.6 versus Dan's published 107.5, which shows that the model can be close when the race is not pulled into the inflated upper tail. These comparisons are not a complete same-run audit: several published Dan marks for our top ten are from different starts or rounded public commentary. They are calibration evidence, not proof that every individual number is wrong.

## Proposed Dan-aligned model

Keep the model as two explicit outputs during research:

* `dan_aligned_wpr`: the closest reproducible implementation of the published WFA philosophy.
* `betmate_custom_rating`: a later, separately evaluated extension that may use additional trip or predictive information.

Do not overwrite the accepted production model until the point-in-time and rating-quality gates are passed.

### 1. Build a true, effective-dated WFA layer

For every runner, calculate WFA weight for the horse's sex, age, race date, distance and Australian season. Store both `carried_kg` and `wfa_kg`, then use `weight_delta = carried_kg - wfa_kg`. Fit the weight response by distance band and race type with shrinkage toward a broad prior; do not use a single 2.2-point-per-kilogram handicapping conversion. This directly follows TopRate's warning that the WFA gap changes with age, sex, distance and time of year.

Produce both an at-the-weights (ATW) run figure and the WFA-normalised figure. The ATW figure is useful for checking the finish order; the WFA figure is the cross-race comparison number.

### 2. Estimate race strength with a bounded, nonlinear evidence model

Start with a pre-race ability distribution from the last three effective-dated WPRs and comparable-distance peak, with explicit reliability shrinkage. Add independent race evidence:

* winner and field time versus a track/distance/going/rail standard;
* early, middle and late sectional speed relative to the same standard;
* robust margin spread, using a distance- and pace-sensitive margin scale;
* the depth and dispersion of the best pre-race runners;
* market expectation only as a diagnostic or low-weight secondary check, never as a replacement for race evidence;
* clock and sectional quality flags.

Combine these through a robust shrinkage model (Huber or Student-t residuals, with interactions for pace shape and going) rather than summing large fixed bonuses. The race-level estimate should move toward the pre-race field strength when the clock is noisy, and toward objective time/sectionals when the field has little proven form. Cap the contribution of any one channel and record the channel weights and uncertainty.

This is the key change for Lindermann versus Tempted: the race level should recognise the better sustained speed in Tempted's race, while Lindermann's slow-then-sprint shape should be recorded as a tactical context and uncertainty signal, not converted into a large elite WFA number by collateral alone.

### 3. Use sectionals as evidence about race efficiency, not automatic merit

Store a vector of standardised segment performances (early, middle, final 800/600/400/200 where available), plus field-relative values and a race-level pace profile. Use those values to:

* decide whether the overall clock is representative;
* change the reliability of margin conversion;
* identify sustained pressure versus sprint-home patterns;
* explain a horse's performance and future suitability.

Do not add a generic “fast late” bonus. A late sectional can be strong because the horse conserved energy, because leaders collapsed, or because the entire field produced the same split. If a runner-level trip adjustment is retained for the custom model, keep it in a separate `trip_context` field and exclude it from `dan_aligned_wpr`.

### 4. Apply a variable margin model after race strength

Estimate beaten-margin points per length from distance, pace profile, going and finish dispersion. A steady-run, bunched race needs a larger multiplier; a strongly-run, strung-out race needs a smaller multiplier. Use a robust cap and a winner/second check so one timing or finishing anomaly cannot create a 10-point tail jump. This follows the BHA description and Dan's statement that the point-per-length scale varies by distance and conditions.

### 5. Replace the global affine upper-tail stretch

Use a monotonic calibration from the raw race-level model to the Dan scale, fitted only on pre-cutoff benchmark observations. The calibration should be piecewise or isotonic with a deliberately flatter elite tail, rather than allowing `b=1.35` to become the default. The first calibration anchors should include published Dan runs with clean identities:

| Benchmark | Published Dan evidence | Use |
|---|---:|---|
| Via Sistina, 2024 Cox Plate | 116 | elite anchor |
| Via Sistina, 2025 Queen Elizabeth | 107.5 | follow-up regression anchor |
| Prognosis, 2024 Cox Plate | 104 | placed elite anchor |
| Without A Fight, 2023 Caulfield Cup | 104.7 (published review) | major handicap anchor |
| Joliestar, 2025 Newmarket | 105 | sprint elite anchor |
| Pericles, 2026 Caulfield | 101.6 | high-quality Group anchor |
| Giga Kick, 2025 Champions | 102; published peak range 105.5–106.7 | sprint peak range |

Keep benchmark values with race date, race identity, article URL, and whether the comparison is exact-run, same-horse different-run, or rounded commentary. Do not fit to a horse's best public description when it is not the same run.

### 6. Separate run rating, current ability and context

`dan_aligned_wpr` should answer “how good was this run?” The ability table should be a recency/reliability estimate of the horse's current level. Sectional suitability, track pattern, map, expected pace and luck should remain context columns. This keeps the rating auditable and prevents a plausible future-trip upgrade from being mistaken for achieved merit.

## Validation and rollout

1. **Data audit:** freeze race identity, clock status, sectionals, WFA table version and effective date. Recheck the Via Sistina 2025 QE identity and all benchmark race IDs.
2. **Historical backfill:** build `dan-aligned-v0.1` through the same 6 September 2026 cutoff. Preserve the accepted v2 and current v3 snapshots.
3. **Calibration report:** compare exact-run benchmarks first, then same-horse/different-run examples. Report median error, 90th-percentile error, elite-tail error and rank concordance separately.
4. **Walk-forward rating-quality test:** evaluate prior-form concordance, run-to-run repeatability, margin calibration, scale stability and missing-clock robustness. Do not use strike rate, ROI or prices as a rating promotion criterion.
5. **Ablation tests:** remove time, remove sectionals, remove collateral, remove WFA, and remove pace context. The chosen model should show which evidence improves scale and repeatability rather than merely increasing the top end.
6. **Case review:** Lindermann/Tempted, Via Sistina Cox Plate/QE, Sir Delius QE, Autumn Glow's peak runs, and the Caulfield Cup 2023 field. Require the written component ledger for every material disagreement.
7. **Promotion:** only after the point-in-time gate passes, keep `dan_aligned_wpr` as the transparent base and introduce `betmate_custom_rating` as a separately versioned shadow. The custom layer can later test predictive trip/context adjustments without contaminating the Dan-aligned achieved-run scale.

## What this means for the immediate question

Our use of time and sectionals is real, but their placement in the architecture is the problem. We currently allow the clock to create a high raw figure, align it with a slope that is currently at its maximum, and then combine it with collateral and pace terms. Dan's public method uses those same evidence families to determine a unique race strength, normalises to WFA, applies variable margin and weight adjustments, and keeps subjective pace/trip allowances out of the individual achieved rating. The proposed work therefore preserves the useful data already collected while changing the order, calibration and separation of the evidence.

The first implementation should be the WFA table, race-strength estimator and elite-tail calibration. It should not be a wholesale deletion of the speed channel: the goal is to make time and sectionals decisive when they are reliable, restrained when they are not, and comparable to Dan's scale across the full population.

## First implementation completed

The first shadow layer is now implemented as `dan-aligned-wfa-v0.1` in
`racing_engine/dan_aligned.py`. It preserves `form-first-v3.0`, removes the
stored runner-level pace term from the achieved run, applies the official
effective-dated WFA schedule where a point-in-time profile is available, and
uses the explicit elite-tail calibration above. The build produced 29,498
shadow runs, with WFA data on 11,510 (39.0%) and runner pace terms removed from
10,093 runs. It is stored in `dan_aligned_run_performances` and remains
research-only. The current three-year top ten is Via Sistina 115.1, Gold Trip
110.1, Prognosis 109.5, Sir Delius 108.8, Joliestar 108.8, Without A Fight
108.7, Pericles 108.6, Giga Kick 108.5, Militarize 108.3 and Autumn Glow
108.3. The next implementation pass is the nonlinear race-strength estimator
and expanded WFA profile coverage; these numbers are not a promotion decision.

## Sources

* [TopRate: WFA Performance Ratings & Analysis](https://toprate.helpscoutdocs.com/article/226-wfa-performance-ratings-an-explanation)
* [TopRate: Sectional Time Ratings & Analysis](https://toprate.helpscoutdocs.com/article/257-sectional-time-ratings-an-explanation)
* [Racing.com: Dan O'Sullivan's Ratings Wrap (methodology note)](https://www.racing.com/news/2021/09/06/news-review-dan-osullivans-ratings-wrap-6921)
* [Racing.com: Dan O'Sullivan's Ratings Wrap, 28 October 2024](https://www.racing.com/news/2024/10/28/news-review-dan-osullivans-ratings-wrap-281024)
* [Racing.com: Dan O'Sullivan's Ratings Review, 6 August 2025](https://www.racing.com/news/2025/08/06/news-review-dan-osullivan-best-of-2024-25)
* [British Horseracing Authority: Handicapping tools](https://www.britishhorseracing.com/regulation/handicapping-tools/)
* [Speed, pacing strategy and aerodynamic drafting in Thoroughbred horse racing](https://pmc.ncbi.nlm.nih.gov/articles/PMC3391435/)
