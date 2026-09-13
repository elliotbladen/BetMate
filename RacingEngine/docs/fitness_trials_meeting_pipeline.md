# Trial meeting ingestion and first NSW archive

Date: 13 September 2026. PR #14 remains open; no ratings or price inputs have
been promoted. This completes the first real meeting pipeline and a bounded
NSW calendar download, not the planned three-year or national backfill.

## What now works

`racing_engine.trial_meeting` verifies a Racing NSW results page against the
requested date, venue, trial category, heat index and runner-link meeting keys.
It reads only the result tables. Interim results, wrong meetings, malformed
rows and unexplained count mismatches stop ingestion before any event writes.
An explicitly abandoned meeting is retained as a zero-event outcome.

The source's advertised starter count excludes scratched rows, even though the
result tables include them. Emergency labels such as `13e` retain their source
label and use numeric runner 13. Source result code `LP` is preserved for review;
we do not infer completed preparation work from it. A zero barrier is missing,
not a real gate. The official heat clock belongs to its winner; other runners
retain the heat context without receiving an invented individual time.

Identity matching uses the existing horse registry. Duplicate provider IDs,
provider/name disagreements, ambiguous matches and unknown horses are held for
review. No new durable horse is invented from an unverified name. Dangling
aliases cannot become foreign-key references. Every runner is saved either as
a linked event, an identity review record, or a quality/exclusion record.

Writes for a meeting are transactional. Identical replays keep original events;
changed event values go to review instead of overwriting them. Quarantine writes
also participate in rollback. Raw page hashes and original collection times are
retained. `effective_at` is the collection time, not the old event date: these
retrospective downloads are not historically available model inputs.

`racing_engine.trial_batch` discovers only trial result links actually present
on the official calendar. It deduplicates links, records excluded jurisdictions,
waits one second between meeting downloads, and writes one immutable report per
meeting. A failed meeting is visible in the final coverage report. Archived
batches can be replayed offline with payload-hash verification.

## Actual download and database result

