# Handover — context gates 1–6

Date: 22 August 2026

## Completed

The accepted `performance-par-v1.0` baseline remains frozen. The earlier WFA,
IFHA-distance and learned weight candidates were not promoted. Implemented
`racing_engine/context_features.py`, two versioned storage tables, two tests,
the architecture document and a revised build sequence.

The full database now contains 29,845 weight-context rows and 29,845 strictly
point-in-time runner rows. The point-in-time builder uses only prior races and
explicitly excludes target-result weight. Full suite: 65 passing tests.

## Material findings

Carried weight is available for 29,456 rows and official WFA for 23,526.
Allocated weight is separately present for only 354 rows. The historical source
does not separately preserve apprentice claims, overweight or penalties; those
three have zero verified coverage and are NULL, never inferred. There are 9,096
no-prior-history rows.

Prior context coverage is 20,571 weight, 20,749 Race Strength, 16,917 daily
variant, 18,280 sectional confidence and 3,719 steward-event rows.

## Commands

```bash
.venv/bin/python -m racing_engine.context_features --component point-in-time \
  --output data/outputs/context_feature_build_2026-08-22.json
.venv/bin/python -m unittest discover -s tests -v
```

## Next safe action

Improve source capture for allocated weight/claims/overweight/penalties and
pre-race timestamps. Then import timestamped Betfair history. Only after those
audits should small interpretable candidates be trained on the point-in-time
table and compared by chronological ablation. Do not alter the frozen holdout
or promote a weight coefficient without repeatable out-of-sample evidence.
