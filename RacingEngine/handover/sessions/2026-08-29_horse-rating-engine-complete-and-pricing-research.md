# Handover — Horse Rating Engine complete; pricing research boundary

Date: 29 August 2026  
Data/market window tested: 23 August 2025 to 31 July 2026  
Jurisdictions: NSW and Victoria  

## Decision

The Horse Rating Engine is complete at the accepted run-rating and sustainable
ability research boundary. Preserve those ratings as descriptive measures of
what a horse achieved and what it can sustainably produce.

Do not describe the rating-to-price conversion tested in this session as a
completed or profitable betting model. Ratings remain an input to the future
race-day probability engine, not fair prices on their own.

## Betfair test definition

The exploratory tests used official Betfair ANZ historical files and:

- `BEST_AVAIL_BACK_AT_SCHEDULED_OFF` as the closing price;
- a 110% model book;
- probability temperature 60;
- flat $1 win stakes;
- 10% NSW and 7% Victorian commission on positive race-market profit;
- complete runner matching only; and
- strictly point-in-time ratings.

The original Sydney/Melbourne Group 1 test showed that the frozen rating-price
conversion was too compressed. It priced genuine outsiders too close to the
centre of the field and consequently generated many false high-EV longshots.
Raising EV thresholds did not repair calibration; it increasingly selected
large-priced runners and made returns depend on a handful of winners.

## Exploratory results discussed

- Non-Group set-weight/WFA, including Listed, EV >50%: +24.13% net ROI on
  404 bets. Excluding Listed: -8.50%.
- The same population with prices below $50: -10.58% on 197 bets.
- Smoothed Ability, EV >100%, no price cap: +26.35% on 346 bets, driven by
  Listed longshots; ordinary non-Group races returned -30.99%.
- Smoothed Ability, EV >400%, below $50: 10 bets, zero winners.
- Latest-run rating with missing runners assigned the mean of known ratings in
  that race, EV >100%, below $50: +15.43% on 142 bets. Listed was -7.88%; the
  47 ordinary non-Group bets returned +62.55%, an exploratory small segment.
- BM70–BM100 latest-run/mean-fallback model, EV >100%, below $50: -9.56% net
  ROI on 805 bets across 347 matched races.
- The same benchmark population, EV >400%, below $50: 37 bets, zero winners.
- The same benchmark population, EV >400%, price $50 or above: +0.94% net ROI
  on 690 bets. BM78 alone supplied the profit.
- The same benchmark population, EV >1000%, price $50 or above: +14.43% net
  ROI on 302 bets; only two winners, both BM78. The race-bootstrap 95% interval
  was -100% to +213.81%.

These are repeated retrospective cuts of one sample. They are diagnostic, not
independent validations, and must not be used to select a live strategy.

## Liquidity finding

For the 175 selections in the non-Group 400%-EV longshot test, runner-level
pre-play matched volume averaged $1,159 and had a $947 median. The historical
summary files do not contain available size at the quoted closing price, so
they cannot prove executable fills. Of $50, $100 and $200, only $50 was even a
plausible initial cap, and $25 was the more defensible base assumption. Exact
fill/slippage testing requires Betfair advanced price-ladder history.

## Agreed future model architecture

Keep three concepts separate:

1. Sustainable Ability — the repeatable underlying level or ceiling.
2. Interpreted recent form — what the latest runs imply after conservative,
   evidence-based treatment of pace, interference, bias and suitability.
3. Race-day readiness — how much ability is likely to be available today given
   campaign stage, target proximity, fitness, distance progression and normal
   preparation pattern.

For Australian benchmark handicaps, register 50% as the first combined
rating/form candidate: 35% Sustainable Ability and 15% latest-run form. The
remaining 50% belongs to weight/race conditions, distance, going, pace/map,
barrier, campaign state, jockey/trainer context and uncertainty. Official
benchmark rating and carried weight are structurally related and must not be
double-counted.

For spring/autumn black-type racing, campaign readiness and target trajectory
may warrant roughly 20% of the fundamental model. It is not part of Sustainable
Ability. A horse can retain 120 Ability while being expected to run below that
first-up or in a lead-up short of its target distance.

## Evidence rules for campaign intent

Never infer an excuse or target retrospectively from the result. Store only
point-in-time evidence such as declared targets, nominations, distance and
spacing progression, trials/jump-outs, trainer preparation history, jockey
bookings, gear changes, sectionals relative to pace, and official steward
interference reports. Preserve achieved rating, interpreted merit and expected
race-day rating as separate values with uncertainty.

## Next boundary

The next build is a race-day probability engine, not another Horse Rating
Engine revision. Pre-register candidate weights and chronological evaluation
windows. Evaluate log loss, Brier score, calibration and ranking before ROI;
then test prices once on untouched data. Do not continue mining EV thresholds
on the completed 2025–26 sample.

## Live race spot checks completed later in the session

The completed rating layer was used descriptively on two 29 August 2026 races.
These were inspection exercises, not live prices or betting recommendations.

### San Domenico Stakes, Rosehill R8

The published eight-runner field was matched to the local achieved-run history.
Revengeance had the highest current sustainable Ability at 101.26. Warwoven
had the highest accepted historical run at 103.32. Blue Door's current Ability
was 90.71 and her best accepted run was 90.05, but only two accepted runs were
available. Berzelius and Wild Atlantic had no accepted history.

This exposed the national-coverage limitation clearly: a low or missing figure
for a lightly raced horse must not be interpreted as proof that the horse lacks
ability. The current clean history is principally metropolitan NSW/Victoria and
can omit provincial and interstate evidence.

### Memsie Stakes, Caulfield R8

For the confirmed 12-runner field, the principal figures were:

- Jimmysstar: Ability 109.59; peak accepted run 117.24.
- Mr Brightside: Ability 109.36; peak 120.14, the highest peak in the field.
- Beiwacht: Ability 108.71; latest and peak accepted run 114.11.
- Buckaroo: Ability 108.26; peak 116.82.
- Treasurethe Moment: Ability 108.18; peak 118.74.

Beiwacht's 114.11 was verified as his winning performance in the Group 1 All
Aged Stakes at Randwick on 18 April 2026: 1400m on a good track, 56.5kg,
barrier 2, Nash Rawiller, winning in 1:20.76 after leading throughout. It is a
genuine relevant Group 1 performance against older horses, not a projection.
The remaining question for the Memsie is readiness to reproduce that peak
first-up, which belongs in the future race-day readiness layer.

## EPL 1X2 matrix spot check

The current 2026/27 round-two EPL tipping card was compared with same-day best
1X2 comparison prices. The highest mathematical edge was Aston Villa to beat
Arsenal:

- matrix-adjusted probability 28.0852%;
- fair price $3.56;
- comparison price $6.50; and
- nominal EV +82.55%.

The matrix moved Villa only slightly from the base probability of 27.688% and
assigned medium confidence. Six large underdog/away edges appeared in the same
round, which is a model-audit warning rather than evidence of six bets. The
market/model disagreement must be investigated before staking. Coventry v Hull
was absent from the generated model card, so only eight of the nine remaining
fixtures were assessed.

## Continue tomorrow

Resume from the race-day probability-engine boundary. Do not alter the frozen
achieved-run ratings to make individual race opinions fit. Priority checks are:

1. expand and audit national race-history coverage, especially for lightly
   raced and interstate runners;
2. build campaign/readiness features separately from Sustainable Ability;
3. preserve a visible coverage/uncertainty flag in every live race table; and
4. audit the EPL round-two underdog probabilities and the missing Coventry v
   Hull fixture before treating the displayed EV as actionable.
