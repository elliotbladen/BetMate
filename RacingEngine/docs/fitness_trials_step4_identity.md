# Fitness trials — Step 4: durable horse identity linking

Step 4 links extracted trial rows to the existing durable `horses` registry. The linker is intentionally conservative because a displayed horse name is not a universal identifier.

## Match order

1. A provider horse ID already present in the registry (exact crosswalk).
2. A unique normalized canonical name or reviewed/source alias.
3. Otherwise quarantine the row as `no_registry_match` or `multiple_horse_candidates`.

Ambiguous names are never auto-merged. The result carries `identity_method`, `identity_confidence`, the identity version, and any name transformations. Quarantined rows can be persisted in `fitness_identity_quarantine` with the source event, candidate IDs, URL, raw row and parser version for review.

The module accepts rows from Step 3 and returns linked rows without inventing a horse. A successful link is then safe to pass to the append-only `fitness_events` table in Step 5. This preserves the owner’s rule that each official trial is ingested as one preparation event while keeping `event_type=official_trial`.

## Review implications

- A provider ID must be supplied by a trusted source before it can be used; a guessed or scraped number is not sufficient.
- Name-only matches are accepted only when the normalized key resolves to exactly one durable horse.
- Unresolved and ambiguous rows remain available for manual alias review and do not silently enter modelling.
