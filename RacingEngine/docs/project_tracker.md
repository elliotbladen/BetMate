# RacingEngine project tracker

Last updated: 2026-08-16.  Internal non-commercial research project for NSW
and Victorian Saturday metropolitan thoroughbred racing.

## Operating rules

- Preserve raw source data and its provenance; do not invent missing values.
- A rating is not a price. Pricing comes only after the rating layers are
  validated and a projected-race model is built.
- Every historical calculation is strictly as-of-date: no future race result
  may influence an earlier rating.
- New signals must improve an out-of-sample comparison against the immediately
  previous model before being promoted.
- Existing source approvals are for internal research use. Raw material is not
  redistributed or exposed as a customer data product.

## What is built

### Historical data foundation

- NSW and VIC Saturday metro history from 19 August 2023 through 8 August
  2026: 2,452 races, 29,616 runner results and 111,162 sectional/in-run rows.
- Historical card metadata: class, weights, barriers, jockeys, trainers and
  official handicap ratings where published.
- Weather matched to scheduled race time with variable-level source quality.
- Official NSW PDF distance-travelled-vs-winner values retained only where
  explicitly supplied.

### V1 ability baseline

- Track/distance/going time pars using prior-race medians.
- One auditable run performance and a recency-weighted current horse state.
- Transparent uncertainty and strict walk-forward evaluation framework.
- V1 deliberately does **not** claim class, weight, daily-variant, trip,
  pace/map or market sophistication.

### Steward evidence layer — completed 2026-08-16

- 257 historical meetings checked through the authorised public form source.
- 1,070 official reports archived and 6,659 runner events classified.
- Categories: slow start, interference, held up, wide/no cover, over-racing,
  gait/direction and veterinary findings.
- 551 severe/material items are marked for human review.
- All report text, exact evidence and parser version are stored separately
  from ratings. No existing rating has changed.

## Rating architecture

1. **Horse Ability Rating** — the horse's current underlying ability from
   adjusted historical merit, class, weight, going, sectionals, trip and
   recency. This is the core user-facing number.
2. **Race Strength Rating** — the quality of a completed race, based on
   pre-race field ability, official class, adjusted race time, pace/sectional
   shape and field depth. Later form validates the number but cannot leak back
   into an original pre-race estimate.
3. **Today’s Projected Race Rating / price** — each runner's expected merit
   today, given Ability + Race Strength plus today's weight, class, barrier,
   map, rail, weather, jockey, scratchings and fitness. This eventually feeds
   a probability model and fair book.

## Steward policy and validation plan

Steward reports are contextual evidence, not a free-text rating engine.

- Minor note: 0 automatic points.
- Corroborated moderate trip incident: maximum +0.75 rating points.
- Severe interference / materially held-up: +0.75 to +1.50.
- Absolute cap: +2.0 points per run after all event components.
- Wide/no cover: 0 automatic uplift until supported by DT-W and sectionals.
- Material veterinary finding: fitness/uncertainty flag only, never a
  forgiveness lift.

When V2 is ready, compare **V2 Base** against **V2 + Stewards** using the same
strict chronological data split. Test each category independently over the
horse's next **one, two and three starts**, with an explicit decaying effect;
also compare race winner probability (Brier/log loss), ranking and
calibration. A signal enters V2 only if it improves the out-of-sample model.

## Next build order

1. Build V2 class prior and Race Strength Rating.
2. Add weight/weight-for-age and daily track-variant components.
3. Normalise sectionals and implement pace/trip/DT-W evidence.
4. Run the steward ablation study across the next three starts and promote only
   validated categories.
5. Build the projected-race/map layer and fair-price simulation.
6. Add Betfair/market comparison and closing-line calibration.

## Human input going forward

Routine source ingestion is automated. Human review is restricted to:

- material veterinary or severe/ambiguous steward reports;
- observed track pattern after the first few races;
- optional parade, trial, trainer or track intelligence, recorded separately
  with source, timestamp and confidence.

No manual item may silently overwrite the base Horse Ability Rating.
