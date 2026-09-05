# Map Position Indicator, Chelmsford GUI and V2 plan

Date: 4 September 2026

## Decisions preserved

The Map Position Indicator is a separate pre-race product answering **where
will each horse settle?** The Expected Tempo Engine separately answers **how
fast will the race be run?** Neither may silently alter accepted horse ratings.

Missing NSW `early_to_800_seconds` can be recovered by subtracting a complete
final-800m chain from official runner finish time, but only when the source rows
are known consecutive 200m intervals. All required intervals and the 800m
boundary must exist, identities must agree, and sanity checks must pass.
Observed and derived values retain separate provenance.

## Implemented state

- Architecture: `docs/map_position_indicator_architecture.md`
- Engine: `racing_engine/map_position.py`
- Early recovery: `racing_engine/sectional_features.py`
- Map steward categories: `racing_engine/stewards.py`
- Course registry: `config/map_course_configurations_v1.json`
- Supabase schema: `../supabase/migrations/20260904_map_position_shadow.sql`
- Scorecard: `reports/map_position/map_position_v1_scorecard.md`
- Test result: 168 passed and one skipped.

Historical build: 43,721 canonical rows, 37,237 early-to-800 times and 37,713
observed map labels. Each field prediction uses 10,000 constrained simulations.

| Metric | Map V1 | Population baseline | Result |
|---|---:|---:|---|
| Log loss | 1.30154 | 1.26434 | Failed |
| Brier | 0.17713 | 0.17262 | Failed |
| Top-state accuracy | 28.37% | — | Descriptive only |

Governance remains `SHADOW_ONLY_DIAGNOSTIC`. No pricing, rating, EV, selection
or staking consumer is authorised.

## Chelmsford GUI

- Standalone page: `../local-racing-map/index.html`
- Frozen map data: `../data/racing/chelmsford-map-2026.json`
- Generator: `scripts/build_chelmsford_map_demo.py`
- Next page: `../app/racing/map/page.tsx`
- Local URL: `http://127.0.0.1:8765/local-racing-map/`

Card: Royal Randwick R9, Chelmsford Stakes, 5 September 2026, 1600m Group 2
Weight For Age, Soft 5, +3m rail, fine. Attica was scratched, leaving nine.
The Euphrates is explicitly marked low-data.

The screen is approximately 70–75% information-complete at T-2 days, expected
to reach 85–90% race morning and about 95% near T-30m. This describes context
completeness, not model validity. Next.js dependencies could not finish
installing because Windows returned `ENOSPC`; no user files were deleted.

## Exact V2 work

1. Collect three years of official Randwick/Rosehill post-race stewards'
   reports and pre-race Racing NSW Raceday Rundown/tactics documents.
2. Store tactical intention separately from actual outcome, with timestamps,
   source URL, payload hash, parser version and preserved evidence.
3. Condition profiles on 900–1100m, 1200–1300m, 1400–1500m, 1600–1800m,
   1900–2200m and 2400m+ bands, plus track, going, field size, preparation
   stage, barrier percentile and verified first-turn distance.
4. Use a fallback hierarchy: horse at track/distance, horse distance band,
   horse overall, bounded trainer/jockey prior, comparable-runner prior.
5. Chronologically compare population, last-start, median-last-three, V1,
   distance V2 and V2 plus NSW tactics using log loss, Brier, calibration,
   leader accuracy and expected-rank error, split for NSW and Victoria.
6. Use Racing NSW's published metropolitan speed maps as an independent
   comparison benchmark, not as a copied training answer.
7. After passing historical gates, save append-only T-24h, T-6h, T-30m and
   T-5m forecasts and grade at least 500 live runners before price integration.

## Resume point

Build the dedicated Racing NSW report/Raceday Rundown downloader and execute the
three-year Randwick/Rosehill backfill. Then build distance-conditioned V2 and
evaluate it against the frozen baselines. Do not promote V1 because its GUI is
useful.
