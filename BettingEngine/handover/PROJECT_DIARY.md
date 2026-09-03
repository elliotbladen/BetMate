# Project Diary — BettingEngine + BetMate
Last updated: 2026-05-04

One doc. Everything built. Newest at the top.

## 2026-08-31 — 2027 NRL/AFL rebuild decision

- The user approved carrying the NFL tier-development architecture into the
  2027 NRL and AFL model rebuilds.
- Reuse point-in-time snapshots, separate tier ablations, within-season shuffled
  controls and shadow-to-paper-to-betting promotion gates.
- Do not copy NFL point values or coefficients across sports; NRL and AFL must
  learn sport-specific personnel, continuity and contextual effects.
- Full decision: `docs/2027_nrl_afl_tier_rebuild_plan.md`.

---

## 2026-05-04 — AFL Tab Fix + New Machine Setup Protocol

### Root cause — this cost a full session to debug, don't repeat it

**Symptom**: AFL tab showed "No games available." NRL worked fine.

**Cause 1 — `.env.local` not in GitHub**
`.env.local` is gitignored (correct — it has secrets). But this means any fresh `git pull` on a new machine produces a broken app. The odds API routes return 500 "ODDS_API_KEY not configured." Without the key, NOTHING loads.

**Cause 2 — header sport tabs were cosmetic**
The NRL/AFL pills in the header had no `onClick`. Clicking AFL in the header did nothing. The working tabs were inside the page body. Users clicked the header, nothing happened, and assumed AFL was gone.

**Cause 3 — `useState` doesn't react to URL changes**
When I wired the header tabs to use URL params (`/odds?sport=AFL`), clicking them changed the URL but `activeSport` state didn't update because `useState(initialValue)` only reads the initial value once. Fixed by adding a `useEffect` that watches `searchParams` and calls `setActiveSport` on every URL change.

### What was fixed
- `Header.tsx` — NRL/AFL tabs now navigate to `/odds?sport=NRL|AFL` (real links)
- `Header.tsx` — hamburger menu added for mobile (Research was also invisible on mobile)
- `app/odds/page.tsx` — `useEffect([searchParams])` syncs `activeSport` with URL
- `.env.local.example` — fixed wrong key name (`NEXT_PUBLIC_ODDS_API_KEY` → `ODDS_API_KEY`)

### NEW MACHINE SETUP — do this EVERY time you pull to a new computer

> **This is the step you keep forgetting. Do it before anything else.**

1. Copy `.env.local.example` → `.env.local`
2. Fill in values:
   ```
  ODDS_API_KEY=<set-in-local-environment>
   NEXT_PUBLIC_SUPABASE_URL=<your supabase url>
   NEXT_PUBLIC_SUPABASE_ANON_KEY=<your supabase anon key>
   ```
3. `npm install`
4. `npm run dev`

Without step 2, the app starts but ALL odds show errors or empty. This is not a code bug — it is always a missing `.env.local`.

### Key file: `BetMate/.env.local.example`
Always keep this file up to date. Every new env var added to the app must also be added to `.env.local.example` so a fresh pull is not broken.

---

## 2026-05-04 — Mobile Nav Fix

### BetMate — Header hamburger menu
- **Problem**: `nav` was `hidden sm:flex` — no way to reach Research (or any page) on mobile or narrow windows
- **Fix**: Added hamburger button (visible mobile-only, `sm:hidden`) that toggles a full-width drawer below the header
- Drawer shows all three nav links (Odds / Tools / Research) with active state in green
- Drawer auto-closes on route change (`useEffect` on `pathname`)
- Desktop layout unchanged

---

## 2026-05-04 — R11 Pricing Readiness + BetMate UI + Odds Snapshot

### BettingEngine
- **Referee validation fixed** — `step6_validate` now treats missing referee as warning (T6=0), not fatal error. Refs not announced until Tue/Wed so Monday 7:03 PM run was dying.
- **Style stats auto-import** — `step0b_import_style_stats()` added to `prepare_round.py`. Runs at every pricing call. Reads BetMate's `latest-style-stats.csv`, UPSERTs into `team_style_stats`.
- **Results loader** — `scripts/load_results.py` + `data/import/r10_results_2026.csv` template. CSV-to-DB results ingestion for manual score entry.
- **AI manager agent** — discussed, decided against for now. Scheduled tasks + human review is the right V1 approach.

