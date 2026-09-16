# Saturday metropolitan stewards-report backfill

This audit covers the Saturday metropolitan race inventory already present in
the RacingEngine database, from 16 September 2023 through 15 September 2026.
It does not claim that the calendar itself is complete.

The inventory contains 2,697 races across 276 meetings. Before this backfill,
1,099 races had non-empty stored report text and 1,598 did not:

| State | Existing | Newly staged | Still unresolved |
| --- | ---: | ---: | ---: |
| NSW (Randwick/Rosehill) | 10 | 1,182 | 186 |
| Victoria (configured metro tracks) | 1,089 | 183 | 47 |
| **Total** | **1,099** | **1,365** | **233** |

The new `racing_engine.stewards_backfill` collector keeps the source database
read-only and writes reports to a separate staging database. It archives each
download with its source URL, byte count and SHA-256 hash. It validates the
meeting date and venue, checks that the report mentions at least one runner from
the stored race identity, rejects empty/duplicate race sections, and records
every unresolved race with a reason.

The local staging run produced 322 raw source files and a 49 MB staging SQLite
database under `data/stewards_backfill_2026-09-16/`. Those source files and the
staging database are intentionally ignored by git because they are generated
research data. A second parser pass excluded supplementary race headers and
accepted PDF text whose date spacing had been collapsed by extraction. The audit
is resumable with the same command and will reuse verified archives.

The 233 unresolved races require source-specific review. The remaining cases
include races where Racing.com returned no report text, malformed or non-race
PDF layouts, date/venue mismatches, reports with no stored runner identity
anchor, and two NSW dates where the Racing Australia PDF URL returned 404. No
unresolved item is marked complete.

Validation: the focused steward parser, storage and backfill tests pass (23
tests, one pre-existing skip). The existing source database was only opened
read-only during the audit.
