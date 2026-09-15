# Fitness and trials engine — Step 3 ingestion

Status: **Step 3 complete; awaiting owner review**

This step adds the meeting-level collector and raw archive contract. It accepts
explicitly supplied calendar, field or result URLs; it does not crawl arbitrary
pages or invent result URLs.

## Delivered

- `racing_engine/trial_ingest.py`;
- deterministic HTML table extraction for horse, trainer, jockey, barrier,
  trial type, position, margin, time and distance fields;
- trial-link discovery from an explicitly supplied meeting page;
- content-addressed raw HTML archive;
- payload hash and parser-version metadata;
- idempotent archive writes;
- per-page manifest with status, row count, discovered trial links and errors;
- focused synthetic HTML tests.

The extracted rows are still source-shaped. Step 4 will resolve horse identity;
Step 5 will reconcile and validate before rows enter the canonical
`fitness_events` table.

## Operational safeguards

- source URL is retained on every extracted row;
- raw payloads are cached before parsing;
- duplicate payloads do not create duplicate files;
- fetch failures remain visible in the manifest for retry;
- network collection requires explicit URLs and a source ID;
- the collector uses a descriptive user agent and a bounded timeout;
- terms, robots and rate limits remain the operator's responsibility.

No production database rows were changed by this step.
