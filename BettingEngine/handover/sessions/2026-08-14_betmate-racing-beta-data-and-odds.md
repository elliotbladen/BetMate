# 2026-08-14 — BetMate Racing beta: live racecards and odds decision

## Product scope agreed

- Keep the product under **BetMate** (not a separate RaceMate brand).
- First-year racing scope is **Saturday metropolitan thoroughbreds only** in
  NSW and Victoria.
- RacingEngine is currently an approved **internal, non-commercial BetMate
  research project**. It is not a customer data product or public raw-data
  feed. The longer-term product is the
  serious-punter workbench described in
  `handover/sessions/2026-08-14_betmate-racing-race-digital-twin.md`.

## What is live on BetMate

- The main sport strip has a Racing menu beside NRL, AFL and Football, with
  NSW Racing and Victoria Racing choices.
- `/racing` has compact expandable race cards. Opening a card shows the actual
  runner list, jockey, trainer, barrier, weight, form and scratch status.
- The live card source is FormFav. The deployed server route is
  `BetMate/app/api/racing/card/route.ts`; the page is
  `BetMate/app/racing/page.tsx`.
- FormFav key setup:
  - Local key is stored at `BettingEngine/.env.formfav.local` (never commit or
    print it).
  - Vercel uses `FORMFAV_API_KEY` in **Production and Preview**.
  - A fresh deployment was pushed in commit `21fba3b`; production then
    returned Rosehill's full card successfully. The earlier empty UI was a
    Vercel key/deployment issue, now resolved.
- Current production card response has real entries such as runner name,
  jockey, trainer, barrier, weight, career form and scratches. FormFav does
  **not** provide bookmaker odds or BetMate fair odds.

## RacingEngine

- `../RacingEngine` is a sibling Python project, intentionally separate from
  `BettingEngine`.
- It imports authorised FormFav racecards into local SQLite and archives raw
  payloads. Core files:
  - `RacingEngine/racing_engine/formfav.py`
  - `RacingEngine/racing_engine/import_saturday.py`
  - `RacingEngine/racing_engine/storage.py`
- Validated for 2026-08-15:
  - NSW Rosehill: 10 races, 140 runners
  - VIC Caulfield: 9 races, 126 runners
- The database and raw source data remain local/ignored. It has no fair-price
  model yet; never label a market price as a BetMate true/fair price.

## PunterEdge research and decision

The desired final UI is an AFL/NRL-style odds matrix:

- compact runner row: horse, jockey, trainer, barrier, weight and form;
- 6–8 bookmaker **win** prices across each runner, with best price highlighted
  and source timestamp;
- later, a separate BetMate fair-price/edge column supplied by RacingEngine.

PunterEdge does return runner-level bookmaker arrays (`key`, `win_price`,
`place_price`, `last_update`, `age_seconds`) from
`GET /api/v1/racing/next-to-go`. It is useful for near-jump odds monitoring,
price snapshots, best-price comparisons, alerts and Betfair back/lay work.

However, the current key/feed must **not** be treated as a full Saturday
racecard odds provider:

- its documented `events` look-ahead is capped at 24 hours;
- on the live test it returned only seven imminent races;
- the observed runner sample had only one bookmaker (`pointsbetau`);
- it therefore cannot reliably populate all NSW/VIC Saturday races with six to
  eight bookmaker columns early in the week.

Do not add a fake or predominantly empty odds grid. Need either (1) a
PunterEdge plan/endpoint that guarantees full upcoming-meeting coverage and
the desired bookmaker depth, or (2) a different properly licensed full
meeting odds provider. Once one is confirmed, add a server-only adapter with
the Vercel secret `PUNTERSEDGE_API_KEY` (or the replacement provider key),
match runners by canonical track/race/runner number, and render the grid above.

Relevant provider docs:
https://puntersedge.online/developers

## Recent BetMate commits

- `7edb2b1` — racing expandable cards
- `0e9ee2d` — RacingEngine scaffold
- `c3349fd` / `295c113` / `b5ed0c8` / `d67d72c` — FormFav card route and beta
  feed corrections
- `21fba3b` — empty production deployment to load corrected FormFav Vercel env

## Next session

1. Confirm a licensed odds feed capable of full Saturday cards plus 6–8 books.
2. Add provider key only as a Vercel secret; do not expose it to the browser.
3. Build the odds adapter and compact runner-by-bookmaker matrix.
4. Build RacingEngine performance ratings and fair odds separately, then add
   a clearly labelled fair-price/edge column.

