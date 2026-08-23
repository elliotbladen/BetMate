# RacingEngine: what we have built, what the rating means, and the path to a professional model

## Executive summary

BetMate now has the beginnings of a serious internal Australian racing research engine. It is not yet a finished pricing model and it should not be marketed as one. Its job so far has been to solve the unglamorous but essential problem that sits underneath every good rating: collect a durable, auditable record of what actually happened in races, then turn that record into a conservative first estimate of horse ability.

The first scope is deliberately narrow: Saturday metropolitan thoroughbred meetings in Victoria and Sydney/NSW. As audited on 20 August 2026, official results cover almost three full seasons, from 12 August 2023 through 15 August 2026:

| Area | Meetings | Races | Historical source |
| --- | ---: | ---: | --- |
| Melbourne / Victorian metro | 120 | 1,146 | Racing.com public form payload, used with Racing Victoria's non-commercial research approval |
| Sydney / NSW metro | 139 | 1,325 | RNSW official sectional PDFs where available; Racing.com public result fallback for explicitly labelled archive gaps |
| Combined | 259 | 2,471 | Source-preserved local research database |

There are 112,193 stored sectional/in-run records in total: 36,759 Victorian records and 75,434 NSW official-PDF records. NSW fallback meetings contain result data only. They are not dressed up as sectional data. The latest stored `performance-par-v1.0` rebuild (`as_of_date=2026-08-16`) contains 18,140 individual run-performance assessments and 10,752 current horse-state records, including the usable 15 August results.

That is a useful foundation because it is repeatable. Every rating can be traced to a race, raw source payload/report, par, time component and confidence rule. The model is deliberately modest. Its present result is an *evidence-backed baseline rating*, not a claim that we have already built a better figure than Punting Form, Dan O'Sullivan or Timeform.

The important next step is not “add a hundred variables”. It is to add the high-value variables in the right order: class and race strength first, then weight/weight-for-age, daily track and rail variants, pace/trip and distance travelled, and finally a race-specific map and fitness layer. The database is now large enough to begin that work honestly.

## 1. What was actually built

### 1.1 A data spine rather than a spreadsheet

The system has a local SQLite database with separate tables for cards, official results, runner results, runner sectionals, track pars, individual run performances, horse rating states and later fair-price snapshots. Keeping these apart matters. A declared field changes with scratchings; a result should be immutable; a sectional is a measurement at a particular point in a particular run; and a rating is a model interpretation of those facts.

Each raw source file is retained locally. Victorian data is archived as Racing.com JSON and NSW official data as the original RNSW sectional PDF. Missing RNSW PDFs use the separately labelled `racing-com-nsw-results-fallback` source: results only, never invented sectionals.

### 1.2 The historic inputs currently held

For every imported race we aim to retain:

- race date, state, venue, race number and race description/class text;
- advertised distance, official race time, track condition and rail position;
- runner number, horse, finishing position, beaten margin where supplied, finish time where supplied, and non-runner status;
- sectional durations and in-run positions where the source provides them; and
- source URL/payload/report and ingestion time.

Victorian records currently provide the 800m, 400m and finish split structure supplied by Racing.com, alongside 800m/400m position fields when available. NSW reports can be richer: the raw report contains cumulative times through multiple 200m markers, sectional positions, final time and, in many reports, distance-travelled information. The importer reconstructs the reported splits from those cumulative clocks. It also supports the older wide PDF report and the newer TripleSData-style report visible on the Racing NSW screenshot.

We should be precise about the gap. The NSW parser places an explicitly reported distance-travelled-versus-winner (DT-W) value into a clean database column where it is available; 552 runner rows currently have one. Missing values remain null, and no current rating adjustment uses ground lost. That is future opportunity, not present model strength.

### 1.3 No-look-ahead discipline

The model is built “as of” an explicit date. If we make a rating for 15 August 2026, only races before that date can enter its pars and horse states. The walk-forward evaluation rebuilds the model before each historic race date and then scores that day's runners. That avoids the classic back-test mistake of allowing a horse's future improvement to improve its past rating.

The walk-forward framework reports Brier score and log loss: probability-quality diagnostics, not profit claims. Later we compare it with Betfair market probabilities, calibration buckets and closing-line performance.

