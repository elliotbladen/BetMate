# Horse-racing matrix confluence architecture

## Purpose

Matrix confluence is a confidence and explanation layer. The core model first
produces a runner's fair win probability. A timestamped market book is stripped
of overround. Confluence then asks whether independent evidence supports the
model's disagreement with that market. It does not manufacture or overwrite a
fair price.

## Runner-level flow

1. Freeze the information cutoff for the race.
2. Generate the model probability using only information available at cutoff.
3. Select one market snapshot (opening, 24h, morning, 60m, 15m or BSP) and
   normalise the complete field to a no-vig probability book.
4. Produce timestamped evidence in five families:
   - `horse_profile`: current ability, form cycle, distance and going response.
   - `track_distance_going`: course geometry and demonstrated conditions fit.
   - `race_setup`: barrier, expected map, tempo, field shape and weight setup.
   - `trainer_jockey`: residual stable/rider effects after horse quality and
     race context are controlled.
   - `environment`: weather, rail, surface evolution and travel/rest context.
5. Collapse correlated signals inside each family, then count genuinely
   independent positive and negative families.
6. Assign A/B/C/PASS confidence. A selection cannot qualify without a positive
   model-versus-market probability edge and at least two independent families.

## Historical build table

The research dataset is one row per runner per market snapshot. It should hold
race/runner identifiers, cutoff timestamp, model version/probability, market
source/type/odds/no-vig probability, evidence version and JSON, family scores,
confidence tier, result, and realised return. Raw provider records remain in
their existing append-only stores.

Betfair historical data supplies market prices, BSP, volume and results where
licensed. Official/authorised form and RacingEngine's point-in-time feature
tables supply the contextual evidence. Joining must use reviewed race and horse
identities; fuzzy name matching alone is not acceptable for a final backtest.

## Validation protocol

- Walk forward chronologically. Fit thresholds on training, choose them on
  validation, and report untouched test seasons.
- Snapshot features as they existed before the nominated cutoff. Late
  scratchings and revised going are available only after their timestamps.
- Compare actual wins with the sum of no-vig market probabilities. Report
  market lift, Brier/log loss, calibration, ROI at the same available price,
  and closing-line movement.
- Report A/B/C/PASS and each edge family separately, with sample size and
  uncertainty intervals. No tier is promoted from a small attractive sample.
- Benchmark fair-price model alone versus model plus confluence selection.
- Re-run excluding short-priced runners, low-liquidity markets, unmatched
  identities and suspect snapshots.

## Promotion gates

Research-only until the test sample is large enough, identity and snapshot
coverage are audited, probability calibration does not degrade, and positive
market lift is stable across seasons/tracks/price bands. ROI is secondary and
must survive realistic availability and commission assumptions.

## Initial implementation

`racing_engine.confluence` contains the grouped, capped scoring contract and
strict timestamp guard. `racing_engine.confluence_backtest` reports market lift
and ROI by tier. These are deliberately provider-neutral so Betfair historical
files can be mapped into the canonical market layer without coupling model
logic to one vendor.
