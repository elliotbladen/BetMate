# RacingEngine — data catch-up and agreed ratings build plan

Date: 2026-08-20

## Work completed

- Imported 15 August 2026 Rosehill: 10 races, 103 finishers and 719 sectionals.
- Imported 15 August 2026 Caulfield: 9 races, 126 runner rows, 104 finishers and
  312 sectionals.
- Fixed the new-format RNSW parser to use the winner's supplied overall clock as
  race-level official time when the legacy Official header is absent.
- Added a regression test; all seven tests pass.
- Ran class, historical metadata, weather and steward enrichment.
- Rebuilt `performance-par-v1.0` as of 2026-08-16: 18,140 performances and
  10,752 horse states.

## Current database

- 259 meetings, 2,471 races, 29,845 runner results and 112,193 sectionals.
- All races have categorical class and matched weather records.
- 1,079 steward reports, 6,714 events and 556 human-review flags.
- All 259 meetings have a completed steward-source check.

## Outstanding steward-source item

Rosehill on 15 August returned no published steward reports through the current
authorised Racing.com public-form source. The completed absence is stored. Before
trip/steward modelling, investigate whether an official Racing NSW report source
is available under the project's approval and, if so, add it as a separately
attributed importer. Do not treat the current absence as evidence of a clean run
and do not invent events. Caulfield is complete: nine reports, 55 events and five
human-review flags.

## Decisions agreed with user

- Work through the ratings build one step at a time.
- Test every meaningful new feature family against the immediately previous
  accepted model, followed by justified interaction and ablation tests.
- Freeze chronological evaluation rules before changing core rating math.
- Treat the market as an external benchmark, not an input to base Horse Ability.
- Matching a mature closing market with objective rating inputs would itself be
  a strong result; later work tests incremental information and CLV.
- Model nominal class hierarchically: jurisdiction, meeting grade and venue plus
  the actual pre-race field. A BM72 is not universally equivalent.
- Keep ability, historical run context, current intent/condition and today's
  projected-race factors as separate layers.
- Steward reports are incomplete. Later structured video, track-pattern,
  stable/intent and yard evidence must be prospective, timestamped and auditable.

## Canonical plan

Read `docs/ratings_build_plan.md` first. It contains success criteria, evaluation
and market policy, hierarchical class design, contextual evidence rules and the
agreed 12-step build sequence.

## Next action

Start Step 1 only: build the automated data-readiness report. Do not begin class
or Race Strength math until Steps 1–3 are complete.
