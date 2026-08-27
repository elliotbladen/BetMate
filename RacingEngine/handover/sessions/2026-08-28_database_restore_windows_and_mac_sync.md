# Handover — database restore, Windows validation and Mac sync

Date: 28 August 2026  
Working branch: `local-sandbox`  
Database seed source commit: `532629a369e1706823f27f4bc279d8bde2335954`  
Cherry-picked Windows commit: `cb6afe2`

## Purpose and modelling boundary

This session made the cross-machine RacingEngine data foundation operational.
It did **not** promote a new rating, change the accepted V2 run figures, or
start pricing work.

The accepted V2 run-rating foundation remains frozen. The naive V2
median-last-three current-state predictor remains rejected. The next modelling
objective remains `horse-ability-v2.1`: convert accepted V2 run performances
into a validated current Horse Ability using sustainable peak, recency,
uncertainty, campaign/layoff state, distance suitability and going suitability,
one registered family at a time. Do not move to market EV testing or claim fair
prices before this layer passes the frozen chronological comparisons.

## Work completed on Windows

1. Cherry-picked database seed commit `532629a` onto `local-sandbox` as
   `cb6afe2`. A branch merge was deliberately avoided because the racing branch
   and `local-sandbox` have diverged and the latter contains newer sports work.
2. Preserved the pre-restore database at:
   `data/backups/racing_engine_pre_seed_restore_2026-08-28.sqlite`.
3. Verified the backup is byte-identical to the original. Both SHA-256 values:
   `927B82A2C69FFD310E9D34EFBBCFC3DF23DB48D860B4F2414C6002F9E27B36DC`.
4. Restored the Git LFS seed into `data/racing_engine.sqlite` through the new
   streaming `restore_db.py` helper.
5. The restore executed 1,096,330 SQL statements and passed
   `PRAGMA integrity_check` before replacing the live database.
6. Added `audit_db.py` for deterministic post-restore integrity, schema, core
   count, date-range and source-coverage checks.
7. Created `.venv` with Python 3.12.10 and installed the pinned dependency
   `pypdf==6.16.1`.
8. Ran every discovered RacingEngine test: 99 passed, one skipped. The skip is
   expected because the cached 15 August 2026 RNSW PDF is not present locally.
9. Regenerated only the two derived V1 tables intentionally omitted from the
   seed, using exclusive cutoff `2026-08-23`. Accepted/frozen V2 tables were not
   rebuilt or mutated.

## Verified live database

Post-regeneration database size: 715,542,528 bytes.

| Check/table | Result |
| --- | ---: |
| `PRAGMA integrity_check` | `ok` |
| Foreign-key violations | 0 |
| Tables | 53 |
| Horses | 9,096 |
| Runner results | 52,094 |
| Runner sectionals | 189,778 |
| Steward reports | 1,079 |
| Steward events | 6,714 |
| Canonical sectionals | 43,305 |
| V2 clean races | 2,720 |
| V2 clean runner results | 36,712 |
| Frozen V2 run performances | 28,939 |
| Regenerated V1 run performances | 19,667 |
| Regenerated V1 horse states | 11,012 |

Result date range is 12 August 2023 through 22 August 2026.

Runner-result source coverage:

| Source | Rows |
| --- | ---: |
| `racing-com-nsw-authorised-v2` | 20,014 |
| `racing-com-nsw-results-fallback` | 4,524 |
| `racing-com-rv-authorised` | 16,958 |
| `rnsw-authorised` | 10,598 |

The V1 regeneration command and exact output were:

```text
python -m racing_engine.performance --as-of 2026-08-23
{"horse_states": 11012, "performances": 19667}
```

The cutoff is exclusive, so it includes stored results through 22 August. This
is an operational current V1 snapshot, not a newly promoted model or a change
to the frozen historical benchmark protocol.

## Data-readiness interpretation

The deterministic broad audit over 12 August 2023 to 22 August 2026 found
4,064 source-race rows and 52,094 runners. Runner-result presence was 100%.
Selected coverage results were:

| Feature | Coverage |
| --- | ---: |
| Results | 100.00% |
| Winner | 98.72% |
| Weather | 99.53% |
| Trainer | 98.85% |
| Carried weight | 98.85% |
| Jockey | 95.53% |
| Official handicap rating | 94.34% |
| Barrier | 81.91% |
| Sectionals | 77.60% |
| Margins | 68.25% |
| Class | 60.80% |
| Official race time | 55.71% |
| Individual runner time | 50.53% |
| Historical pre-race cards | 1.21% |
| Explicit DT-W | 1.23% |

The broad readiness status is `NOT_READY`, with blocking categories for class,
margins, official time, steward checks, weather and winner. Do not interpret
this as a failed restore. The audit evaluates every source row independently;
NSW structured result ownership and separate PDF/fallback evidence create
intentional partial/duplicate source representations. The accepted V2 pipeline
already applies identity ownership, clock quarantine and source-specific
semantics. Nevertheless, the gaps remain real constraints for feature coverage
and must not be imputed away.

## MacBook continuation procedure

From the repository root:

```bash
git pull --ff-only
git lfs pull
cd RacingEngine
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

For a Mac with no local RacingEngine database:

```bash
./restore_db.sh
```

For a Mac that already has a local database, preserve it explicitly:

```bash
mkdir -p data/backups
./restore_db.sh --backup data/backups/racing_engine_before_seed_restore.sqlite
```

Then validate and rebuild the intentionally excluded V1 snapshot:

```bash
.venv/bin/python audit_db.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m racing_engine.performance --as-of 2026-08-23
.venv/bin/python audit_db.py
```

Expected final V1 counts are 19,667 `run_performances` and 11,012
`horse_rating_states`. Expected V2 count remains 28,939
`v2_run_performances`. Stop and investigate rather than accepting materially
different counts, any integrity failure, or any foreign-key violation.

## Restore-helper note

The original seed contains a non-SQL informational list of table names between
`BEGIN TRANSACTION` and the first insert. The original shell/`sqlite3` restore
path treats that list as SQL and fails. `restore_db.py` safely skips those bare
identifiers, restores into a temporary file, runs the integrity check, and only
then replaces the destination. `restore_db.sh` is now a thin wrapper around
that Python implementation. Use these helpers on both machines.

## Next work — do not skip the gate

1. Confirm both machines are on the same Git commit and reproduce the audit
   counts above.
2. Preserve accepted `v2_run_performances` unchanged.
3. Pre-register `horse-ability-v2.1` candidate families and frozen comparison
   periods before fitting.
4. Test robust sustainable-peak versus median/recency alternatives first.
5. Add recency, explicit uncertainty, campaign/layoff state, distance and going
   suitability separately, retaining only repeatable chronological gains.
6. Compare on identical races against equal chance, accepted V1 and the frozen
   failed V2 current-state predictor using log loss, Brier, calibration,
   ranking, coverage and jurisdiction/distance segments.
7. Keep `energy-sectionals-v2.3` frozen for forward testing. Do not promote it
   until next-start uncertainty resolves and Victorian staying data is honest.
8. Market-EV and production pricing remain downstream of a frozen Horse Ability
   layer.