## 2. How the current V1 rating is calculated

### 2.1 The central idea: rate a run, then rate the horse

The model has two layers.

1. A **performance rating** says how good one run appears relative to a local time standard.
2. A **horse state rating** says what the evidence from all prior runs suggests about the horse today, while giving more weight to recent and reliable evidence.

The scale is centred on 100. It is an internal scale, not a kilogram, benchmark or official handicap scale. A horse above 100 has performed above the neutral reference on the evidence currently used; below 100 is below it. It should not be compared numerically to a Timeform, Racing and Sports or Dan O'Sullivan figure.

### 2.2 Track/distance/going pars

The first calculation is a local par. Races are grouped by:

- track (`randwick`, `rosehill`, `flemington`, and so on);
- advertised distance, rounded to the nearest 10 metres for unusual distances; and
- going bucket: heavy, soft, good, firm, synthetic or unknown.

For each group, the model takes the **median** official race time, provided there are at least five prior races. Median is intentional. A mean can be distorted by one timing error, a suicidal tempo, an extreme weather event or a genuine track-bias day. The median is a safer first estimate when the data history is still relatively short.

Example: suppose prior Soft 5 1,200m Randwick races give a median par of 72.00 seconds. A horse that runs 71.66 seconds has run 0.34 seconds faster than that simple local par. V1 converts time to its internal length-like unit using 0.17 seconds per length:

`time component = (par time − runner finish time) / 0.17`

In this example the time component is +2.0. A slow 72.34 run would be -2.0. The 0.17 conversion is a transparent working assumption, not a universal truth. Where runner time is absent, V1 uses winner-time differential and beaten lengths once, never double counting them.

### 2.3 The limited sectional signal

Where enough runners have a terminal sectional, V1 compares a runner's late split with the **median late split of that race**. Faster than the median earns a small credit; slower loses a small amount. The formula is:

`sectional component = clamp(((race median late split − runner late split) / 0.17) × 0.20, -2, +2)`

The clamp means this signal can never move a run by more than two points. That conservatism is correct at this stage: an eye-catching late sectional can simply be the result of a slow early pace, clear running, a fast lane or a horse being eased late. A raw closing split is not automatically hidden merit.

There is one implementation item to fix before this feature is promoted. In Victoria, marker `0` represents the 400m-to-finish split. In many NSW PDFs, marker `0` is the final 200m split, because the report contains every 200m marker. V1 currently labels both as “last 400” and compares the terminal segment. We must normalise NSW to a genuine last-400 measurement from the cumulative 400m and finish clocks, or maintain separate, explicitly named final-200 and last-400 features. Until that correction is made, the late-split contribution must stay small and be treated as provisional.

### 2.4 Performance formula and confidence

The current per-run formula is therefore:

`run rating = 100 + time component + margin component + capped late-sectional component`

The model also records confidence. Confidence rises with the number of races supporting the par and gets a modest uplift if usable sectional evidence exists. It is capped at 0.80. In other words, even a well-covered V1 run is not treated as certainty because class, weight, track variant, rail, pace and trip are still missing.

### 2.5 Converting runs into a current horse state

Not every run should count equally. A horse's performance evidence decays with a 180-day half-life. A run 180 days ago receives roughly half the recency weight of a run today, before its run-confidence factor is applied.

The weighted mean is then shrunk toward neutral (100) for lightly raced horses. The reliability rule is:

`reliability = 1 − exp(-number of rated runs / 4)`

and the horse state is:

`horse state = 100 + reliability × (weighted mean run rating − 100)`

This does something useful. A horse with one enormous run is not immediately treated like a proven Group horse. A horse with four consistent above-par runs is allowed to carry more of that evidence. The output also stores peak rating, consistency (the standard deviation of its run ratings), rated-run count and uncertainty. These are as important as the headline number. A 104 rated from seven stable runs is not the same betting proposition as a 104 created by one spike.

## 3. What statistics currently enter the rating

The table below separates facts we have from facts V1 currently uses.