### BetMate — UI Redesign
- RacingZone-inspired: black/white/green premium feel
- Header: solid green `border-b-2` line, two-tone logo (Bet white / Mate green), green underline nav active states
- Cards: `#111111` on `#0D0D0D` page — visibly lifted. Borders `#252525`.
- Market tabs: underline indicator (not filled background)
- Muted text tightened: `#5C5C5C` not `#888`

### BetMate — Daily Odds Snapshot
- `lib/scraper/odds_snapshot.py` — pulls NRL + AFL from The Odds API daily
- Saves to `data/odds_snapshots/YYYY/YYYY-MM-DD.csv`
- 716 rows per day — every game × bookmaker × market × outcome
- Windows Task: daily 9:00 AM — **installed and running**
- Purpose: end-of-year study — line movement, bookmaker quality, EV validation

---

## 2026-05-04 — BetMate Scraper Pipeline

### BetMate — new scrapers
- `lib/scraper/nrl_fixture.py` — NRL.com draw API, outputs `latest-fixture.json`
- `lib/scraper/nrl_injuries.py` — Fox Sports injury list, outputs `latest-injuries.json`
- `lib/scraper/nrl_referees.py` — NRL.com draw page for referee appointments
- `lib/scraper/nrl_round_prep.py` — orchestrator, runs all three in sequence
- `lib/scraper/nrl_historical_results.py` — Playwright scraper for aussportsbetting.com xlsx

### BetMate — Windows Tasks installed
| Task | Time |
|------|------|
| BetMate NRL Historical Results | Mon 5:00 PM |
| BetMate NRL Style Stats Scrape | Mon 6:00 PM |
| BetMate NRL Round Prep | Mon 6:05 PM |
| BettingEngine NRL Pricing | Mon 7:03 PM |

### BettingEngine — prepare_round.py updated
- `_find_betmate_root()` — locates BetMate at `../BetMate`
- `step0_load_fixture_from_betmate()` — inserts R{N} fixtures from BetMate JSON
- `--round 0` default — auto-detects from BetMate fixture
- Auto-resolves injury + referee paths from BetMate if not supplied

### R11 fixture scraped
- 8 games, Magic Round, all Suncorp Stadium, May 15–17

---

## 2026-05-03 — Market Snapshots + Actual Bets Ledger

- BetMate market snapshot infrastructure built
- Actual bets ledger created for tracking real wagers
- NRL + AFL market intel pages

---

## 2026-05-01 — R8 Full Pricing + AFL Models + ML Shadow

### BettingEngine
- R8 full pricing run — NRL + AFL
- H2H, handicap, totals research matrices for R8
- AFL pricing engine built — `scripts/prepare_afl_round.py`
- AFL T1–T8 model adapted from NRL engine
- ML shadow model — parallel predictions stored in `results/`
- `ml/rebuild_models.py` — retrain on historical data

---

## System Overview (current state 2026-05-04)

### What runs automatically
| When | What | Output |
|------|------|--------|
| Daily 9:00 AM | BetMate odds snapshot | `data/odds_snapshots/YYYY/YYYY-MM-DD.csv` |
| Mon 5:00 PM | NRL historical results download | `data/nrl/historical/latest.xlsx` |
| Mon 6:00 PM | NRL style stats scrape | `data/nrl/style-stats/processed/latest-style-stats.csv` |
| Mon 6:05 PM | NRL round prep (fixture + injuries + referees) | `data/nrl/*/processed/latest-*.json/csv` |
| Mon 7:03 PM | BettingEngine NRL pricing | Terminal output + DB |

### What still needs human input each week
| Task | When | How |
|------|------|-----|
| Enter previous round results | Monday before 7:03 PM | Fill `data/import/rN_results_2026.csv`, run `scripts/load_results.py` |
| Check injury scraper quality | Monday evening | Verify `latest-injuries.json` has real players |
| Check referee assignments | Tuesday/Wednesday | Re-run pricing after refs announced |
| Review pricing output | Monday 7:03 PM | Inspect terminal output before acting |

