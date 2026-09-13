# Trials coverage correction — 13 September 2026

## Why this work was necessary

The owner checked Autumn Glow and Sheza Alibi on the local review page and
correctly identified missing trials. The earlier "download pass finished"
wording was too narrow: the horse cohort came only from one available month of
NSW trial meetings. It excluded horses whose trials were earlier, and Victorian
jumpouts were not collected at all. Successful replay of that cohort did not
establish coverage of the requested two-month window.

Do not repeat that completeness claim. This session expanded actual collection
and made the omissions reproducible regression cases.

## Results now present

- Autumn Glow: Royal Randwick, 20 July 2026, heat 1, 900m, third of seven,
  6.42L; Royal Randwick, 31 July, heat 1, 1000m, third, 2.53L.
- The July 31 API has eight listed rows including an unresolved status code,
  so its starter count stays null in the immutable source event. The independent
  Racing NSW complete result and verified horse history both establish seven
  starters. The review page shows that corroboration and links both sources.
- Sheza Alibi: Pakenham jumpout, 28 July, heat 1, 800m, second of six;
  Pakenham Synthetic jumpout, 11 August, heat 1, 1000m, first of six.
- Racing.com editorial reports independently confirm the two jumpout dates.
  Venue labels come from the structured source; do not infer surface solely
  from "Synthetic" in a venue name. The source condition text can differ.

The new collector queried every completed day from 13 July–12 September 2026.
It found 160 NSW/VIC/ACT trial/jumpout calendar IDs and retrieved runner data
for 147. All 8,909 returned runner observations are stored, including unresolved
ones: NSW 3,303; VIC 5,561; ACT 45. Event types: 5,108 jumpout observations and
3,801 official-trial observations. These are source observations, not 8,909
new canonical events or unique horses.

1,641 accepted events were added; the database now has 3,280 fitness events.
The original 1,639 events and all original quarantine rows are unchanged.
Autumn Glow's current official full history also added 13 profile observations.

## Remaining source and identity gaps

Thirteen calendar IDs returned no runner results. Some are placeholder IDs
sharing a venue/date with a populated ID. They are retained individually in the
coverage report and must not be silently called cancelled or complete.

Source observation review statuses: 5,291 unmatched-registry observations,
428 unresolved result codes, 32 conflicting heat clocks and one known-horse
observation with an ambiguous source heat number. The remaining observations
are 1,641 new accepted results and 1,516 matching an existing event's finishing
position and distance. Original held identity/LP records remain separate.

Unknown numeric source codes such as 104/109 are not finishing positions. When
any listed runner has an unknown code, the API-only starter count remains null.
Empty placeholder heats are retained in source archives. Duplicate populated
heat numbers retain all runner observations and block affected event promotion.

This is not a complete national backfill and is not the finished fitness model.
The next work is identity resolution for newly collected horses, source-gap
reconciliation and expansion beyond these states/window, before model use.

## Reproduce and inspect

Code: `racing_engine.trial_calendar_expansion`. It uses the existing public
Racing.com query integration with one query per day. The broad multi-state
calendar query was rejected during investigation because it returned only VIC
and a shortened date range. Daily query dates are checked, archived, and verified
again on replay. Four bounded workers fetch; one writer installs data.

```sh
PYTHONPATH=RacingEngine python3 -m racing_engine.trial_calendar_expansion \
  --database /absolute/path/to/trials_review.sqlite \
  --registry-database /absolute/path/to/racing_engine.sqlite \
  --archive /absolute/path/to/raw \
  --run-directory /absolute/path/to/calendar_expansion_run \
  --from-date 2026-07-13 --to-date 2026-09-12
```

Same run directory replays archived sources. A new run directory refreshes
network sources. Reports distinguish run insertions from total stored data.
`trial_calendar_observations` is append-only and retains nullable horse links.
New accepted events are written only for linked, placed runners without an
existing same-horse/date/venue/heat/type event. Existing results are never
rewritten; divergent places/distances are held.

Persistent data root: `RacingEngine/data/trials_review/nsw_archive/`.
Run: `runs/2026-09-13_calendar_expansion/`; includes every daily calendar,
meeting archive manifest, summary, independent audit and the Autumn Glow
Racing NSW cross-check. `raw/` and the database are local/gitignored.

Backups in `RacingEngine/data/trials_review/backups/`:
`nsw_trials_before_calendar_expansion_2026-09-13.sqlite`,
`trials_after_calendar_expansion_2026-09-13.sqlite`, and
`trials_calendar_expansion_sources_2026-09-13.tar.gz`.
These are local machine backups, not remote recovery copies.

## Review page and validation

`racing_engine.trial_review_page` builds a read-only static snapshot for eight
selected horses, currently 20 records. It labels trials versus jumpouts,
source links, starter-count limitations and held results. Generate with
`--database /absolute/path/to/trials_review.sqlite --output /path/to/site`.
Serve only that output directory with Python's HTTP server.

Current preview: `http://localhost:8765`, LAN `http://192.168.1.106:8765`.
The server serves `/private/tmp/betmate-trial-review-site`, not repository data.
The temporary server must be restarted after it exits; regenerate the snapshot
after further database imports.

59 focused tests passed. Independent extraction matched all 8,909 archived
runner-ID/hash/name/date/heat/status tuples to stored observations. Every daily
archive hash was verified. All original events/quarantine rows matched the
pre-expansion backup. Final replay inserted zero observations and zero events;
SQLite integrity passed with zero foreign-key violations. Browser checks
confirmed both target horses' two records, Autumn Glow's corroborated field
sizes, search filtering, and no mobile horizontal overflow. Desktop inspected.

PR #14 stays OPEN for merge review; no production changes or merge authorised.
