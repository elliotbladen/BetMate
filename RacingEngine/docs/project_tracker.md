# RacingEngine project tracker

Last audited: 2026-08-20. Internal non-commercial research project for NSW
and Victorian Saturday metropolitan thoroughbred racing.

This is the canonical status and forward-plan document. Counts below come from
`data/racing_engine.sqlite`; implementation status was checked against the code
and tests, rather than inferred from proposed design documents.

## Current position

RacingEngine has a strong, source-audited historical data spine and two
transparent research baselines. It does **not** yet have a validated V2 ability
rating, a race-strength model, or a production fair-pricing model.

The active historical model is `performance-par-v1.0`. The older
`base-lengths-v0.1` model can create shadow card prices, but those prices omit
class, weight, track variant, map, pace and trip. Neither model should be
presented as a betting edge.

## Operating rules

- Preserve raw source data and provenance; never invent missing values.
- A rating is not a price. Pricing follows validated rating layers and a
  projected-race model.
- Every historical calculation must be strictly as-of-date. Future results
  cannot influence an earlier rating or par.
- Promote a new signal only after it improves a true out-of-sample comparison
  with the immediately previous model.
- Keep source evidence, deterministic classifications, model interpretations
  and human judgments in separate layers.
- Existing source approvals are for internal research. Do not redistribute raw
  material or expose it as a customer data product.

## Verified data snapshot

Official results now cover 12 August 2023 through 15 August 2026.

| Area | Meetings | Races | Result source |
| --- | ---: | ---: | --- |
| NSW metro | 139 | 1,325 | 1,006 RNSW-authorised races plus 319 explicitly labelled Racing.com result fallbacks |
| Victorian metro | 120 | 1,146 | Racing.com/Racing Victoria-authorised history |
| Total | 259 | 2,471 | Source-preserved local research database |

Other verified holdings:

- 29,845 runner-result rows.
- 112,193 sectional/in-run rows.
- All 2,471 races have categorical class and matched weather records.
- 552 explicit NSW distance-travelled-versus-winner values; missing values
  remain null.
- 1,079 official steward reports and 6,714 classified runner events; 556 are
  flagged for human review. All 259 meetings have a completed report check.
  Rosehill on 15 August has no published race reports in the checked source;
  that absence is recorded rather than treated as missing ingestion.
- The latest `performance-par-v1.0` rebuild (`as_of_date=2026-08-16`) contains
  18,140 run performances and 10,752 horse states, including the usable 15
  August results.
- Card storage is much smaller than result history: 29 racecards / 385 declared
  runners across 8 and 15 August 2026. Historical result enrichment is not the
  same thing as having full pre-race cards.

## What is implemented

### Ingestion and evidence

- FormFav Saturday card ingestion for configured NSW/VIC metro meetings, with
  raw response archiving and ingestion-run status.
- Canonical manual CSV imports for official results and runner sectionals.
- Racing NSW PDF ingestion with archived reports, old/new layout parsing,
  meeting discovery and labelled Racing.com results-only fallback.
- Racing.com ingestion for configured Victorian metro meetings, including
  result, runner split and in-run-position fields.
- Historical metadata enrichment for barrier, carried weight, jockey, trainer,
  official handicap rating, scheduled start and class text.
- Deterministic race-class taxonomy, hourly station-weather matching, explicit
  NSW DT-W extraction and deterministic steward-event classification.

### Research baselines

- `base-lengths-v0.1`: sequential beaten-length updates, reliability shrinkage,
  normalized shadow win probabilities and persisted price snapshots.
- `performance-par-v1.0`: prior-only median track/distance/going pars, auditable
  time/margin run performances, a small capped terminal-sectional component,
  recency-weighted horse states, shrinkage and uncertainty.
- A chronological evaluator that rebuilds states using only races before each
  scoring date and stores Brier score and log loss.

### Verification

- Six unit tests pass with `.venv/bin/python -m unittest discover -s tests`.
- Tests cover canonical imports, separated result/sectional storage, card
  storage, V0 ratings/prices, V1 pars/states, and steward evidence isolation.
- The only stored walk-forward result is for the 2026-08-15 cutoff: 417 races,
  4,370 runners, mean Brier 0.085534 and log loss 2.309284. This is a baseline
  diagnostic, not sufficient validation of the model.

## Known gaps and technical debt

1. **Class and race strength are not modelled.** The taxonomy exists, but no
   numerical class prior or Race Strength Rating exists.
2. **The sectional feature is not normalized across sources.** V1 queries
   `marker_metres = 0`; that represents 400m-to-finish in the Victorian feed
   but can represent only the final 200m in NSW reports. Keep its contribution
   provisional until genuine last-400 and final-200 fields are separated.
3. **No daily track variant or rail/meeting adjustment exists.** Long-run pars
   can therefore confuse a fast or slow meeting with horse ability.