### Key file locations
| Data | Path |
|------|------|
| NRL fixture | `BetMate/data/nrl/fixture/processed/latest-fixture.json` |
| NRL injuries | `BetMate/data/nrl/injuries/processed/latest-injuries.json` |
| NRL referees | `BetMate/data/nrl/referees/processed/latest-referees.csv` |
| NRL historical xlsx | `BetMate/data/nrl/historical/latest.xlsx` |
| Style stats | `BetMate/data/nrl/style-stats/processed/latest-style-stats.csv` |
| Daily odds CSV | `BetMate/data/odds_snapshots/YYYY/YYYY-MM-DD.csv` |
| BettingEngine DB | `BettingEngine/data/betting.db` |
| Pricing entry point | `BettingEngine/scripts/prepare_round.py` |

### Repos
- `BettingEngine` — Python pricing engine, SQLite DB, 8-tier model
- `BetMate` — Next.js web app, Python scrapers, data hub for BettingEngine
- Both pushed to GitHub: `elliotbladen/BettingEngine` + `elliotbladen/test` (BetMate)

---

## Pending / Known Issues

- **R10 results** — still NULL in DB. Must be entered before next pricing run.
- **Injury scraper quality** — Fox Sports parse untested on real round. Check `latest-injuries.json` after Monday 6:05 PM.
- **Referee scraper** — returns 0 records until Tue/Wed. Normal. Re-run pricing Wednesday.
- **Style stats stale in DB** — step0b will fix this at next 7:03 PM run.
- **BetMate UI** — changes deployed, browser hard refresh needed (`Ctrl+Shift+R`).
- **AFL pricing** — engine built but not wired into the Monday pipeline yet.

---

## 2026-08-12 — Independent NRL ML Shadow v1

- Built a versioned, independent XGBoost margin and calibrated H2H shadow.
- Removed the broken string rest-class features and stopped applying T2–T8 rule
  adjustments to ML predictions.
- Walk-forward results: 2024 margin MAE 14.36, H2H 61.0%, Brier 0.2287; 2025
  margin MAE 14.31, H2H 59.2%, Brier 0.2360.
- Wired the shadow to run after every successful normal NRL price-up. It writes
  only to `ml_shadow_predictions` and cannot alter official rules prices.
- Generated the R24 shadow for eight games.
- Full diary: `handover/sessions/2026-08-12_nrl-ml-shadow-v1-build.md`.

## 2026-08-12 — NRL ML H2H/handicap coherence correction

- Made the expected-margin model the single source of truth for both markets.
- H2H probabilities now come from the predicted margin and its held-out error
  distribution; the separate classifier remains diagnostic only.
- The rebuilt 2024–25 walk-forward test improved winner accuracy from 61.0% to
  62.7% and Brier score from 0.2316 to 0.2313. Classifier log loss was narrowly
  better (0.6553 vs 0.6559), so it remains visible as a challenger.
- Repriced the eight Round 24 games and saved
  `outputs/results/nrl_r24_ml_shadow_v2_2026-08-12.txt`.

## 2026-08-14 — Monday AFL/NRL availability and movement forecasting

- Changed the line-movement system from late team-list reaction to a Monday
  primary forecast for both codes; Tuesday NRL and Thursday AFL are now
  confirmation updates.
- Added per-player miss probabilities, value priors, expected absence points and
  projected team availability burdens using weekend match reports, injuries,
  HIA/judiciary information and post-game news.
- Installed Monday morning and afternoon AFL/NRL runs and preserved immutable
  Monday snapshots for honest scoring.
- Explicit long-term requirement: the system must self-learn by reconciling every
  Monday player/market prediction against confirmed selection and actual line
  movement, then recalibrate on time-split historical data for confident 2027
  forecasts.
- Current `availability_rules_v1` probabilities are initial priors, not yet
  calibrated confidence claims.
- Full handover:
  `handover/sessions/2026-08-14_monday-availability-line-movement-model.md`.

## 2026-08-14 — Championship opening-round and player shadow repair

