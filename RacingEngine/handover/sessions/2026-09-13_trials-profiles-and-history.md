# Trials profile and history import — 13 September 2026

## Delivered

Continued PR #14 in its isolated checkout and merged current main into the branch.
PR #14 remains open. No production release or rating/pricing change was made.

Downloaded all 1,300 official Racing NSW All Form profiles for the horse codes
in the existing calendar dataset. Verified and installed 1,299 profiles, adding
959 previously absent horses to the local review registry. One source identity
remains unresolved: the 14 August Randwick heat 9 result says
ANOTHERBADDECISION, while the linked horse profile says WADDLES. The same
provider code and matching trial history support further investigation, but no
alias or name change was assumed. Both direct profile contexts were checked.

The verified profiles yielded 6,408 trial-history observations dated
18 September 2023–11 September 2026, within the requested three-year window.
4,754 predate the original calendar window. There are 819 distinct linked
meeting pages. These are cohort histories published by Racing NSW and may
include interstate trials; they are not complete NSW or national coverage.

Replaying the original 40 meetings resolved 1,189 of 1,190 identity-review
records and installed 1,189 additional accepted events. Current accepted event
count is 1,639. The original 450 events and all original quarantine records were
preserved unchanged. Outstanding reviews: one identity discrepancy, 142
non-starters and one unresolved LP status. The old identity-review rows are
historical evidence, not 1,190 outstanding problems: use the resolution ledger.

## Data and recovery

Persistent review root:
`RacingEngine/data/trials_review/nsw_archive/`

- `trials_review.sqlite`: review database, separate from the production registry.
- `raw/racing_nsw_profiles/`: all downloaded profiles, content-addressed.
- `runs/2026-09-13_profiles/`: fixed cohort plan and resumable profile checkpoints.
- `runs/2026-09-13_profile_resolutions/`: full meeting replay and resolution audit.
- `runs/2026-09-13_resolved_replay/`: final idempotence replay.
- `runs/2026-09-13_profile_source_audit.json`: independent extraction results.
- `runs/2026-09-13_profile_source_audit.py`: local audit reproduction script
  (uses the existing environment's BeautifulSoup package).
- `runs/2026-09-13_profile_history_meeting_plan.json`: actual source meeting URLs
  and horse/date/heat/finish anchors for the next reconciliation stage.

The earlier datasets and backups remain. A pre-profile SQLite backup is
`RacingEngine/data/trials_review/backups/nsw_trials_before_profiles_2026-09-13.sqlite`.
Post-import database and source/report backups use the `nsw_trials_profiles_2026-09-13`
and `nsw_trial_profiles_sources_and_reports_2026-09-13` filenames in that directory.
These backups are on this machine. Raw data and databases are gitignored; raw
pages can include owner details and signed replay links and must not be committed.

## Implementation and checks

`trial_profiles` provides four bounded download workers, a global request-start
throttle, one database writer, archived replay, strict identity/result checks,
and immutable profile/history evidence. Written Failed to Finish and Lost Rider
results are explicitly recognised. Exact registry/provider conflicts and name
mismatches remain review failures. A profile's historical trial rows must match
all known calendar anchors before it can establish identity.

`trial_profile_reconcile` validates archived hashes and installed observations,
replays complete meetings, verifies original records and records resolutions.
The identity linker sets newly resolved evidence availability no earlier than
profile collection. An original event is never rewritten by replay.

53 focused synthetic tests passed. Independent BeautifulSoup extraction exactly
matched all 6,408 historical source observations to the database. SQLite
integrity passed with no foreign-key violations. The final 40-meeting replay
showed zero insertions and 1,639 unchanged accepted events; its summary is
stored in the run directory above. No UI was changed.

## Next work

Download and reconcile the 819 linked full-meeting sources before promoting
older profile observations to accepted fitness events. The interactive meeting
layout differs from the calendar results layout: it lacks the advertised
starter total and uses RATime. It needs an explicit parser contract backed by
profile anchors, rather than silently relaxing the current meeting parser.

Investigate the held name discrepancy using further official identity evidence.
Continue VIC/ACT coverage and the remaining fitness preparation/modelling steps
from the ten-step plan. This import completes the current profile download and
review-database installation pass; it does not finish the entire trials engine.

Commands: `RacingEngine/docs/fitness_trials_meeting_pipeline.md`.
Sanitised results: `RacingEngine/reports/fitness_trials/nsw_profile_history_import_2026-09-13.json`.
