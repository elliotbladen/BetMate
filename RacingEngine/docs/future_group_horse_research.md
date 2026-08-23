# Research — identifying future Group horses before class confirmation

## Objective

The ratings engine must recognise demonstrated high ability before a horse has
beaten an already established Group field. This is the central early-value use
case. Natural Fling's four-length Caulfield Group 3 win is the first hard sanity
case, but the model must solve a broad historical cohort rather than be tuned to
one horse.

## Research findings

1. **Age is a trajectory, not merely a category.** A longitudinal Thoroughbred
   study using comparable speed figures estimated peak performance near 4.45
   years and substantial improvement from age two to that peak. A young horse's
   last official rating is therefore not a stable ability estimate. Its US male
   long-career sample cannot be copied directly into Australian fillies and is
   vulnerable to survivor selection. [Gramm and Marksteiner](https://pmc.ncbi.nlm.nih.gov/articles/PMC4013968/).
2. **Early records contain forward information, with high uncertainty.** An
   Australian longitudinal cohort associated early performance, sex, birth
   date, age at first start and racing exposure with later participation and
   performance. High attrition requires explicit censoring; learning only from
   horses that kept racing would bias the model. [Bailey et al.](https://pubmed.ncbi.nlm.nih.gov/10078358/).
3. **The individual race effect matters.** Cross-validated equine research found
   lower bias and error for racing-time prediction when each race, rather than
   only the racetrack, was modelled as an environmental effect. Meeting, going,
   pace and race-specific effects must be removed before persistent horse
   ability is estimated. [Bugislaus et al.](https://www.sciencedirect.com/science/article/pii/S0301622604001599).
4. **Rank is not latent ability.** Competitive/Thurstonian models explicitly
   separate competition level from an underlying horse effect and have produced
   stronger cross-validated rank prediction than simpler threshold models in
   equine data. This supports a latent horse state plus race-context state—not
   pure collateral chaining. [Sole et al.](https://www.sciencedirect.com/science/article/pii/S1751731117001331).
5. **Pace distribution and drafting expose hidden effort.** Data from 44,803
   racehorse performances found distance-dependent pacing strategies and a
   material drafting effect. A run must be decomposed into energy distribution
   and exposure, not judged from placing or raw last-400 alone.
   [Spence et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC3391435/).
6. **Sectionals estimate efficiency, not automatic superiority.** The useful
   signal is deviation from an appropriate course/distance/going par. A fast
   final split after a crawl is not equivalent to sustaining speed after strong
   pressure. [Timeform sectional analysis](https://www.timeform.com/horse-racing/features/rowley/the-timeform-knowledge-sectional-analysis-872015).

## Required rating products

One number cannot represent both today and tomorrow. Store separate point-in-
time outputs:

1. **Achieved run rating:** demonstrated performance after time, meeting
   variant, margin, WFA, sectionals, pace, ground loss and sourced environment.
2. **Current latent ability:** posterior estimate from prior achieved runs, with
   wider uncertainty for lightly raced horses.
3. **Forward development rating:** plausible ability distribution over the next
   30/90/180 days, conditional on exact age, sex, starts, progression, spell
   pattern and distance profile.
4. **Pace-style vector:** preferred pressure, acceleration point, sustained
   speed, late burst and pace-collapse resilience.
5. **Breakout probability:** probability latent ability already exceeds the
   published/pre-race rating by at least 5, 10 and 15 points.

Expected development must never be added retrospectively to the achieved run.
A horse may run 102 today with a projected ceiling of 108; today's figure does
not become 108 merely because improvement is expected.

## Breakout update mechanism

The present 80% collateral weight is unsuitable for a lightly raced dominant
winner. Replace it with an uncertainty-aware update:

- Reduce prior authority when the horse is young, lightly raced, rapidly
  progressing or independently records a high time figure.
- Combine daily-variant-adjusted time, distance-specific 200m energy profile,
  positive but capped winning-margin evidence, WFA and later collateral
  confirmation.
- A large conflict with the old rating widens uncertainty first. Corroborating
  independent signals then permit a rapid upward update.
- Make the rule symmetric so false breakouts can be downgraded.
- Trainer, jockey and pedigree may inform projection but cannot overwrite
  demonstrated track evidence.

## Historical evaluation cohort

Build the cohort without looking at future success:

- Australian two-, three- and four-year-olds with no more than eight prior
  starts.
- Pre-race official/engine rating below the eventual Group threshold.
- Candidate run flagged by at least two independent signals: adjusted time,
  margin dominance, sectional efficiency/ability or high WFA performance.
- Freeze all information at the candidate race date.
- Evaluate at 90, 180 and 365 days: peak achieved rating, Listed/G3/G2/G1
  placing or win, and eligible subsequent starts.

Report precision, recall, calibration, false-discovery rate and median lead
time over later official/class confirmation. Compare with pre-race official
rating, class-only V2 and a naive age/start baseline. Report retired, injured,
exported and missing horses separately to reveal survivorship bias.

## Promotion gates

- Natural Fling's achieved rating must fall in the hard 100-110 band from
  independent evidence.
- The broader frozen cohort must improve future peak-rating MAE and Group-
  achievement calibration over official-rating and class-only baselines.
- Improvement must hold in NSW and Victoria, both sexes, and the two-, three-
  and four-year-old cohorts.
- Preserve 2026/live data as the final untouched test.
- A candidate that only solves Natural Fling fails. A candidate with excessive
  false positives also fails.

## Grey areas

- “Group class” has no universal numerical boundary; race quality and provider
  scales vary.
- Population age curves do not determine an individual horse's maturation.
- Dominant margins can be inflated by collapse, bias or weak opposition and
  require corroboration.
- Later Group success depends on placement and opportunity, so future peak
  performance is a necessary co-target.
- Market comparison belongs later: first detect ability early, then determine
  whether the market already priced it.
