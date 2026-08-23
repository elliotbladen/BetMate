# RacingEngine session record — ratings audit and next build

Date: 21 August 2026

## Ground covered

Today the build completed Step 10 Race Strength evaluation, Step 11 daily-
variant/carried-weight evaluation, ten follow-on research/infrastructure items,
winning-margin research and a full architecture/readiness audit.

No weak candidate was promoted. V1 remains accepted. The form-anchored winning-
margin shadow produced the first encouraging retrospective direction, especially
against the identity-only control, but requires genuinely future results.

## Important corrections

V1 already preserves the gap between a winner and horses beaten by a recorded
margin. Its deficiency is that absolute winner merit is mainly fixed by winning
time rather than anchoring the race to reliable opposition/form. The new shadow
candidate addresses that without applying a flat winner bonus.

Completing Step 11 did not mean the complete rating architecture was ready.
Pace/trip, rail/lane pattern, campaign state, steward ablation, projected maps,
calibration, markets and ML remain later work.

## Market and ML decision

Official free Betfair Australia/NZ Thoroughbred CSV history overlaps the project
and can supply BSP plus scheduled-start benchmarks. Detailed stream tiers are
available later for time-path, back/lay, volume and execution work.

ML should wait for the point-in-time feature table and core racing semantics.
The first challenger should be small and regularized, chronologically split by
meeting day and benchmarked against both transparent V1 and market probability.

## Next committed build

1. Durable horse profiles containing birth/foaling date, sex, country and source
   provenance.
2. Historical age on every race date, with Australian season-boundary handling.
3. Versioned official Australian WFA tables.
4. Isolated WFA, carried-weight and form-margin interactions.
5. Data-quality tests, no-lookahead tests and controlled backtests.

Unknown profile evidence must remain unknown. No age, sex or WFA value may be
inferred merely to increase coverage.

## Result of the committed profile/WFA build

The durable profile schema, historical AR161 age engine and official Australian
AR168/169/170 layer are implemented. The source supplied 228 age/sex observations
for 218 horses (73 explicit countries) but no exact DOB. Identity extended these
facts to 1,566 historical appearances. All 58 tests pass.

The first isolated WFA-relative carried-weight diagnostic did not improve frozen
V1: validation delta +0.001324 and historical holdout +0.002323, where positive
is worse. Coverage is incomplete and intervals cross zero, so this is REVISE,
not a rejection of WFA. Exact DOB and sire provenance remain the next data task.

## Seven-part scrape completion

The profile block is now largely resolved without contacting providers. A
race-history-verified Breednet scraper produced 6,177 exact profiles and raised
historical appearance coverage to 80.7%. Racing.com comparison returned 208/208
age and sex matches. AR170 separately flags 1,445 appearances. All 61 tests pass.

The repeated chronological WFA test improved toward baseline but did not beat
it: validation +0.000230 and holdout +0.001475 log loss. The one-point-per-kg
candidate stays REVISE. The next test must estimate/shrink the weight response
from training data and distinguish handicap from set-weight race conditions.