Source: [Racing NSW results calendar](https://mdata.racingnsw.com.au/FreeFields/Calendar_Results.aspx).
The downloaded calendar listed 40 NSW trial meetings from 13 August through
11 September 2026. Two ACT meetings are explicitly recorded as outside this
NSW parser's current scope.

| Evidence | Result |
|---|---:|
| NSW source pages downloaded and accounted for | 40 |
| Meetings with results | 39 |
| Abandoned meetings | 1 (Wellington, 13 August) |
| Heats | 214 |
| Advertised starters | 1,641 |
| All listed runner observations | 1,783 |
| Linked events in `fitness_events` | 450 |
| Preserved in `fitness_identity_quarantine` | 1,190 |
| Scratches/non-starters held separately | 142 |
| Unresolved `LP` result held separately | 1 |
| Unexplained missing observations | 0 |

Thus the full source record set is installed, but only 450 observations currently
have accepted horse-registry links. The 1,190 unmatched observations are stored
in the database and raw archive; they are not deleted or counted as linked
fitness events. The next substantive task is verified provider identity linking
for these horses, followed by broader historical/source coverage.

The initial batch stopped seven meetings. Six parser gaps were repaired from
archived evidence (emergency runner labels and the LP result); the seventh was
the abandoned meeting. A replay reconciled the entire calendar without further
network calls. The original failed reports remain available as historical evidence.

## Durable local locations

Relative to the shared BetMate checkout:

- Database: `RacingEngine/data/trials_review/nsw_archive/trials_review.sqlite`.
- Source pages and collection metadata: `RacingEngine/data/trials_review/nsw_archive/raw/`.
- Original, reconciled and replay reports: `RacingEngine/data/trials_review/nsw_archive/runs/`.
- Database backup: `RacingEngine/data/trials_review/backups/nsw_trials_2026-09-13.sqlite`.
- Source/report backup: `RacingEngine/data/trials_review/backups/nsw_trial_sources_and_reports_2026-09-13.tar.gz`.

These files are in the persistent project directory, not a temporary worktree.
They are local and gitignored; this does not establish an off-machine backup.
Do not commit raw source pages: they may contain rotating signed replay URLs.
The earlier Rosehill-only review database is also preserved separately.

The main `RacingEngine/data/racing_engine.sqlite` was opened read-only to copy
horse and alias identities. It was not modified. The CLI refuses using that
file, its hard links, the registry file or a database containing race results
as the review output.

## Running or replaying

Run from the repository root with the PR #14 code checked out. Choose a new run
directory each time so reports cannot be overwritten. The database must be a
separate review database. Use absolute paths when working in an isolated checkout.

```sh
PYTHONPATH=RacingEngine python3 -m racing_engine.trial_batch \
  --database /absolute/path/to/trials_review.sqlite \
  --registry-database /absolute/path/to/racing_engine.sqlite \
  --archive /absolute/path/to/trial_raw_archive \
  --run-directory /absolute/path/to/new_run_directory
```

Add `--replay-directory /absolute/path/to/previous_run_directory` to reuse that
run's exact plan and archived pages without downloading. Failed downloads with
no saved payload remain explicit failures and need a fresh network run.

For one meeting use `racing_engine.trial_meeting` with `--url`, `--date`,
`--track`, `--database`, `--registry-database`, `--archive` and `--report`.
Archived HTML replay additionally needs `--html` and its original `--collected-at`.
The batch reports per-run insertions; total stored events are not the same as
new insertions on a replay.

## Verification and limits

- 37 focused tests pass: meeting/source identity, changed columns, truncated
  rows, interim/abandoned meetings, scratches, emergency numbers, source-code
  handling, duplicate ingestion, provider conflicts, transaction rollback,
  calendar deduplication, archived replay, corrupted payloads and output guards.
- An independent BeautifulSoup extraction of source heat/provider/name tuples
  exactly matched all 1,783 stored records across the three event/review tables.
- SQLite integrity check passed and foreign-key violations were zero.
- Replaying all 40 meetings after reconciliation inserted zero events. The
  stored event and quarantine rows were byte-for-byte identical by SHA-256.

This is NSW calendar coverage for one available month. VIC, ACT and the older
three-year archive are not claimed complete. No fitness model, live scheduler,
rating promotion or production release is included. PR #14 remains open for
continued work and owner review.

## Horse profiles and historical trial observations

The follow-up collector is `racing_engine.trial_profiles`. Its cohort is the
unique Racing NSW horse codes in accepted events and identity quarantine from
the saved calendar import. This is a cohort history download, not a complete
national archive. It follows the official All Form endpoint and stores trials
inside the requested date window. Race starts are excluded.

Each profile must agree with the archived result name, have a valid birth date,
and corroborate the horse's known trial dates, heats, field sizes and finishes.
Provider IDs and existing birth-date evidence must not conflict. A mismatch is
held for review. The collector does not invent aliases to force a match.

```sh
PYTHONPATH=RacingEngine python3 -m racing_engine.trial_profiles \
  --database /absolute/path/to/trials_review.sqlite \
  --registry-database /absolute/path/to/racing_engine.sqlite \
  --archive /absolute/path/to/trial_raw_archive \
  --run-directory /absolute/path/to/profile_run \
  --from-date 2023-09-13 --to-date 2026-09-12
```

Unlike meeting runs, a profile run is resumable in the same directory. Its plan
fixes the database, horse cohort and date window. Reports are atomic checkpoints;
raw pages are content-addressed. Four download workers share a request-start
throttle, and only the main thread writes SQLite. Failed downloaded pages replay
from the archive; failed network requests retry on the next invocation. Add
`--recheck` to revalidate all saved profiles and replay their database writes.
No raw profiles, owner tables or signed replay URLs belong in Git or PR text.

The review database adds three append-only evidence tables:

- `trial_profile_evidence`: verified identity, birth date and archived source hash.
- `trial_history_observations`: source-dated trial history and the actual linked
  full-meeting URL. These observations are not accepted `fitness_events`.
- `trial_identity_resolutions`: original quarantine key, resolved horse and
  profile evidence. Original quarantine records remain intact.

After collecting profiles, verify their archived hashes and source-to-database
history, then replay the original complete meetings to accept resolved runners:

```sh
PYTHONPATH=RacingEngine python3 -m racing_engine.trial_profile_reconcile \
  --database /absolute/path/to/trials_review.sqlite \
  --registry-database /absolute/path/to/racing_engine.sqlite \
  --profile-directory /absolute/path/to/profile_run \
  --meeting-directory /absolute/path/to/previous_reconciled_meeting_run \
  --run-directory /absolute/path/to/new_resolution_run \
  --archive /absolute/path/to/trial_raw_archive
```

The resolution audit distinguishes historical quarantine rows from outstanding
reviews. Reconciliation verifies that every original event and quarantine row
remains unchanged. Newly resolved events become effective no earlier than the
profile observation that established their identity. Repeating reconciliation
in a new run directory must insert no additional events or resolutions.

Older profile observations still require full-meeting reconciliation before
promotion into accepted events or fitness modelling. Their presence in the
review database does not establish complete meeting coverage, historical
availability, or readiness for production.

The 13 September follow-up downloaded all 1,300 cohort profiles, verified 1,299,
and installed 6,408 history observations (4,754 older than the calendar window).
It resolved 1,189 identity-review rows, bringing accepted events to 1,639.
The ANOTHERBADDECISION/WADDLES name discrepancy remains one outstanding identity
review. See `handover/sessions/2026-09-13_trials-profiles-and-history.md` for the
current counts, evidence locations and next reconciliation stage.

## Coverage correction after the owner's spot check

The original cohort missed Autumn Glow's July trials and Sheza Alibi's Victorian
jumpouts. The follow-up `trial_calendar_expansion` queries each completed day
for NSW/VIC/ACT rather than deriving the horse population from one month's
NSW results. It now stores 8,909 source observations from 147 populated calendar
IDs in the 13 July–12 September window, with thirteen empty IDs explicitly held
as source gaps. The database has 3,280 accepted events. Unmatched observations
and unknown source result codes remain review items, not fabricated identities
or finishing positions. This is still not complete national coverage.

Use `trial_review_page --database PATH --output DIRECTORY` to generate the local
source-linked spot check. Full commands, regression evidence and remaining work:
`handover/sessions/2026-09-13_trials-coverage-correction.md`.
