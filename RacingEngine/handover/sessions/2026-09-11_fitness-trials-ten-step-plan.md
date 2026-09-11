## Fitness and trials engine — ten-step review branch

This branch builds a reusable Australian thoroughbred fitness/event layer for both the existing Saturday engine and the planned Wednesday/Friday engine. The two engines will share canonical race and trial events; meeting type is a feature, not a duplicated database.

Each step will be implemented, documented and tested separately. Work pauses for owner review and sign-off before the next step.

### Ten review steps

1. **Event contract and schema** — create the immutable `fitness_events` contract for races, official trials, jump-outs and other preparation events, with durable horse IDs and provenance.
2. **Official trial source discovery** — map Racing Australia, Racing NSW, Racing Victoria/Racing.com and licensed-source calendars, result pages and access limits.
3. **Trial meeting ingestion** — download trial calendars, fields and results; extract every horse in every heat; preserve raw payloads and hashes.
4. **Horse identity linking** — link trial runners to the existing durable horse IDs, with alias queues and manual review for unresolved names.
5. **Deduplication and quality controls** — enforce event uniqueness, date ordering, source reconciliation, trial-type classification and missing-data reason codes.
6. **Three-year historical backfill** — collect the available trial archive for the existing horse population and produce coverage, gap and source-quality reports.
7. **Preparation and fitness state** — build the event sequence and pre-race state: layoff, first-up/second-up, trial count, recency, workload and current campaign stage.
8. **Meeting-type conditioning** — add Wednesday/Friday versus Saturday, metro/provincial/night and carnival context without duplicating the event store.
9. **Fitness model and chronological testing** — compare race-only and trial-enhanced baselines across first-up, long-layoff, lightly raced and carnival cohorts.
10. **Operational integration and sign-off** — run continuous ingestion, publish explainable fitness outputs, document limitations and seek explicit approval before any ratings, prices or bets consume the result.

### Operating rule

Official trials are ingested immediately as first-class preparation events. Each trial advances the preparation sequence by one event, while retaining `event_type=official_trial` so the model can learn its context rather than silently treating every trial as an ordinary race.

### Current data finding

The existing database contains race history and horse identity tables but no identifiable trial rows, so the trial source and backfill work is new. No production rating, map, tempo, price or betting output is changed by opening this branch.