4. **Weight/WFA, pace, map, barrier, DT-W, weather and steward evidence are
   stored but not consumed by V1.** This is deliberate pending validation.
5. **Evaluation coverage is thin and unsegmented.** There is one stored run,
   with no market baseline, calibration buckets, winner-rank report, or splits
   by track, going, field size and class.
6. **Horse identity is name-based.** `horse_aliases` exists but currently has
   zero rows; name normalization alone is not a durable identity solution.
7. **Tests are storage-oriented.** Importer parser fixtures, source edge cases,
   no-look-ahead invariants, idempotency and failure/retry behavior need direct
   coverage.
8. **V0 card pricing is separate from V1.** `price_card.py` uses
   `base-lengths-v0.1`, not the newer V1 horse states. There is no implemented
   V1/V2 projected-race pricing path.
9. **Rosehill 15 August has no published steward reports in the current checked
   source.** The source check is recorded complete. Investigate a separately
   attributed official Racing NSW report source before steward/trip modelling;
   absence must not be interpreted as a trouble-free run.

## Rating architecture

1. **Horse Ability Rating** — current underlying ability derived from adjusted
   historical merit, with explicit uncertainty.
2. **Race Strength Rating** — quality of a completed race estimated from
   pre-race field ability, official class, adjusted time, pace shape and depth.
   Later form may validate it, but must not leak into its original estimate.
3. **Today's Projected Race Rating and price** — expected merit under today's
   weight, class, barrier, map, rail, weather, jockey, scratchings and fitness,
   then converted into a calibrated probability book.

## Agreed build order

### Phase 0 — lock down the baseline

- Add parser and no-look-ahead regression tests using fixed fixtures.
- Record a reproducible full V1 evaluation report with coverage, calibration,
  winner rank and segment diagnostics.
- Define the immutable train/validation/test dates and comparison protocol.
- Resolve horse aliases/identity collisions before model comparisons depend on
  longitudinal histories.

### Phase 1 — class prior and Race Strength Rating

- Specify the class prior and race-strength math separately from plumbing.
- Use only information available before each race for the pre-race strength
  estimate; store later-form validation separately.
- Add schema/pipeline support and an auditable component breakdown.
- Compare against V1 under the locked walk-forward protocol. This remains the
  highest-priority modelling gap.

### Phase 2 — daily variant and weight/WFA

- Estimate a robust, shrunk daily track variant without class/pace leakage.
- Normalize carried weight against an explicit WFA/sex/age framework.
- Add each component independently and retain only validated improvement.

### Phase 3 — sectionals, pace and trip

- Fix the NSW/VIC last-400 mismatch first.
- Derive source-consistent pace-shape features and validate DT-W rather than
  treating missing distance as zero.
- Estimate meeting/rail patterns conservatively and separately from intrinsic
  horse ability.

### Phase 4 — steward ablation

- Test each event category independently over the next one, two and three
  starts with an explicit decay.
- Keep wide/no-cover at zero unless supported by DT-W/sectional evidence.
- Treat material veterinary findings as fitness/uncertainty flags, never an
  automatic forgiveness lift.

### Phase 5 — projected race and pricing

- Build probabilistic speed-map and pace scenarios from pre-race cards.
- Combine Ability, Race Strength and today's conditions without mutating the
  base ability figure.
- Produce calibrated win probabilities and uncertainty bands, then compare
  with market/open/close prices and closing-line value.

## Steward policy

Steward reports remain contextual evidence, not a free-text rating engine.
Current stored suggestions are capped at +0.75 for a moderate trip incident,
+0.75 to +1.50 for severe interference/held-up evidence, and +2.0 in aggregate
if eventually combined. Wide/no-cover receives no automatic lift. Material
veterinary findings create a fitness/review flag only. None of these values is
currently consumed by `performance-par-v1.0`.

## Human input

Routine ingestion should remain automated. Human review is limited to material
veterinary or severe/ambiguous reports, observed same-day track pattern, and
optional parade/trial/trainer intelligence recorded with source, timestamp and
confidence. No manual observation may silently overwrite Horse Ability.

## Document status

- `README.md` is the operator guide.
- `three_season_rating_assignment.md` explains the V1 model and longer-term
  architecture.
- `v2_build_spec.md` is a **deferred research note**, not the active V2 plan. It
  covers daily variant, campaign stage and meeting bias; the 2026-08-16 scope
  decision put class prior and Race Strength first.
- `handover/sessions/2026-08-16_v2-build-spec-and-scope-decision.md` records that
  scope decision and the division between core model judgment and supporting
  data/evaluation/plumbing work.
- `ratings_build_plan.md` is the canonical detailed plan for feature testing,
  market benchmarking, hierarchical class strength, contextual evidence and
  the agreed 12-step build sequence.