| Statistic/data item | Held in database | Used in V1 rating | Why it matters |
| --- | --- | --- | --- |
| Track | Yes | Yes | Each venue has different geometry and surfaces. |
| Distance | Yes | Yes | Time must be compared at comparable trips. |
| Track condition | Yes | Yes, broad bucket | Good/Soft/Heavy are materially different environments. |
| Official race time | Yes | Yes | Foundation for track/distance/going par. |
| Individual finish time | Often | Yes, when supplied | Better runner-specific evidence than result position alone. |
| Finish position | Yes | Indirectly / validation | Determines result and assists data quality checks. |
| Beaten lengths | Often | Only if runner time missing | Fallback evidence, never double-counted with finish time. |
| Terminal sectional | Often | Yes, tightly capped | Small closing-efficiency clue. |
| Other sectional splits | Often | Not yet | Needed for pace-shape and efficiency. |
| In-run position | Often | Not yet | Needed to judge map, pressure and race shape. |
| Rail position | Yes | Not yet | Required for track-pattern and ground-loss context. |
| Race class text | Yes | Not yet | The largest missing variable. |
| Weight carried / WFA | Not consistently ingested | No | Needed for comparable merit figures. |
| Barrier | Available on cards/raw reports | No | Input to map and ground-loss expectation. |
| Jockey/trainer | Available on cards/raw reports | No | Secondary explanatory features, not a base-rating substitute. |
| Distance travelled | Present in many NSW PDFs | No | Required to quantify ground lost/won. |
| Market odds | Separate layer | No | Useful benchmark, never a substitute for model evidence. |

## 4. Comparison with established rating approaches

### 4.1 Timeform: a mature merit-and-weight framework

