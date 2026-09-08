# NSW post-stewards report importer

Date: 8 September 2026

## Trigger

Follow-on from importing the 5 Sep 2026 stewards reports. The existing
`racing_engine.steward_reports` (racing.com authorised form feed) only carries
**Victorian** reports — historically 1,097 rows, 0 NSW. Randwick 5 Sep imported
clean but with 0 reports. User pointed at the Racing NSW results page, where the
stewards report is the "Post Stewards" PDF hosted by Racing Australia.

## Work done

### VIC (this session, before the NSW build)
- `python -m racing_engine.steward_reports --state VIC --date 2026-09-05` →
  Sandown Hillside R1–R8 (8 reports, 38 events). R9/R10 had no `htmlCode` in the
  feed; a later re-run (clear the `steward_report_ingestions` row) will pick them
  up when RV publishes them.

### NSW — new importer
- **`racing_engine/post_stewards.py`** — new module.
  - Source: `https://racingaustralia.horse/PostStewardsReports/{DDMMYYYY}{CODE}.pdf`.
    Verified codes: Randwick `RAND`, Rosehill `RHIL` (not `ROSE` for this feed).
    `VENUE_CODES` also carries best-guess codes for the other NSW tracks, first
    candidate that returns a `%PDF` wins.
  - Downloads + archives the unmodified PDF to `data/raw/post_stewards/{date}/{slug}.pdf`.
  - `parse_races()` — `pypdf` text, fold `– —` → `-` and `’ ‘` → `'`, strip the
    running `20260905RR n` page stamp, split on `RACE n: <name> <dist>m[:]`
    (trailing colon optional — R8 Concorde Stakes had none), stop at `GENERAL:`.
    Meeting header + `GENERAL`/`SUMMARY` trailer are **not** stored (matches the
    per-race scope of the VIC path). Per-horse paragraphs split on a
    `<Name> - ` boundary preceded by `.`/`)`.
  - Classification **reuses `racing_engine.stewards.classify_report`** unchanged,
    with the race's `runner_results` names — so identical wording gives identical
    category/severity/trip across NSW and VIC.
  - Stored under source `racing-australia-post-stewards`, parser_version
    `stewards-rule-v1.1-map-position+post-stewards-pdf-v1`. Independent of the
    VIC rows.
  - CLI mirrors `steward_reports`: `--date`, `--track`, `--dry-run`; discovers
    NSW meetings from `race_results` not already `complete`; a meeting whose PDF
    is not published yet records an `error` check and retries next run.
- **`tests/test_post_stewards.py`** — 8 unittest cases (header w/o colon,
  supplementary/GENERAL exclusion, page-stamp strip at a paragraph boundary,
  dash/curly-apostrophe split + attribution, punctuation fold, empty input,
  venue codes). All pass. `test_storage` + `test_rnsw_report_date` still pass.
- **README** — new paragraph under "Official steward reports".

### Result — Randwick 5 Sep 2026
`python -m racing_engine.post_stewards --date 2026-09-05` → **10 reports, 65 events**.
8 human-review flags: severe held-up (Brooklyn Lights R2, Tequila Baby + Scillato
R3, Unleeshing R5, Striking Alibi R6, Headwall R8), severe interference (Signor
Tortoni R8 — the stewards' inquiry incident), material vet (Exit Fee R5 — late
scratching, lame in front, vet clearance required). DB `quick_check` = ok.

## Known gaps / not done

- **`stewards.RULES` has no `cardiac`/`arrhythmia` pattern** — Randwick R10
  Fortune ("cardiac arrhythmia … 2nd occasion, AR88B(2)(b)") produced no
  `vet_material` event. Same gap affects the VIC path. Add `cardiac|arrhythmia`
  (and probably `tie[- ]?up`) to the `vet_material` rule, bump the rule version,
  and re-run both importers — but only after eyeballing historical matches.
- **`GENERAL` section not captured** — swabs, tactics-notified, change-of-tactics,
  bleeders/cardiac register. Tactics-notified is genuinely new signal (not in the
  per-race text). Deliberately out of scope for v1; revisit if a tactics feature
  is wanted.
- Sandown R9 (Gr.3) + R10 stewards reports still pending in the RV feed.
- No scheduled task. If NSW Saturday metro stewards should refresh automatically,
  add `post_stewards --date <sat>` to the weekend pipeline (runs after the RNSW
  results import, since it needs `race_results` for the runner lists).
- Stale `racing-com-stewards-authorised / randwick / complete` ingestion row left
  in place — it correctly records that the racing.com feed was checked and had no
  NSW report; harmless, independent key from the new source.
