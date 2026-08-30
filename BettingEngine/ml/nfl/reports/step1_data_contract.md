# NFL Step 1 — Frozen data contract

**Completed:** 30 August 2026  
**Contract:** `nfl-data-contract-v1.0`  
**Development window:** 2014–2024  
**Untouched vault:** 2025  

## Decision

The NFL identifier, spread, feature-timing and dataset-boundary rules are now
locked in executable code. The rebuilt feature store passes the contract with
3,151 unique regular-season games and no duplicate game IDs.

This step does not claim an NFL edge and does not complete the deferred deep
historical opener audit. Historical opening/closing columns remain labels and
benchmarks only; they are prohibited from the pure pre-open feature matrix.

## Frozen conventions

### Game identity

- Canonical historical key: nflverse `YYYY_WW_AWAY_HOME`.
- The season, week, away team and home team in every row must match that key.
- Historical nflverse franchise codes are preserved: `STL` through 2015, `SD`
  through 2016 and `OAK` through 2019.
- Provider aliases `LA`, `LAC` and `LV` are converted to the appropriate
  historical code before joining.
- Historical odds join on season **plus calendar date plus home plus away**.
  A season/team-only join is prohibited because rematches and playoff rematches
  are not unique.

### Spread sign

- Every BetMate NFL spread is the **home-team handicap**.
- Negative means the home team is favoured; positive means the home team is the
  underdog. A Philadelphia home line of `-3.5` is stored as `-3.5`.
- nflverse's raw schedule field is the away-team handicap. It is preserved as
  `schedule_away_spread` and negated into the canonical `spread_line` field.
- Provider closing odds use `spread_home_close` and follow the same home-team
  convention. Cross-provider movement through pick'em is permitted; wholesale
  sign disagreement fails the contract.

### Feature timing and leakage

- Historical Week N EPA features use completed games through Week N-1 only.
- Each row records `stats_through_week = week - 1` and the immutable timing rule
  `week_n_uses_completed_games_through_week_n_minus_1`.
- Scores, outcomes, openers and closes are labels/benchmarks, never pure-model
  inputs.
- Live feature bundles require timezone-aware `as_of` and kickoff timestamps.
- `as_of` must precede kickoff, and every source timestamp must be at or before
  `as_of`.
- The pre-open prediction target remains one hour before the defined market open.
  True timestamped opener construction is deferred to the separate market audit.

### Dataset boundary

- The builder now returns only the requested 2014–2025 regular seasons.
- 2014–2024 is available for development and rolling-origin testing.
- 2025 remains the one-shot vault and must not be used for feature selection,
  hyperparameter selection or tier calibration.
- Postseason rows are excluded from this first regular-season model.

## Rebuild result

| Check | Result |
|---|---:|
| Regular-season rows | 3,151 |
| Unique game IDs | 3,151 |
| Duplicate game IDs | 0 |
| Rows with complete core EWMA features | 3,151 |
| Rows with historical closing spread | 3,065 |
| Closing-spread coverage | 97.27% |
| Schedule/odds direction conflicts | 1.11% |
| Contract result | PASS |

The 1.11% direction-conflict rate comprises a small set of games where two
closing feeds crossed pick'em. The raw nflverse away spread is exactly inverted
into the canonical home spread on every populated row, so this is market-source
variation rather than an unresolved sign convention.

## Defects corrected

1. The previous feature builder processed 2014–2025 PBP but retained the full
   1999–2026 schedule, producing 7,289 rows outside the intended model boundary.
2. Odds were joined using only season/home/away, which duplicated games when the
   same teams met twice or met again in the postseason.
3. Relocated-team PBP used current codes while schedules retained historical
   codes, leaving 168 games with missing team features.
4. nflverse's away-side spread was stored beside provider home-side spreads
   without an explicit conversion.
5. Parquet support was used by the pipeline but `pyarrow` was neither declared
   nor installed.

All five are now corrected in the canonical builder.

## Executable enforcement

- `ml/nfl/data_contract.py` owns identifiers, aliases, required columns, sign
  rules and the contract report.
- `ml/nfl/contracts.py` rejects invalid game identities, naive timestamps,
  post-cutoff sources, empty markets, impossible line ranges and incomplete
  prediction identity.
- `ml/nfl/features.py` performs the season-bounded build and one-to-one
  date-aware odds join.
- `tests/test_nfl_architecture.py` contains 12 passing contract/architecture
  regression tests.
- `ml/nfl/reports/step1_data_contract.json` is the machine-readable PASS result.

## Tier implication

The likely practical NFL stack is four to six modelling tiers, not ten mandatory
adjustment layers. T0 remains a data-health gate rather than a price-making tier.
The working order is team strength, QB/personnel, combined situation/continuity,
weather for totals, and matchup/scheme; market disagreement/confluence remains a
later decision layer. Tiers will be combined or rejected according to measured
incremental value as the baseline develops.

## Deferred—not forgotten

- Reconstructing true timestamped historical openers.
- The manual 50-game market audit.
- Live append-only quote polling and bookmaker eligibility rules.
- Kickoff-level source timestamps for roster, injury, QB and weather features.

Those belong to the later market/live-data work. They do not block Step 2's Elo
and ridge baselines because open/close fields will remain evaluation-only.
