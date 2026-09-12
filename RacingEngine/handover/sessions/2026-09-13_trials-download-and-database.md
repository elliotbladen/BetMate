# Trials download and database handover — 13 September 2026

PR #14 remains open. The owner asked to continue downloading and installing
trial data after the first-meeting pipeline. The existing ten-step foundation
is now connected to a real NSW source and a separate durable review database.

Completed: downloaded every one of the 40 NSW trial meeting links on the current
calendar (13 August–11 September), reconciled 39 results meetings / 214 heats,
and explicitly recorded one abandoned meeting. All 1,783 listed observations
are in the database: 450 linked events, 1,190 identity-review records and 143
quality/exclusion records (142 scratches plus one unresolved LP code).

The original Rosehill-only review data is preserved. The aggregate database is
`RacingEngine/data/trials_review/nsw_archive/trials_review.sqlite` in the shared
checkout. Raw downloads, immutable reports and separate local backups also
exist under `data/trials_review/`; none depend on the temporary code worktree.
No production racing data was written. Raw pages are gitignored and may contain
signed replay URLs, so do not commit them.

Validation: 37 focused tests; independent source-to-database identity matching
for all 1,783 rows; SQLite integrity and foreign-key checks; full replay creates
no duplicates and preserves the stored-row fingerprint. The initial batch's
seven failures are retained in its reports; archived replay resolved the source
format gaps and correctly classified the abandoned meeting.

Next: resolve the 1,190 preserved observations against verified horse identities,
then extend historical and jurisdictional coverage. Unknown horses must not be
silently invented or mistaken for missing downloads. The current one-month NSW
archive is not the full three-year trial backfill. No fitness modelling or rating
promotion has occurred.

See `../../docs/fitness_trials_meeting_pipeline.md` for commands, evidence,
backup locations and scope. PR #14 must remain open until the remaining work is
reviewed; previous approvals to merge unrelated PRs do not authorise it.