Timeform is the useful international comparison because it separates a horse's assessed merit from a calculated time figure. Its published material says its ratings are adjusted for weight, age/weight-for-age and the race conditions; its computer time figures also account for track differences, distance, surface condition and wind. It explicitly warns that the raw time alone says little without standardisation. [Timeform's explanation of ratings](https://www.timeform.com/horse-racing/features/timeform-ratings/how_the_ratings_for_a_race_are_calculated) and [computer time figures](https://www.timeform.com/horse-racing/features/timefigures/timeform_computer_timefigures_explained) are good reference points.

Our V1 shares pars, separate performance/horse-state layers and uncertainty. It does **not** yet share Timeform's mature weight, age, daily-variant, class/form-handicapping and analyst layer. Calling ours better today would be wrong.

### 4.2 Dan O'Sullivan: merit, class and context

Dan O'Sullivan's public ratings examples show the central point we need to absorb: a winner is not automatically the best performance once weight is normalised to weight-for-age. Racing.com noted one example where a 51kg winner's normalised rating was below several rivals. That is the right mental model for our next phase. The model must rate the *merit of the run*, not reward the finishing order blindly.

Our advantage is not present sophistication but testability: run a class/weight feature in shadow mode and keep it only if walk-forward calibration improves. The analyst should always see whether a number came from a fast par, race strength or map benefit.

### 4.3 Punting Form: map as an immediate race-specific edge

Punting Form's published speed-map description is an excellent benchmark for the user experience. It dynamically identifies advantage/disadvantage from historical run style, barrier, rail and venue, and presents the impact quickly. [Its documentation](https://docs.puntingform.com.au/docs/speed-map) gives the basic idea.

Our current rating is **not** a speed map. It is a prior ability estimate. The future system should be stronger when it combines a clean base ability rating with a probabilistic race simulation: expected early positions, pace pressure, lane/rail pattern, barrier, jockey decision and each horse's historical ability to sustain or finish from that shape. The key distinction is that we should not create one static map picture. We should simulate many plausible maps, quantify each runner's benefit across them, show uncertainty, and allow an expert to challenge the assumptions.

### 4.4 What can genuinely make ours better

“Better” cannot mean more colours or more variables. It means better out-of-sample calibrated probabilities after costs. Our potential advantages are:

1. **Auditability.** Every adjustment is stored and testable rather than hidden.
2. **Local specificity.** We can learn local tracks rather than impose an overseas conversion.
3. **Separation.** Base ability is distinct from today's barrier/map setup.
4. **Uncertainty.** Lightly raced horses and fragile assumptions widen a price rather than create fake precision.

None of these is an edge until back-tested. They are the design conditions for finding one.

## 5. What must go into the next rating algorithm

The correct architecture has four separate layers. Do not mash all inputs into one opaque number.

### Layer A: base performance merit

This answers: “How well did this horse run, independent of where it finished?” Start with the current par model, then add:

- **daily track variant:** estimate whether the entire meeting was fast or slow versus expected, separately by surface/distance where evidence supports it;
- **rail and lane pattern:** model rail setting, track configuration and observed leader/on-pace/back-marker lane effect, with shrinkage when a day has too few races;
- **weight and weight-for-age:** translate the carried weight and age allowance to a consistent merit scale; do not hard-code a universal kilograms-to-length factor without validation by distance and going;
- **race class and race strength:** use official category/benchmark/prize conditions, then improve it through the prior ratings of the actual opposition;
- **distance travelled:** turn extra ground into a time/energy correction, especially around turns;
- **pace/trip:** identify genuine fast/slow early pace, pressure received, cover, being held up, wide runs and whether a late sectional was earned or gifted; and
- **sectional profile:** use early, middle and late relative-to-par figures, not only the last split.

Class is first because it stops the model from treating a fast low-grade sprint as equivalent to a similarly timed higher-quality performance. The practical method is a two-way loop: start with an official class prior, rate each runner against a track-adjusted par, then use the prior and subsequent ratings of its opponents to estimate race strength. Apply shrinkage so one unusually strong winner does not instantly re-rate an entire maiden.

### Layer B: current horse condition

This answers: “What is the horse likely capable of now?” It should include a recency-weighted latent ability state, peak, average, volatility, time since run, preparation stage, spell, first-up/second-up profile, stable change and a distance/going suitability profile. Use hierarchical shrinkage: a horse with two wet-track starts should not be declared a wet tracker with certainty.

This should become a probability distribution, not a single point estimate: a fresh two-year-old has a wider ability range than a seasoned horse.

### Layer C: today’s race setup

This answers: “How does this horse's ability translate into this exact race?” Inputs should be barrier, declared weight, jockey, field size, map, expected tempo, rail, track condition forecast, distance, class, expected lane pattern and likely scratchings. It is the correct home for the speed map.

Build the map from historical run-style distributions, not a single label. For each runner estimate probabilities of leading, on pace, midfield and back; estimate pace pressure from the combined field; run many scenarios; then calculate the average and downside effect on each horse. A horse that needs a lead but draws wide among four natural leaders should have both a lower mean and higher uncertainty. The user-facing map can still be simple, but the engine underneath should be probabilistic.

### Layer D: price, not rating

The final layer turns projected performance distributions into win/place probabilities by simulation or a calibrated multinomial model. It then makes a fair book and compares it with bookmaker/Betfair prices. The model rating and the betting decision must remain separate. A good 105 horse rating does not itself mean “back the horse”; price, uncertainty, market liquidity and portfolio exposure decide that.

## 6. Delivery order and tests

The practical order is:

1. Correct NSW sectional normalisation and ingest structured weight, barrier, jockey, trainer and DT-W fields.
2. Build race-class taxonomy and race-strength adjustment. This is the first V2 model.
3. Build daily track/rail variants with conservative shrinkage.
4. Add full sectional pace-shape and trip adjustment.
5. Build probabilistic map scenarios and race-specific price adjustment.
6. Add fitness, stable/trainer and qualitative intelligence as low-weight, auditable overlays.
7. Only then explore ML as a challenger model. A gradient-boosted model or PyTorch sequence model can learn interactions, but it must compete against the transparent model in blind walk-forward tests.

Every stage needs three tests: (a) a data-quality test, such as split durations reconciling to the finish time; (b) a no-look-ahead walk-forward test; and (c) a market comparison using only information available at the time. Measure calibration, Brier score, log loss, rank of winner, expected value at recorded market prices, closing-line value and drawdown. Segment the results by track, distance, class, wet/dry, field size and price band. A model that works only at Flemington on good ground is not a universal model; it may still be a useful specialist.

## Conclusion

We have a three-season, source-audited history and a transparent baseline. The current number is mainly a track/distance/going time-par rating with a small late-sectional clue, recency weighting and uncertainty; it is not yet a class, weight, pace, trip, track-bias or map rating. Add those layers one at a time and demand walk-forward improvement before calling any of them an edge.
