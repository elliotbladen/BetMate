# RacingEngine — V2 build spec attempt and scope decision

Date: 2026-08-16

## What happened

Continued from a prior session that had researched three Codex-proposed enhancements
(daily track variant, campaign stage weighting, track bias). That session ran out of
context mid-spec.

This session:
1. Re-read all key files: `performance.py`, `storage.py`, `evaluation.py`, `ratings.py`,
   `classify_history.py`, `project_tracker.md`, `three_season_rating_assignment.md`.
2. Wrote a full build spec to `docs/v2_build_spec.md` covering daily variant, campaign
   stage weighting, and meeting track bias — with math, schema, constants, and
   validation criteria.
3. **User corrected the build order.** The spec was written against the wrong three
   items. The correct build order from `project_tracker.md` is:
   - **1. Class prior and Race Strength Rating** (the biggest gap in V1)
   - **2. Daily track variant + Weight/WFA**
   - **3. Sectionals and pace/trip/DT-W**
4. **User decided Claude is not trusted with the core rating build.** Will handle the
   rating architecture personally. Claude's role going forward is limited to:
   - Data processing and ingestion
   - Model evaluation / logging / diagnostics
   - Pipeline plumbing and schema work

## File created

- `docs/v2_build_spec.md` — covers daily variant, campaign stage, and track bias.
  **Not the correct build order.** The campaign stage and track bias sections contain
  valid empirical research (correlation ratios, shrinkage math) that may be useful
  later, but the spec should NOT be treated as the build plan. Class and race strength
  come first.

## Key empirical findings (still valid, from prior session's data queries)

These were derived from the actual database and are correct regardless of build order:

- Campaign boundary: 60 days (42.3% of gaps > 42d, clear bimodal split)
- First-up correlation with next run: r=0.508 vs mid-campaign r=0.953
- Campaign stage multiplier when eventually built: first-up 0.50, second-up 0.80
- Bad first-up runs (<85 rating) improve +5.7 pts second-up on average
- Prior campaign rating is near-useless for predicting second-up (r=0.077)
- 21,968 runners with 800m/400m position data (VIC) for future bias work
- 85% barrier coverage, 99% weight coverage across the database
- 257 meetings, avg 8.0 races with official times per meeting

## Existing infrastructure for the class build (when user tackles it)

- `classify_history.py` already parses race class text into families: group, listed,
  benchmark, class, maiden, open_or_quality, handicap_unspecified, unclassified
- `race_classifications` table is populated for all races
- `race_results.race_class` has text on most rows
- The class taxonomy and race strength rating are item 1 in `project_tracker.md`

## Claude's role going forward

- Data processing, ingestion, schema migrations
- Model evaluation, walk-forward logging, diagnostics
- Pipeline plumbing (wiring new steps into `run_pipeline()`)
- NOT the core rating math or architecture decisions
