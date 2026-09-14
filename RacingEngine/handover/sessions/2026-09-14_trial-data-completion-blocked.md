# Trial data foundation — 14 September 2026

**Not ready for sign-off. PR #14 stays open. No fitness calculations or release are authorised by this checkpoint.**

The owner requested resolution of unmatched horses and empty/ambiguous meetings, the planned historical/geographic backfill, verified clocks and consistent jockey/trainer naming before calculations. The saved plan specifies three years of available Australian trial history for the existing horse population. The calendar window is 14 September 2023 through 13 September 2026.

## Completed and verified

- Archived and date-validated all 1,096 daily Racing.com calendars. They identify 4,125 trial/jumpout meeting IDs across NSW, VIC, ACT, QLD, SA, WA and TAS. NT has no returned trial entries; this does **not** establish NT completeness.
- Cached results for 291 meeting IDs in the combined runs: 274 populated, 17 empty. Added 7,480 historical source observations. The review database now has 16,389 Racing.com observations and 4,730 legacy accepted fitness-event rows. Source observations and accepted events are different denominators.
- Installed 336 verified public horse profiles from the frozen 5,159-horse recent cohort, creating 139 durable horse identities and resolving 233 previously unmatched observations. Profile identity requires provider ID, registered name and birth date; conflicting names, dates and provider IDs are held. Retrospective identity evidence cannot become available before collection.
- Installed 508 official Racing Australia observations from 11 complete sheets. Header/date/venue/runner meeting keys, complete heat lists and advertised starter totals reconcile. Interim results, unknown statuses, missing headers and human-verification pages are not accepted. Zero clocks/sectionals remain missing.
- Added immutable corrections and a `trial_normalized_observations` view. Four Warwick Farm 18 August source heat assignments are corrected using official results: Flying For Fun 1→4, Without Peer 7→4, Weeping Woman 6→4, Tendi 14→13. Original rows remain intact.
- 1,893 observations have official heat-clock and participant-name evidence. Heat times remain winner/heat clocks, never inferred individual times for other runners. Official result sheets supply participant names; there is no fuzzy merge of jockeys or trainers.
- Confirmed the empty Randwick 31 July listing 5195235 duplicates populated listing 5197249, with the same source URL and a matching heat set. Warwick Farm 21 July remains unresolved: its empty listing has 16 heats, whereas the populated listing has only 10. Same URL alone is insufficient.
- Reconciliation replay inserted **zero** additional rows. All original 3,280 fitness events, 8,909 calendar observations, 10,055 horse records, 6,421 history observations, 1,300 NSW profile records and 1,189 original identity resolutions compare unchanged against the pre-run backup. SQLite integrity is `ok`; foreign-key violations: zero.
- 76 focused tests passed together; the subsequent identity-conflict regression also passes (77 tests total), including source identity/count rejection, retrospective profile availability, scratch/finish separation, immutable replay, source access refusal, and calendar cache reuse without network or database writes.

## Actual blockers

Racing.com began returning HTTP 403. Racing Australia subsequently returned HTTP 200 pages titled “Are you human?”. Bulk requests were stopped; no credentials, IPs or challenge workarounds were used. Do not retry until normal access is restored or official exports are provided. Collectors now bound queued requests, stop on HTTP 401/403/429 or a recognised access challenge, and preserve checkpoints. Racing Australia uses one request at a time.

The result/profile backfill is incomplete. 10,856 source observations remain unmatched, including newly downloaded historical horses beyond the original registry; this is not a count of unique horses. Sixteen empty source meeting IDs remain unresolved across both runs. The duplicated Geelong 19 August heat numbers and Traralgon conflicting heat clocks still require source evidence. Most observations have no independent official-sheet match yet. The original NSW ANOTHERBADDECISION/WADDLES identity conflict also remains open. National calendar discovery is **not** national results completeness; WA/NT and country trial coverage still need primary-source reconciliation.

The existing 20-horse browser audit remains valid for its sampled recent observations, but it cannot establish three-year or national completeness. Do not use `fitness_events` alone for sign-off or calculations; consult the correction view and its identity, clock and source-review flags.

## Local artifacts and safe continuation

Review database: `/Users/elliotbladen/BetMate/RacingEngine/data/trials_review/nsw_archive/trials_review.sqlite`.
Original registry/rating database: `/Users/elliotbladen/BetMate/RacingEngine/data/racing_engine.sqlite` — read-only.

Run roots under `nsw_archive/runs/`:

- `2026-09-14_national_three_year`: frozen dates/states, daily calendars, meeting plan/checkpoints and access-block record. Reuse `2026-09-13_calendar_expansion` archives; do not restart completed downloads.
- `2026-09-14_racing_com_profiles`: frozen 5,159-code cohort, 336 cached profiles and access-block record. `trial_profile_catalog --cached-only` installs/rechecks cached evidence without requesting missing profiles. The cohort must not silently expand on resume.
- `2026-09-14_official_national`: official sheet/checkpoint evidence, including explicit access-challenge failures. `trial_official_archive --cached-only` performs offline replay. `--retry-access-failures` is only for a later run after normal access has been restored; original challenge payloads remain archived.
- `2026-09-14_reconciliation.json`, `2026-09-14_reconciliation_replay.json`, `2026-09-14_original_evidence_audit.json`.

New modules: `trial_profile_catalog`, `trial_official_archive`, `trial_data_reconcile`, `trial_coverage_report`, `trial_source_requests`. Run with `PYTHONPATH=RacingEngine` from the isolated checkout and the existing BettingEngine virtualenv. Every writing CLI requires separate review and registry paths and rejects the production database. Finish downloads, validate profiles, run reconciliation and coverage reporting, then repeat preservation/idempotence checks before requesting sign-off. No calculations, merge or deployment until the owner reviews the completed scope.

The committed `reports/fitness_trials/national_data_completion_2026-09-14.json` is a scoped coverage checkpoint, not a completion certificate. Raw source payloads, databases and owner information are excluded from git. Backups: `data/trials_review/backups/trials_before_national_completion_2026-09-14.sqlite`, `trials_national_checkpoint_2026-09-14.sqlite` and `trials_national_sources_2026-09-14.tar.gz`. The latest normalized view additionally clears a previously accepted identity when new evidence introduces a conflict; originals are preserved.

The review UI has not been changed in this pass and is still the earlier recent-window snapshot.