- Repaired returning-team season resets, stale form/rest context, current-season
  config, Matchweek-1 division priors and the reversed value label.
- Normal Wolves–Blackburn fair H2H: $2.27 / $3.51 / $3.65.
- Backfilled 1,483 official-lineup matches across 2023/24–2025/26 and installed
  a 30-minute official-XI collector.
- The first genuine player starter model failed its time-split gate: goal MAE
  0.848123 versus base 0.847649. It was rejected; player output remains ABSTAIN.
- Full handover:
  `handover/sessions/2026-08-14_championship-normal-player-shadow-readiness.md`.

## 2026-08-15 — NRL halftime totals v2 rebuild

- Rejected the score-only five-bin lookup as the final totals model.
- Audited 754 historical halftime rows: 737 valid score/finish rows but no
  populated historical deep-stat features.
- Rebuilt totals around remaining-points prediction, a continuous historical
  score-state baseline, retained pregame prior, capped live-process evidence,
  uncertainty/fair-price output and explicit feature coverage.
- Full decision record:
  `handover/sessions/2026-08-15_nrl-halftime-totals-v2.md`.

## 2026-08-15 — NRL halftime totals v3 activated

- Replaced the active totals import with v3 while preserving v2 for replay.
- Added reliability-shrunk pace, opportunity, execution and defensive-stress
  layers on top of the empirical score-state distribution.
- Changed NRL live collection from halftime-only to 10/20/30/HT normalized,
  raw-timeline and market snapshots, with restart deduplication and the NRL
  feed's direct FirstHalf-to-SecondHalf transition handled.
- Replayed 753 historical rows: missing deep stats produced zero price changes,
  as intended. The new process weights cannot yet receive a genuine historical
  backtest because the archive contains no historical deep halftime fields.
- Full handover:
  `handover/sessions/2026-08-15_nrl-halftime-totals-v3-active.md`.

## 2026-08-15 — NRL halftime H2H/handicap v3 activated

- Replaced separate handicap/H2H calculations with one empirical final-margin
  distribution, making the two markets mathematically coherent.
- Fixed the old disconnect where H2H simulation ignored the displayed adjusted
  margin; Manly–Dolphins replay changed from an incoherent 5.0% Manly price to
  35.9%, paired with Manly +4.2 from the same distribution.
- Added capped, coverage-shrunk execution, opportunity, physical/defensive and
  conversion-regression layers using the newly expanded snapshot collector.
- Full handover:
  `handover/sessions/2026-08-15_nrl-halftime-margin-v3-active.md`.
- Research review then identified and corrected a fixed-weight baseline error:
  active pricing now preserves the current score and adds only the
  remaining-time share of pregame expected margin. Manly repriced from +4.2 and
  $2.79 to +8.3 and $4.58, much closer to the captured +11.5/+12.5 market.

## 2026-08-15 — AFL halftime margin correction and totals audit

- Corrected the same scoreboard-regression defect in AFL: current margin is now
  preserved and 61% of pregame full-game margin forecasts the remaining half.
- Removed active double counting through the old dynamic regression, stopped
  projecting unvalidated first-half accuracy, and calibrated H2H uncertainty to
  the observed 23.93-point remaining-margin residual SD.
- Leave-one-season-out margin MAE improved from 20.429 to 19.186 with the fitted
  remaining-margin structure.
- The 875-match totals audit found the existing bins competitive (15.480 MAE);
  compact ridge improvement was only 0.023 points. Keep the bins as baseline but
  add the NRL-v3 distribution, prior and forward snapshot architecture.
- Full handover:
  `handover/sessions/2026-08-15_afl-halftime-margin-v3-and-totals-study.md`.
- Implemented the recommended AFL totals v3: retained bins, conservative
  pregame prior, capped shots/inside-50/clearance evidence, injury adjustment,
  and empirical O/U distribution. Added nominal 10/20/30/HT raw/stat/odds
  snapshots and automatic Fox match IDs so unattended injury detection fires.

## 2026-08-31 — NFL T7 and context-event decision

- Rejected T7 scheme/matchup as a separate tier: margin MAE improved only 0.005
  points, RMSE and distance to the closing spread worsened, and totals worsened.