## 2026-08-15 — RacingEngine V1 foundation implemented

- Added canonical SQLite tables for `race_results`, `runner_results`,
  `runner_sectionals`, `rating_snapshots` and `fair_prices`.
- Added safe CSV templates and the validated import entry point:
  `python3 -m racing_engine.results_import --results ... --sectionals ... --source ...`.
  Each row preserves an authorised source label and URL; no proprietary-source
  scraper was added.
- Added `base-lengths-v0.1`: a deliberately provisional, reproducible
  beaten-length rating update. It shrinks lightly raced horses to neutral and
  makes field-normalised shadow fair odds. It explicitly does **not** yet
  apply track pars, class, weight, barrier or sectional adjustment.
- Verified with four unit tests: cards, canonical CSV imports, result/sectional
  storage, and a two-horse rating/fair-book calculation.
- FormFav only permits seven days of historical card access. On 2026-08-15,
  2026-08-01 was rejected as too old. Backfilled 2026-08-08 Randwick (10 races,
  119 runners); the Victorian meeting did not match the metro-track allowlist.
  Existing 2026-08-15 card data remains Rosehill (10 races) and Caulfield (9).
- This historical snapshot is superseded by the approved data-access update
  below. Do not publish the shadow model as a meaningful price until the data
  history is materially larger and calibration has been completed.

## 2026-08-15 — approved research data access

- User confirmed verbal approval from **Racing NSW** and **Racing Victoria**
  for non-commercial research use. Keep the project internal, retain source
  provenance, and do not redistribute raw feeds or represent this as a
  commercial/public licence.
- Racing NSW official CSV results importer implemented and used for 2026-08-01
  Rosehill (10 races, 109 finishers) and 2026-08-08 Randwick (10 races, 100
  finishers). Both official sectional PDFs are archived.
- Racing.com/RV importer completed after the user confirmed Racing Victoria
  said to scrape its public form page. `RacingEngine/racing_engine/racing_com.py`
  uses the same public GraphQL payload as that page, archives raw JSON locally,
  and writes verified results and runner split sections. It ingested:
  - 2026-08-01 Flemington: 9 races, 116 runner result rows, 267 sectional rows.
  - 2026-08-08 Caulfield Heath: 9 races, 112 runner result rows, 267 sectional rows.
- The local database now has 38 result races, 437 runner-result rows and 534
  runner-sectional rows (the NSW PDFs are archived pending their careful
  marker-level parser). Racing.com's marker data is stored as split durations
  at 800m, 400m and finish; its `109` non-runner code is stored as scratched.
- User clarified Racing Victoria's instruction was simply to scrape the public
  Racing.com data. The implementation was validated against both historic
  Saturday cards and all unit tests passed. It was committed and pushed as
  `f8e97dd` (`Add authorised Victorian racing importer`).
- Next racing-data task: build a carefully validated parser for the archived
  Racing NSW sectional PDFs, then begin the track/distance/going par layer.
  Do not produce or publish live racing prices yet; the current ratings remain
  internal, low-history research output.

## 2026-08-15 — historical rating spine and VIC backfill

- Added internal V1 storage and pipeline in `RacingEngine`:
  `track_pars`, `run_performances`, `horse_rating_states` and
  `evaluation_runs`. `racing_engine.performance` uses an explicit as-of date,
  median track/distance/going pars, no double-counting of finish time and
  margin, capped last-400 relative evidence, recency weighting and uncertainty
  shrinkage. It is deliberately not yet weight/class/rail/pace/trip adjusted.
- Added `racing_engine.evaluation`, a chronological walk-forward diagnostic
  that rebuilds only from information available before each race date. Latest
  baseline (not evidence of betting edge): 417 races / 4,370 runners, Brier
  0.0855 and log loss 2.3093.
- Victorian authorised public-form backfill is complete for 2025-08-16 through
  2026-08-08: 399 result races, 5,031 runner results and 12,540 runner
  sectional records were added. The research database now totals 419 result
  races and 5,240 runner-result rows (plus the RNSW PDFs already archived).
- NSW Saturday metro discovery works (45 meetings in the same interval), but
  the RNSW historic CSV endpoint returns an HTML archive error for the first
  2025 request (`WebMeeting is null`). The importer now fails loudly rather
  than ingesting an invalid file. Resolve the authorised historic RNSW archive
  path before bulk importing NSW; do not substitute an unverified source.
