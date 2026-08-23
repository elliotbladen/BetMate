# RacingEngine — full readiness and Betfair audit

Date: 2026-08-21

## Outcome

The user correctly questioned whether completion of Steps 1–11 meant the full
rating/pricing system was ready. It does not. The evaluation spine, identity,
class/Race Strength research and several isolated candidates exist, but most of
the contextual Step 12 architecture remains unimplemented.

## Authoritative current status

- Accepted model remains `performance-par-v1.0`.
- Form-anchored winning margin is the most promising shadow candidate but was
  designed after the old holdout was viewed and requires future evidence.
- Daily variant, full Race Strength and relative carried-weight candidates were
  not promoted.
- WFA is blocked by zero historical runner age/sex coverage.
- Pace/trip, rail/lane bias, campaign state, steward ablation, today's map and
  calibrated production pricing are not built.
- Raw evidence can continue to be ingested. A race is prospective evidence only
  if its prediction was frozen before the result.

## Betfair finding

Free official Australia/New Zealand Thoroughbred CSV files are available from
2020 through July 2026 and contain BSP, result, price/volume summaries and best
available scheduled-start prices plus overround. These overlap the existing
2023–2026 results and should be acquired first. Basic/Advanced/Pro historical
stream data adds one-minute, one-second and API-tick price paths respectively;
Advanced is the sensible later tier for executable back/lay and liquidity work.

## ML finding

The current 2,471 races over 153 race days can support a small regularized
tabular challenger after a point-in-time feature matrix exists. It does not
justify a large neural model. Chronological meeting-day splits, race grouping,
complete probability books and transparent/market baselines are mandatory.

## Next action

Follow the corrected 14-item pre-prospective order recorded under “Full
architecture and market-readiness audit” in `docs/ratings_build_notes.md`.
Begin with durable horse age/sex profiles and official WFA, while separately
acquiring the free Betfair CSV history for market matching.

## End-of-session continuation instruction

The conversation and decisions are also preserved in
`docs/session_2026-08-21_ratings_audit_and_next_build.md` and the permanent
ratings notes. The next active work is explicitly authorized: implement durable
horse profiles (birth date, sex, country), historical age on race day and the
official Australian WFA scale, then test and backtest the isolated effects.

## Continuation result — profiles and WFA

Implemented versioned profile storage, AR161 age derivation and AR168/169/170.
Two refreshed authorised Victorian meetings yielded 228 observations across 218
horses and 1,566 derived historical appearances, but zero exact DOBs and only 73
explicit countries. All 58 tests pass.

The first retrospective relative-WFA weight candidate was slightly worse than
frozen V1: validation +0.001324 and holdout +0.002323 log loss (positive is
worse), with uncertainty spanning either direction. Status is REVISE and not
promotion eligible. Full historical DOB and sire-hemisphere sourcing is next.

## Profile scrape completion

A conservative public-profile scraper now accepts Breednet profiles only when
an exact race date overlaps the local horse history. It produced 6,177 verified
horses and 24,096/29,845 covered appearances (80.7%). Cross-source validation
was 208/208 for both age and sex. AR170 separately flags 1,445 appearances. All
61 tests pass.

The full-profile WFA candidate remains REVISE: validation +0.000230 and holdout
+0.001475 log loss, with both intervals crossing zero. This is substantially
closer to V1 than the sparse run, but still not an improvement. Next learn and
shrink weight effects on training only and separate handicap from set-weight/WFA
race conditions.

## Kilogram conversion correction

Research confirms 1kg equals two Australian official benchmark points, not one.
RacingEngine internal points are length-style units; IFHA implies a distance
curve of roughly 0.735 points/kg at 1000m, 1.102 at 1600m and 2.205 at 2800m+.

The IFHA curve and a training-only shrunk within-horse response were implemented
and tested. Neither improved V1: IFHA +0.000403/+0.001379 and learned response
+0.001226/+0.002236 for validation/holdout. Both intervals crossed zero. All 63
tests pass; no weight response was promoted.