- Added an NFL-only context-event register for coaching changes, bereavements,
  milestones, returns and big-game labels. It is diagnostic with zero points.
- NFL does not inherit the unvalidated global emotional-tier point table.
- Player returns route to T2 personnel; rivalry/playoff structure routes to T1,
  preventing emotional double counting. Prospective timestamped evidence is
  required before any context event can influence a bet.

## 2026-08-31 — NFL T8 market-disagreement diagnostic

- Walk-forward 2020–2024 testing found that ridge disagreement of at least three
  points matched the closing spread-move direction in 65.8% of 412 moving games;
  three-point total disagreement reached 62.6% of 390 moving games.
- Rejected T8 as a spread price adjustment because MAE worsened despite a small
  RMSE improvement. Totals improved modestly but remain diagnostic.
- Enhanced the live Step 7 collector with bookmaker dispersion, structural/tree
  agreement and T8 WATCH statuses. Staking and betting actions remain disabled.
- True-opener provenance and prospective captures are mandatory promotion gates.

## 2026-08-31 — NFL T9 matrix confluence discovery

- Built family-level confluence that collapses correlated rows, requires three
  distinct fresh families and abstains on directional conflict.
- Retrospective spread discovery selected 124 games: +1.79 mean CLV, 78.6%
  closing direction on 103 moving lines, and synthetic 67–55–2 results.
- Froze the two-point structural/ML plus personnel-direction rule for the 2026
  prospective shadow. It cannot bet or be retuned during collection.
- Totals confluence remains an observed-weather oracle and is not promotable.

## 2026-08-31 — NFL final readiness consolidation

- Consolidated T0–T9 decisions and verified the sealed 16-game Week 1 T1 card.
- Historical T2+T3 improved margin MAE from 10.309 to 10.104 across 1,599 games
  and improved all six development seasons; it remains a live shadow.
- Generated a fail-closed Week 1 readiness card: all games ABSTAIN, staking off.
- Live blockers are market quotes, QB review, post-cut continuity, official
  injuries and verified stadium-weather capture—not silent model defaults.
- Froze promotion requirements at 500 predictions, two seasons, 90% market
  coverage, audited prices/openers, positive CLV and out-of-sample improvement.

## 2026-08-31 — NFL Step 11 shadow operations

- Added a weekly fail-closed checkpoint runner that rechecks all live gates,
  writes an immutable timestamped report and keeps all betting actions disabled.
- Missing live sources produce an explicit blocked checkpoint and ABSTAIN card;
  thresholds cannot be changed by a weekly result.

## 2026-08-31 — NFL Step 12 promotion ledger

- Added an append-only prospective evidence ledger for frozen T9 predictions.
- It tracks opener/price verification, coverage, CLV, opening-line beat rate,
  settlement and threshold version.
- The empty ledger correctly reports no evidence and cannot promote or enable
  staking. Manual overrides are disabled.

## 2026-09-01 — NFL Step 13 end-to-end backtest

- Added the EPL-style consolidated NFL backtest: 1,599 walk-forward games plus
  the sealed 272-game 2025 vault, with spread, totals and H2H row-level output.
- Across 1,871 games, H2H accuracy was 65.4%; spread synthetic -110 ROI was
  +4.3% at a three-point edge; totals were approximately breakeven at that edge.
- Opening coverage and bookmaker prices remain incomplete, so no ROI is treated
  as real-world evidence. Paper pricing is ready; staking remains disabled.

## 2026-09-03 — UCL separate-market architecture and player shadow

- Confirmed the UCL design: shared football ratings/fixure controls feed separate
  1X2 and Over/Under 2.5 market layers. The corner-enhanced U/O version remains a
  challenger and cannot automatically create bets in 1X2.
- Added the handover `sessions/2026-09-03_ucl-market-architecture-and-player-shadow.md`.
- SofaScore match statistics provide validated corners for 342 UCL fixtures;
  36 FotMob-recovered fixtures still lack matched SofaScore event IDs.
- The UCL player shadow framework exists but is data-pending: 0 timestamped UCL
  player events, shadow-only, no production price influence. It requires player
  event/appearance backfill and a walk-forward residual gate.
