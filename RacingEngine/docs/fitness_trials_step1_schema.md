# Fitness and trials engine — Step 1 schema

Status: **Step 1 complete; awaiting owner review**

This step defines the immutable `fitness_events` contract. It does not ingest
trial data and does not change ratings, map, tempo, prices or bets.

## Contract

Each row represents one horse preparation event:

- `race`;
- `official_trial`;
- `jumpout`;
- `exhibition_gallop`;
- `trackwork`.

The event keeps its type so the fitness model can treat a trial as a real
preparation event without silently pretending it was an ordinary race.

Required identity and provenance fields are `horse_id`, `source`,
`source_event_id`, `source_url`, `collected_at`, `effective_at`,
`parser_version`, `payload_hash` and `raw_json`.

The table is append-only. SQLite triggers reject updates and deletes. A later
correction must be a new observed event or a new source observation; the
original evidence is retained.

## What is deliberately included now

The contract reserves fields for trial heat/type, distance, surface, going,
rail, field size, barrier, finish position, beaten margin, official time,
sectionals, jockey/trainer identity, source payload and parser detail.
This keeps the schema ready for official trial pages and future licensed data
without changing the contract in later collection steps.

## What is not included yet

Step 1 does not choose providers, scrape calendars, resolve unmatched horses,
backfill history or calculate fitness features. Those are Steps 2–7 and require
separate review.
