# Flemington and Rosehill — 12 September 2026

Collected the two completed meetings and rated their 219 finishers using the
existing accepted `form-first-v2.0` model. This change contains data and review
outputs only; no engine, website, model formula or production configuration
changes. The owner approved this release on 15 September 2026; application evidence is
recorded in `release_2026-09-15.json`.

## Collected data

| Meeting | Races | Finishers | Scratches | DNF | Individual clocks | Detailed sectionals |
|---|---:|---:|---:|---:|---:|---:|
| Flemington | 10 | 118 | 14 | 0 | 118 | 889 |
| Rosehill | 10 | 101 | 32 | 1 | 101 | 719 |

All 20 races have official clocks, race conditions, distances, rail positions,
weights and result-card metadata. All 219 finishers have individual clocks and
sectionals. All 20 official stewards reports were also collected. Source JSON,
PDFs and detailed sectional responses remain in the local research archive;
`manifest.json` records their paths and SHA-256 hashes.

The result feed's general importer labels every entry other than a scratch as
finished. The official Rosehill Race 4 PDF explicitly records **Bold Mac (#1)
as Did Not Finish**. This collection corrects that specific row to `dnf`, with
no finishing position, beaten margin or finishing clock. It receives no rating.
No general importer change is included in this data task.

## Top 10 runs — accepted model

These are weight-adjusted achieved run figures, not finishing-order predictions,
current horse-ability estimates, fair odds or a model promotion.

| Rank | Horse | Meeting / race | Finish | Accepted rating |
|---:|---|---|---:|---:|
| 1 | Sheza Alibi | Flemington R8 | 1 | 114.24 |
| 2 | Another Wil | Flemington R8 | 3 | 113.45 |
| 3 | Autumn Boy | Flemington R8 | 2 | 113.15 |
| 4 | Sir Delius | Flemington R8 | 4 | 111.95 |
| 5 | Desert Lightning | Flemington R7 | 6 | 110.48 |
| 6 | Half Yours | Flemington R8 | 6 | 110.45 |
| 7 | Mr Brightside | Flemington R8 | 7 | 109.75 |
| 8 | Hedged | Flemington R7 | 2 | 109.57 |
| 9 | Lazzura | Rosehill R7 | 3 | 109.07 |
| 10 | Light Infantry Man | Flemington R8 | 8 | 108.75 |

`rated_runs.csv` contains all 219 accepted ratings and explicitly labelled
`achieved-run-v2.10-young-wfa-shadow` comparisons, sectional totals and evidence
availability. `results.csv` contains all 266 entries, including scratches and DNF.
A winner's source margin is its winning margin; it is zero lengths beaten in
the accepted rating calculation. Relative weights can place a beaten runner
above a horse that finished ahead of it.

## Rating and availability limits

The accepted model uses collateral form, margins, class and carried weight. It
does **not** use the clock or sectionals to set the race level. Collecting those
inputs does not turn this into a speed-based rating model. The stored promotion
policy still identifies this model as accepted.

Shadow ratings are comparison-only. WFA/profile and historical time-par
availability are recorded independently of raw timing coverage; a complete
clock does not imply an eligible historical par. All 219 shadow WFA profiles remain unlinked; 26 Flemington runs lack a usable
historical clock comparison. All 219 have sectional energy evidence. No missing evidence was
invented. The next-start column is a research run-based carry-forward proxy:
accepted plus 15% of the signed shadow difference for three-year-old Group/Listed
winners, accepted unchanged outside that validated cohort. It is not a complete
current-ability or race-day pricing model.

Append-only snapshots preserve accepted and shadow figures, the next-start
proxy, model versions, evidence availability and actual collection timestamp.
They are collected after the meeting and are not backdated to pretend the data
were available on race day. Historical prospective snapshots remain intact.
No prices were fabricated from the post-race results.

## Validation

- Calendar and each result payload agree on meeting ID, date, venue and state;
  each card has 10 races and one winner per race.
- Rosehill PDF runner numbers and normalized identities match the independent
  result card for every finisher in every race, accounting for the confirmed DNF.
- Flemington's detailed source matched all 118 finishers, with no unmatched
  runners across its 10 races.
- Every finisher's detailed split sum reconciles to its individual clock within
  0.15 seconds; observed residuals are 0.00 seconds for every finisher, as
  recorded in `manifest.json`.
- No September 12 race or runner clock was quarantined by the existing checks.
- All 29,541 historical accepted rating rows are byte-for-byte identical in
  their stored column values. Targeted SQLite integrity checks passed on the
  ten source/rating tables recorded in `validation.json`. The full 17 GB
  database check was stopped after six minutes; it is not claimed as passed.
- The date-scoped SQL package was replayed on a fresh baseline clone; its rows
  match the completed review database, foreign-key checks pass, and a second
  application is rejected rather than overwriting existing data.
- The 14 focused report-date, Victorian-sectional, V2 rating and young-WFA tests
  passed. No UI checks apply to this data-only change.

## Approved release — 15 September 2026

The owner approved merging PR #33 and applying its reviewed data, retaining
`form-first-v2.0`. The Dan-aligned experiment is ended; its unmerged default
switch is excluded. PR #14 stays open and is outside this release.

The hash-verified package in `manifest.json` adds only these two meetings.
It preserves all 29,541 historical accepted ratings and freezes the 219 new
accepted/shadow snapshots at their actual collection time. Before application,
a fresh compact copy of the current canonical database passed replay, full
integrity, foreign-key, rating/CSV equality and duplicate-insert rejection checks.
The compact copy excludes data only from the seed builder's existing two legacy
exclusions (`run_performances`, `horse_rating_states`); the canonical database
retains those tables and their contents.

The canonical database is `RacingEngine/data/racing_engine.sqlite`.
`release_2026-09-15.json` records the backup and verified application results.
The cross-machine seed now contains the same retained tables and weekend data;
restore verification is recorded in that release report. No ratings were
recalculated, no model formula changed, and no pricing or UI release is included.

All 14 focused parser/rating tests passed during release validation. The report
date tests require the existing RacingEngine virtual environment (`pypdf` is
not installed in the system Python). The original full 17 GB integrity check
remains unclaimed; the fresh compact release database passed its full check.
