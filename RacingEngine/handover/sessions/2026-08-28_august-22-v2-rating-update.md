# Handover — 22 August 2026 V2 run-rating update

Date: 28 August 2026  
Data cutoff: `2026-08-23` exclusive  
Model version: `form-first-v2.0` (methodology unchanged)

## Outcome

The accepted V2 run-rating database now includes the NSW and Victorian races
held on 22 August 2026. This was a weekly data/rating extension only. It did not
alter the V2 formula, promote the rejected current-state predictor, or begin
`horse-ability-v2.1`.

The update added:

- 19 clean races;
- 260 clean runner results; and
- 187 V2 run performances.

The live totals are now 2,739 clean races, 36,972 clean runner results and
29,126 V2 run performances. Database integrity is `ok`; foreign-key violations
are zero.

## Mandatory rating gates

The complete rebuild used:

```bash
python -m racing_engine.v2_ratings --as-of 2026-08-23
```

All elite sanity checks passed:

- reviewed audit rows retained: 25;
- official audit matches: 24;
- audit Spearman: `0.6857937153`;
- expected named horses present: yes;
- at least seven Group 1 runs in the top ten: yes;
- impossible clocks used: no;
- overall sanity gate: passed.

The clean build quarantined 1,404 clock records: 1,401 missing/non-positive,
one physically implausible average speed and two runner clocks too far from the
official clock. None entered a V2 race level.

The deliberately rejected median-last-three V2 current-state predictor remains
rejected. On the now-616-race comparison through 22 August it records log loss
`2.45954`, versus V1 `2.30551` and uniform `2.31997`. This weekly update is not
evidence to promote that predictor.

## Leading 22 August run performances

| Horse | Rating | Race |
| --- | ---: | --- |
| Autumn Glow | 119.683 | Randwick R9 |
| Gringotts | 116.976 | Randwick R9 |
| Sheza Alibi | 115.337 | Randwick R9 |
| Ceolwulf | 113.336 | Randwick R9 |
| Midnight Dynamite | 111.306 | Randwick R9 |
| Lady Shenandoah | 109.720 | Randwick R9 |
| Idle Flyer | 108.880 | Randwick R9 |
| Lindermann | 106.872 | Randwick R9 |
| Green Spaces | 106.843 | Randwick R9 |
| Changingoftheguard | 104.042 | Randwick R5 |

These are individual run performances, not signed-off current Horse Ability
ratings and not fair prices.

## Operational fault found and fixed

The first update attempt was rejected because `load_audit_set` deleted the 25
reviewed audit classifications before discovering that the optional source CSV
was absent on this machine. The database was restored byte-for-byte from the
pre-run backup before continuing.

`load_audit_set` now preserves the reviewed database rows when the optional CSV
is absent. A regression test covers that behavior. The prediction report's test
window label is also derived from the actual latest scored date rather than
being hard-coded to 15 August.

Pre-run backup:

`data/backups/racing_engine_pre_2026-08-22_v2_ratings.sqlite`

Backup/source SHA-256 before the accepted update:

`ED1C4FBE091D6E54A7C59C3F6B4B87D8B131DE51A5294F764E1A9899AA3D1ED0`

## Cross-machine seed

The Git LFS seed was rebuilt from the updated live database using the new
reproducible command:

```bash
python build_seed.py
```

The builder preserves every schema and all core/V2 data while excluding only
the documented large V1-derived row data:

- `run_performances`: 19,667 rows excluded;
- `horse_rating_states`: 11,012 rows excluded.

The refreshed compressed seed is 49,995,895 bytes. It was restored into a new
throwaway database and independently verified before acceptance:

- 1,096,917 SQL statements restored;
- integrity check `ok`;
- zero foreign-key violations;
- 29,126 V2 performances through 22 August;
- excluded V1 tables present with zero rows.

On the MacBook:

```bash
git pull --ff-only
git lfs pull
cd RacingEngine
./restore_db.sh --backup data/backups/racing_engine_before_aug22_seed.sqlite
.venv/bin/python audit_db.py
.venv/bin/python -m racing_engine.performance --as-of 2026-08-23
```

After restoring the seed, expect 29,126 V2 run performances. After regenerating
V1, expect 19,667 `run_performances` and 11,012 `horse_rating_states`.

## Next boundary

The database is current and ready to begin Step 1 planning. Preserve
`form-first-v2.0` run performances as the accepted input layer. The next task is
to pre-register and build `horse-ability-v2.1`; do not reinterpret these weekly
run ratings as signed-off Horse Ability or move directly to game-day pricing.
