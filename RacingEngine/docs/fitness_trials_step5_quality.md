# Fitness trials — Step 5: deduplication and quality controls

Step 5 prevents duplicate or malformed trial observations entering the append-only fitness event store.

The gate requires `source`, `source_event_id`, `horse_id` and an ISO event date. It validates event type and date format, computes a stable SHA-256 payload hash, and tags the quality version. Identical repeats of the same `(source, source_event_id, horse_id)` and payload collapse to one row. If the same key arrives with a different payload, neither version is silently selected: the later row is quarantined as a conflicting duplicate for review.

Missing fields, invalid dates and unsupported event types are also quarantined. This preserves evidence for correction while keeping modelling inputs deterministic. The gate runs after Step 4 identity linking and before insertion into `fitness_events`; it does not alter ratings or prices.
