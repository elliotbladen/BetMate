# BetMate — Claude Context

---

## READ FIRST — data-integrity lessons

`handover/DATA_INTEGRITY_LESSONS.md` records ten ways the numbers in this repo
have been confidently wrong, with the real cases and figures. Most were not code
bugs — they were plausible conclusions built on quietly bad data, and in three
cases the *checking tool* was the thing that was wrong. Read it before trusting a
metric, a source comparison, or a validation result you did not build yourself.

---

## HOW TO START A SESSION

1. Read **Current State** below — this tells you what's happening right now
2. Check `handover/sessions/` for the latest diary if you need more detail
3. Do NOT ask "what were you working on?" — the answer is here

---

## TWO-MACHINE RULE (established 2026-07-08 after work/home divergence incident)

The user works from TWO computers (work + home) on this same repo. On 2026-07-08 they
diverged badly: the home machine's monorepo import carried a stale BettingEngine copy,
the work machine had newer uncommitted data, and each side held work the other lacked
(EPL engine + AFL ML retrain existed only in git history; Jun 18 calibrations + Jul 7
work existed only in the work machine's working tree). Reconciled in commit `cefe758`.

**Protocol — every session, both machines:**
- **Start of session:**
  - Windows: `& scripts\git-sync-start.ps1`
  - macOS:   `./scripts/git-sync-start.sh`
  Refuses to pull over a dirty tree, fast-forward only, never auto-merges
  divergence, and **checks the RacingEngine seed against your local DB**.
- **End of session:**
  - Windows: `& scripts\git-sync-end.ps1 "what happened"`
  - macOS:   `./scripts/git-sync-end.sh "what happened"`
  **Rebuilds the RacingEngine seed if this machine is ahead of it**, then commits
  everything and pushes. NEVER leave a machine with uncommitted work.
- `git config pull.ff only` is set on the work machine — set it on the home machine too.
- If sync-start reports divergence: stop and reconcile deliberately (diff both sides,
  keep the newer of each file) — never `git checkout --` or `git reset --hard` blind.
- Untracked model artefacts (`ml/afl/results/models/*.pkl`) do NOT travel via git —
  retrain locally after pulling ML code changes.
- **Known outstanding:** diary `2026-07-05_afl-ema-form-split-models.md` exists only on
  the home computer — commit + push it from there. (The EPL build diary is NOT missing —
  it lives at `BettingEngine/handover/sessions/2026-07-05_epl-engine-build.md`; note
  BettingEngine has its own handover/ dir separate from the repo-root one.)

**Where the repo lives (updated 2026-08-29):**
- **This machine (work, user `Insight Survey`):** `F:\dev\BetMate` — moved here from
  `F:\IS\OneDrive - insightsurvey.com.au\Documents\BetMate` on 2026-08-29 because OneDrive
  was locking `.git/objects` mid-write. **Never put a working copy inside OneDrive / any
  file-sync folder.** Git is the only sync path between machines.
- **Home machine (user `ElliotBladen`):** `C:\Users\ElliotBladen\Apps`.
- **Fixed 2026-09-09:** the sync scripts no longer hardcode a path — they resolve the
  repo root from their own location, so the same script works on every machine.
  macOS equivalents (`git-sync-start.sh` / `git-sync-end.sh`) now exist too.
- **RacingEngine DB (fixed 2026-09-09).** The live `racing_engine.sqlite` (18.5 GB)
  never travels — but **91% of it is regenerable model output**: `run_performances`
  (14.2 GB) and `horse_rating_states` (2.6 GB). The irreplaceable source data —
  results, sectionals, cards, steward reports — is ~450 MB, **~52 MB gzipped**, and
  DOES travel as `RacingEngine/data/seed/racing_seed.sql.gz` (Git LFS).

  The seed only works if it is rebuilt after racing work. That is now automatic:
  `scripts/racing_seed_status.py` compares the seed's manifest watermark
  (`data/seed/seed_manifest.json` — max race date + row counts) against the live DB
  and both sync scripts act on it. Exit 1 = local DB behind the seed, restore it;
  exit 2 = local DB ahead, rebuild the seed before pushing.

  Manual equivalents:
  - Behind:  `cd RacingEngine && git lfs pull && ./restore_db.sh`
  - Ahead:   `cd RacingEngine && python3 build_seed.py` then commit
  - After restoring, regenerate the two excluded tables:
    `python -m racing_engine.performance --as-of <cutoff>`

  **Do not cloud-host this.** The sync problem is 52 MB, not 18.5 GB. A Postgres
  migration would be a large change across 82 SQLite-native modules to solve a
  problem the seed already solves.
- The pre-monorepo standalone `BettingEngine` checkout was removed from this machine on
  2026-08-29 (was fully pushed to `github.com/elliotbladen/BettingEngine`).

---

## CURRENT STATE
**Last updated:** 2026-09-12 PM (**SECURITY AUDIT DONE — PR #18 MERGED (`db172fb`), all CI green.** Report: https://claude.ai/code/artifact/cc2d1a58-1893-4f40-af02-84ff3f3dc2fd — 7 findings, 5 closed. **Fixed:** (1) ⚠️ **tipping tips were readable BEFORE kickoff** — `GET /api/tipping/tips` took `user_id` from the query string and never compared it to the session user, so any entrant could read a rival's picks and tip against them; the handler already computed `isGameweekLocked()` but only used it to guard the backfill. **Tips going public AFTER the round locks is the intended feature and is preserved** — the read is now gated on lock state. `POST` was always correct (uses `user.id`). (2) **`tipping_comps`/`tipping_entries`/`tipping_tips` are in NO migration** (hand-made in the dashboard, RLS unverifiable from the repo) and were queried with the **public anon key**; all 5 call sites now use `createAdminClient()`. ⚠️ **`supabase/migrations/20260912_tipping_rls.sql` IS WRITTEN BUT NOT APPLIED — RUN THE VERIFICATION QUERY IN IT.** It would have taken tipping offline before the code change, because `createServerClient()` forwards no cookies so `auth.uid()` was NULL in every query. Service role bypasses RLS, so **route checks stay load-bearing**. (3) `createServerClient()` **failed as success** — returned a stub answering `[]` with `error: null`; now throws (`getDataStore` still degrades but LOGS). (4) ⚠️ **`xlsx` is NOT local-only** — `lib/matrixEV.ts` → `app/api/ev-signals/route.ts` → PUBLIC_PATHS, so it ships; no exploit path today. (5) cron secret now constant-time. **Added:** Dependabot + CI (gitleaks/tsc/eslint/npm audit/pip-audit) + security headers (**no CSP** — Next injects inline scripts, needs nonces). **CI caught a real bug on its FIRST run:** `requests==2.32.5` → PYSEC-2026-2275, the Railway collector's own dependency; bumped to 2.33.1. Gitleaks confirms no secrets in history. ⚠️ **VERCEL HAS NOT DEPLOYED FOR DAYS — betmate.au IS STALE.** Every deploy on `main` fails (Railway is fine). **This is why the tipping cron 401s with the correct secret — the route was never deployed**, so the OLD gate is live and `/api/cron` is not in its allowlist; Next 16 + tipping are also not live. NOT the code (clean clone of tracked files builds fine) and NOT `vercel.json`. Needs `npm i -g vercel && vercel login` to read the build log. ⚠️ **A `git push` reported "Everything up-to-date" while the commit sat on the WRONG branch** — the working dir switched to `research/nrl-totals-matrix-v2-hitrate` mid-session. **Verify pushes against `origin/<branch>`, never push output.** **OWNER DEFERRED (~1 year, beta): Anthropic spend cap, 2FA — do not re-raise.** **STILL OPEN: (1) the RLS verification query + migration — the one security item NOT deferred. (2) Vercel deploy failure. (3) F-03 `/api/chat` in-memory rate limit is per-instance on serverless (public route, paid API). (4) F-07 unpickled models. (5) CSP. (6) `mobile/` never audited.** See `handover/sessions/2026-09-12_security-audit-and-remediation.md`. Prior state 2026-09-12 AM below: (**RAILWAY ODDS COLLECTION IS LIVE FOR ALL SEVEN CODES.** First real cloud run: worker `betmate-market-worker-1`, 21:55:25-21:56:11 UTC, AFL+EFL+EPL+NBA+NFL+NRL+UCL, **8,481 quotes / 3,424 genuine price changes / 42 credits / 0 errors**. Warehouse now 8,770 `odds_quote_state`, 11,523 `odds_quote_changes`, 8,647 `odds_market_checkpoints`. **It had never executed a single cycle before today** — TWO faults, either alone causing total silence: (1) the five Railway service variables were **staged but never applied** (canvas read "Apply 5 changes"), so every container started with no environment and died at the `ODDS_API_KEY` guard; (2) **Settings -> Cron Schedule was EMPTY** — `deploy.cronSchedule` in `railway.json` is schema-valid (verified against Railway's live JSON schema) but had never been applied to the service; now set to `*/5 * * * *` in the dashboard. **5 minutes is required, not arbitrary** — it is Railway's minimum AND `close_capture_lead_minutes` is 3, so anything coarser starts missing closing prices, which are the model's target. ⚠️ **THE 11 SEP DIAGNOSIS WAS UNSOUND — "no run row means the container is not executing" does not hold**: all three preflight guards returned 2 BEFORE the first Supabase write, so a container that ran perfectly but was misconfigured and one that never started left byte-identical evidence. It WAS executing the whole time. Fixed in `ddf5a84`: presence banner printed before any guard exits (set/MISSING, never values); aborted runs recorded in `odds_capture_runs` as `failed` with the reason; **status `skipped` instead of `success` when a cycle fetched nothing** — at `*/5` that is 288 rows/day and every one claiming success made the table useless, so **`status=eq.success` now means a real capture**; `live_enabled` dropped from `odds_collection_config.json` (nothing read it — the only switch is the env var). ⚠️ **THE QUOTA WAS 4 CREDITS FROM DEAD.** `com.betmate.odds-snapshot-10min` on the Mac was running **every 10 minutes** at ~3,300 credits/day for only 5 of 7 codes; the log shows the quota hitting **4 remaining** on 11 Sep before its refill, and the refill was ~4 days from dry — it would have killed Railway the day after it started working. **Throttled to twice-daily 09:00/18:00 (~60/day); plist version-controlled at `deploy/launchd/com.betmate.odds-snapshot-csv.plist`. DO NOT put it back to 10 minutes.** Budget: Railway ~14,900/mo + CSV ~1,800/mo vs 20,000. `scripts/run_odds_collector.sh` is **manual/emergency only, never a launchd timer** — a second scheduler double-spends credits and races Railway for the poll state. ⚠️ Local `main` is **24 commits behind origin** and checked out in a worktree at `/private/tmp/betmate-horse-ratings` — `git show main:` reads the WRONG ref; check `origin/main`, which is what Railway builds from. **CRON CONFIRMED FIRING** — 22:15:04 and 22:20:20, both `skipped`/0 credits, two consecutive 5-minute boundaries. **It was not firing at first because the Cron Schedule had been set with the "Daily" dropdown preset (`0 0 * * *`)** — Railway's field defaults to a preset selector and the **`Customize`** link beside it is what accepts a raw crontab. Daily would NOT have looked broken: one capture a day at midnight UTC, rows appearing, everything reading healthy, while missing every close capture. A **`Cron Runs` tab** appears on the service once a schedule registers, and Railway states **"Serverless is not available for services that have a cron schedule"** so scale-to-zero cannot sleep the collector. **Railway CLI access now exists** — logged in as elliotbladen@gmail.com, repo linked; project `65b6724e-5a68-4618-a203-06d30e4ec7cf` / service `7205580b-0028-4237-b9fb-31063e3a99c8` / env `df30a73b-dc36-47c1-a966-18a8985e09f4`, so no interactive linking again (scope granted is `workspace:admin`+`project:admin`, i.e. full read/write). `railway logs --deployment` shows the presence banner working live. ⚠️ **`railway.json` IS DEPRECATED AND STOPS WORKING 2026-12-01** — the CLI warns on every command; there is **no `.railway/` directory**, so this repo is entirely on the dead path, and that is the likeliest reason `deploy.cronSchedule` never applied. **It is a dated time bomb:** railway.json carries `builder: DOCKERFILE` + `dockerfilePath: cloud/Dockerfile`, and when it stops being read Railway falls back to auto-detection and tries to build the Next.js site — the exact failure that blocked the original deploy. `railway config migrate` translates it and **defaults to a dry run**; not run yet, and when done keep the cron in the dashboard where it is proven. **NEXT: (1) ⚠️ Railway trial is "30 days or $5.00 left" — now the single biggest risk; when it runs out collection stops silently and looks EXACTLY like today's fault; add a payment method. (2) migrate off `railway.json` before 2026-12-01. (3) confirm the 23:55 UTC capture and the close captures (NRL 06:02, AFL 09:32 UTC) landed. (4) delete `feat/market-engine-cloud` (Railway deploys from `main`). (5) Vercel tipping-reminder 401 still open, untouched.** See `handover/sessions/2026-09-12_railway-odds-collection-live.md`. Prior state 2026-09-11 PM/2 below: (**Next.js 14.2.35 -> 16.3.4 + React 19.3 MERGED (#11), and automatic tipping reminder emails MERGED (#12).** main=`71a7f24`. **Both critical unauthenticated RCEs are cleared — `npm audit` no longer flags `next` at all**; remaining are `@anthropic-ai/sdk` (moderate, breaking fix) and `xlsx` (**high, NO upstream fix**) - ⚠️ **NOT local-only, that note was wrong**: `lib/matrixEV.ts` imports it, `app/api/ev-signals/route.ts` imports that, and `/api/ev-signals` is in PUBLIC_PATHS, so it ships to production. No exploit path today (it only parses local BettingEngine spreadsheets, absent on Vercel), but do not add a spreadsheet upload against it. ⚠️ **`middleware.ts` is now `proxy.ts` and runs on NODE, not edge** (not configurable in Next 16). `next lint` is gone -> `eslint .` with `eslint.config.mjs`; the repo had no eslint config before so 59 pre-existing findings appeared, none of them upgrade breakage. **Two latent bugs fixed, neither caused by the upgrade:** a UTF-8 BOM in `app/globals.css` that Turbopack refuses to parse, and **`lib/oddsSnapshotFallback.ts` was flatMapping the ENTIRE 385MB odds archive (2.75M rows) into memory per request — dev server OOM'd at 8GB on any `/api/odds/*` call; now reads newest-first and stops (flat 60MB)**. Not a production issue (`data/` is gitignored). Also pinned `turbopack.root` — a stray `package-lock.json` in `$HOME` made Turbopack treat `~/` as the workspace root. ⚠️ **THE UI WAS NEVER VISUALLY CHECKED** (no browser tooling); merged on explicit instruction. Click `/odds` at 375px, Ask Baz, Details tabs. **TIPPING REMINDERS:** daily Vercel cron 09:00 UTC -> `app/api/cron/tipping-reminder`; emails entrants with incomplete tips when the next gameweek locks within 48h, deduped via `tipping_reminders`. Resend configured, **betmate.au verified** (DKIM/SPF/MX confirmed externally). ⚠️ **DKIM silently truncated on first paste (88 of 218 chars)** — if re-keying, check it ends `...8Wrd1wIDAQAB`. `RESEND_API_KEY`+`CRON_SECRET` are in Vercel but **RESEND_API_KEY is NOT in local .env.local**. ⚠️ **`lib/supabaseServer.ts`'s `createServerClient()` FAILS AS SUCCESS** — it uses the ANON key and returns a no-op stub answering `[]` to every query when that key is absent; the first dry run reported '0 people to remind' having queried nothing. Use `lib/supabaseAdmin.ts` (throws) for any job. `/api/cron` is in PUBLIC_PATHS but the route enforces `Bearer $CRON_SECRET` itself. **Baz GW4 tips submitted** (10 favourites from gw04 `1_model.json` market prices; 45pts from GW1-3). ⚠️ **`scripts/baz_tipping.py` IS BROKEN — do not run it**: `data/epl/predictions/latest.json` is 3 rounds stale AND it matches predictions by home team only, so it would tip 9/10 games off the wrong opponent's odds. **NEXT: (1) verify the deploy with `curl -H "Authorization: Bearer $CRON_SECRET" "https://betmate.au/api/cron/tipping-reminder?dry_run=1"` — the only way to confirm the Vercel env vars; drop dry_run to send. Reminder delivery to the one outstanding entrant was still unverified (GW4 locked Sat 14:00 UTC); participant records are deliberately kept out of this file. (2) click through the UI. (3) repoint Railway at `main` before deleting `feat/market-engine-cloud`. (4) market engine is still `ODDS_COLLECTION_LIVE_ENABLED=false`.** See `handover/sessions/2026-09-11_nextjs16-upgrade-and-tipping-reminders.md`. Prior state 2026-09-11 PM below: (**MARKET ENGINE MOVED TO THE CLOUD — PR #8 merged to main (`2eadea5`).** Cloud collector (`cloud/odds_collector.py`, Railway + Supabase) is deployable for 7 sports incl. NBA. **Cadence: flat 2-hourly + one close capture per kickoff cluster = ~14,900 credits/month, 26% inside the existing $30/20k plan.** ⚠️ **NEVER drive the close capture off the cadence ladder** — staggered kickoffs keep the sport in tight mode all evening, measured at **86,046 credits/month**; `next_due_at()` does it for ~1,900. Paid calls gated on the **FREE** `/events` check (0 credits, measured), NOT the API's `active` flag — UCL read `active=false` while matchday 1 had been played and Oct fixtures were live. ⚠️ **`ODDS_COLLECTION_LIVE_ENABLED=false` and the laptop launchd jobs are still running.** Go-live: force one run with the flag false → `cloud/collection_health.py` + quota headers → flip true → confirm rows → unload `com.betmate.odds-snapshot-10min` + `com.betmate.prevent-sleep`. ⚠️ **Railway deploys from `feat/market-engine-cloud` — repoint it at `main` before deleting that branch.** **SECURITY: Next.js 14.2.3 → 14.2.35** (Railway's scanner blocked the deploy over two HIGH CVEs; npm rated the old state critical incl. an authorization bypass, and `middleware.ts` gates the API routes). **NOT fully clear — 14.x tail has two critical unauthenticated RCEs fixed only in 15.5.24+; Next 14→15/16 scheduled 2026-09-11 PM.** `xlsx` has two HIGH advisories with no upstream fix (local-only use). ⚠️ **`log_actual_bet.py` WAS EATING THE LEDGER** — `FIELDNAMES` lacked `week_ending` and the script rewrites the whole file, silently deleting that column from all 118 historical rows; it is read by 9 scripts incl. `update_clv_running.py`. Fixed + now writes LF. **Byte-compare an untouched row against `git show HEAD:` on any script that rewrites rather than appends.** Also merged: the Championship referee cards matrix and the first two cards bets. Closed `research/efl-totals-vault-test` and `research/efl-totals-signal` (already in main). **Racing branches/worktrees left alone — Codex owns those.** See `handover/sessions/2026-09-11_market-engine-cloud-deploy.md`. Prior state 2026-09-11 below: (**Championship REFEREE cards matrix built, and the first two cards bets placed.** The referee-centric transpose of the team confluence workbook: `scripts/efl_championship_referee_matrix.py` -> `outputs/football/_reference/efl_championship_referee_goals_matrix.xlsx` (51 referee sheets, 2021/22-2024/25), plus a local HTML viewer (`scripts/_referee_matrix_viewer.py`, served on :8777) and **the weekly job `scripts/efl_cards_weekend.py`**. **THE FINDING: referee O/U 2.5 GOALS edge does not exist; referee CARD tendency does.** Same 80 referee-season pairs: goals-vs-close r=+0.08 (CI -0.12/+0.29), cards/game r=+0.42 p=0.0001. Goals side is noise by every measure - 1,309 cells gave 69 at p<0.05 where chance predicts ~65 (**ratio 1.05x**) and **zero** survive Benjamini-Hochberg at q=0.10; a planted-effect power check says an 8pp spread would have been caught 99% of the time, so it is evidence of absence at bettable size (a 2-5pp effect could hide but is not harvestable). ⚠️ **Two claims were corrected mid-session** - the 1.99pp "true between-referee spread" sits at the 66th percentile of its OWN null (p=0.34, estimator returns 1.46pp on zero-effect data) so it is consistent with zero; and an apparent negative split-half r=-0.59 on 16 refs vanished on the proper pooled 80-pair design. Workbook now carries **empirical-Bayes shrinkage** (`Over edge pp (shrunk)`: n=10 keeps 1.6%, n=119 keeps 15.8%; S Allison -20.0pp -> -1.25pp) and **FDR flags instead of +/-7.5pp** (the team rule lit 58% of referee cells). Cards shrinkage is far gentler (tau 0.366 c/g) because cards persist. **BETS PLACED (first ever cards bets): 2026-0118 Preston v Lincoln OVER 3.5 cards @1.85 $25 (ref S Martin, 95g, 63% o3.5) and 2026-0119 Charlton v Portsmouth UNDER 3.5 @1.85 $25 (ref A Kitchen, 80g, 39%)** - EV +10.8%/+10.4%, though bootstrapped the Preston bet has a 21% chance of being -EV vs Charlton's 3%. Added `cards` to `log_actual_bet.py --market` so bookings never pool with goals totals in CLV. **SETTLE both once football-data publishes the 12-13 Sep round (HY/AY).** Model: `lambda = ref_cpg x team_cpg / league_mean` then Poisson, validated against the real card distribution (fits within 1pp at every line). ⚠️ **DATA SOURCES LEARNED: referee appointments come from FotMob** `https://www.fotmob.com/api/data/matchDetails?matchId=` (fixtures via `.../api/data/matches?date=YYYYMMDD`, English Championship = ccode ENG) - it is the ONLY working route: efl.com is a Nuxt SPA returning a 7KB shell to every URL for both curl and WebFetch, Transfermarkt says "Referee: Unknown" until kickoff, ESPN fills it in only at kickoff, worldreferee/footballwebpages/11v11 all 403/404. **The Odds API DOES carry `alternate_totals_cards` - but not for the Championship** (zero books across uk/eu/au); EPL returns Pinnacle 1.80/2.02 at 5.1% margin, and Betfair at a 34.7% overround i.e. no exchange liquidity. Pinnacle covers the Championship (guest API league 1977) but does not price its cards. **The Odds API carries NO Asian bookmaker at all** (63 books uk/eu/au/us, none of SBOBET/IBC/188Bet/MaxBet) - do not treat its coverage as "the market", that error was made and retracted this session. Pinnacle's guest API zeroes the `limit` field for unauthenticated requests (EPL too), so real limits are only visible in a logged-in betslip. **NEXT: build the same cards matrix for the EPL**, where Pinnacle actually prices the market and a live price exists to measure real EV/CLV against instead of the break-even proxy. Nothing committed - whole session is in the working tree on `research/efl-totals-vault-test`. See `handover/sessions/2026-09-11_championship-referee-cards-matrix-and-first-bets.md`. Prior state 2026-09-10 PM/2 below: (**Championship O/U 2.5 is CLOSED, not parked — trees and confirmed lineups both null, and the xG route is blocked to ~May 2027.** Two probes, neither touching the spent vault (`load()` drops 2025/26 first). **(1) Tree ensemble** (`ml/football/backtest/efl_totals_tree_probe.py`) — the de-vigged close enters as an XGBoost **`base_margin`** so trees learn residual only; early stopping on the last *training* season; two pre-specified feature sets (7 symmetric aggregates / 21 raw per-team). Pooled n=2153: market-only .68194, treeA .68167 (+0.00027, 1/4 seasons, CI [-0.0027,+0.0033]), treeB .68119 (+0.00075, 2/4 seasons, CI [-0.0011,+0.0026]), trees-only .69214 (−0.0102). **treeB reproduces the closing line (.68121) to 5 decimal places** — a tidier copy of the market, measured. Self-tests pass: 0 rounds = market to 5.7e-08 (proves base_margin is wired), planted total → .0189. **(2) Confirmed lineups** (`efl_totals_lineup_probe.py`) — ESPN XIs 2023/24+2024/25, 851 matches joined, all 24 names map cleanly. XI per-90 shots/SOT/goals + minutes-share continuity correlate with the outcome at +0.05–0.06 but with the **market residual at +0.0004 (p=0.99)**; n=851 detects |r|>=0.096 at 80% power; walk-forward .68717 → .69465 (worse). Note the XI is known ~1h pre-kickoff, so its benchmark is the CLOSE, not the open this account bets into. **(3) xG is blocked.** Verified against football-data headers: **HxG/AxG exist in 2026/27 ONLY** (absent E0+E1 2022/23–2025/26); local coverage Championship 60/69, EPL 30/30. A usable Championship season arrives ~May 2027, not October 2026 — correct the parked plan. ⚠️ **Understat is more dead than recorded**: league pages return 200 with the right title but NO embedded data payload (18KB, adsense only, no `datesData`) for *historical* seasons too — so it is also NOT the fix for the EPL totals scale break, which the AM session had as top football priority. FBref/StatsBomb 403s a plain client: plausible, unverified, a source-evaluation job. **Three independent input classes are now ruled out (raw stats linear, same with interactions, confirmed lineups); only weather is untested and needs a backfill that doesn't exist. Do not price Championship O/U 2.5 as a bettable market and do not model it further.** The one piece of work that changes anything is acquiring real xG from a non-football-data source, which also unblocks the EPL fault. See `handover/sessions/2026-09-10_championship-totals-trees-and-lineups.md`. Prior state 2026-09-10 PM below: (**EFL Championship GW7 priced (11-13 Sep) — NO BETS. Three model faults found, and the results file was missing a whole played round.** Outputs: `BettingEngine/outputs/football/championship/2026-27/gw07/` (`1_model.md`, `2_bets.md`, `2_bets_matrix.md`, `_supporting/`); driver `scripts/price_efl_week7_normal_shadow_2026.py`. ⚠️ **DATA FIX — football-data.co.uk had not published the 8-9 Sep round (GW6).** Its live E1.csv stopped at 60 matches, so the engine was missing a full round AND reported **7-day rest for every club** when West Ham/Wrexham were on a 3-day turnaround. Supplemented 9 completed matches from ESPN via new reusable `scripts/ingest_espn_results_supplement.py` (goals/refs/shots/corners/cards, tagged `SourceSupp=espn`, CSV backed up, refs verified against football-data naming). Fit 6684->6693. **Re-run `fetch_results.py --league championship --live-merge` once football-data publishes 8-9 Sep** — it de-dupes keep=last so the official rows replace the supplement automatically. Round numbering: GW4=1-2 Sep, GW5=5-6 Sep, GW6=8-9 Sep (9 played, 3 postponed), GW7=11-13 Sep. **FAULT 1 (new, Championship-specific): the O/U 2.5 isotonic calibrator has almost no resolution and a hard ceiling.** It returns only 6 distinct values over raw 0.25-0.80 and is censored at **0.6042** (raw 0.61 and raw 0.99 both map there); the widest plateau is raw 0.34-0.48 -> 0.4495. Across GW7's 12 fixtures the model emits **4** distinct P(Over) values and **8 fixtures share 0.4495**; model is below market no-vig in 10/12. Cause is real: in the 2205-row calibration set the actual over-rate is flat/inverted (0.4534 / 0.4511 / 0.4451) across the band holding 75% of games, and the ceiling is set by 20 games with raw>0.7 that went 50% over. **The model structurally cannot price an Over (min fair 1.655) and O/U selections cannot be ranked.** This is a DIFFERENT fault from the EPL totals bias — Championship is goals-fed (`xg_csv: null`) so the Understat scale-break does not apply (confirmed); EPL over-predicts, Championship under-predicts and can't resolve. **Do not bet Championship O/U 2.5 until it is rebuilt.** **FAULT 2: `_reset_new_team_dc_ratings` distorts TOTALS, not 1X2** (corrects the EPL GW4 expectation). Re-pricing the 5 affected fixtures with a current-season D-C refit moves totals by −0.59 to **+0.72** goals (4 of 5 up) but 1X2 by at most ±0.036 — when both clubs are misstated the same way the errors cancel in the H/D/A split. It flattens exactly the extreme profiles (Wolves 13 GF, Burnley 13 GA, Bolton/Cardiff next worst). T8 doesn't rescue it: no ClubElo file, so static `new_team_elo_priors` worth ±0.03 xG — and it gives bottom-placed Burnley **+180**. **FAULT 3: ratings lag the table** — rank correlation of raw D-C net strength vs 2026/27 PPG is **0.334** (0.384 ex-reset) at `decay_rate: 0.001`; Burnley are bottom with the worst defence and are the highest-rated club in the raw fit, Derby 21st/rated 10th. That is the source of the round's 13-19pp market disagreements. **T5 LESSON (likely explains GW5's 0/5): 62 of ~110 published Championship absentees have made ZERO 2026/27 appearances** — their absence is already in the ratings, so feeding them to T5 double-counts. Restricted T5 to players on a list who featured in one of their club's last 2 matches and start >=60%: 10 players, 6 clubs. Both suspensions derived independently from red cards then confirmed. Every EV reported with and without T5. **Result: 10 selections cleared 10% EV, all rejected** — 4 Unders are one calibrator plateau; Wrexham +69.6% and Sheffield United +51.0% ride reset clubs (the matrix's +7 on Sheff Utd is 7 overlapping base-rate cells, one fact counted 7x); Derby +37.6% is rating lag and the matrix opposes at −2; Watford +16.4% collapses to +8.6% with T5 off. Season context: Championship model selections are **0W-8L, −100% ROI with +6.67% CLV** (paper, not staked) — good prices, wrong sides. Also open: T6 refs not published at build time; `ppda_dated.csv` still has only matchweek-1 2026/27 rows and `get_ppda` has no recency guard. Rebuilt `player_match_stats_espn_2026.csv` (Championship, 2759 rows / 69 matches; 28 feeds had been cached pre-kickoff with no rosters). No engine code modified; 255 tests pass, 3 pre-existing failures. **SAVED FOR GRADING:** at the user's request the seven >=20% EV selections are saved to `gw07/2_bets.csv` as `tracked_selection_not_staked` (7.5u notional; Sheffield United 1.5u on matrix +7) — **judge them next week** with `python scripts/grade_gameweek_saved_bets.py --bets outputs/football/championship/2026-27/gw07/2_bets.csv --league championship` after running `fetch_results.py --league championship --live-merge`. Only 1 of the 7 has matrix support (Sheffield United +7); the three Unders score +0/+0/-1 and the draw is unscoreable. ⚠️ **GRADER BUG FIXED:** `score_football_saved_bets.py` could not grade a **Draw** or an **Under** — draws scored as losses against the AWAY odds column, unders graded **backwards** against the OVER column; 4 of the 7 saved selections would have been mis-graded. Patched (historical 2026-09-08 output re-runs byte-identical) and new reusable `scripts/grade_gameweek_saved_bets.py` added, validated by reproducing GW5's published figures exactly. Matrix scans extended beyond EV qualifiers: `_supporting/matrix_full_scan.csv` (all 24 team-sides) and `_supporting/matrix_ou_scan.json` (goals matrix, `scripts/_efl_gw7_ou_confluence.py`). **O/U 2.5 INVESTIGATION DONE — PARKED ~1 MONTH (user call 2026-09-10).** Branch `research/efl-totals-signal` (pushed) + note `BettingEngine/outputs/football/championship/_research/TOTALS_SIGNAL_PROBE.md`, harness `ml/football/backtest/efl_totals_signal_probe.py`. **Verdict: the Championship O/U 2.5 model has NO measured edge and must not be rebuilt on existing inputs.** Walk-forward over 3,225 matches with opening+closing Pinnacle totals odds (2019/20-2024/25; `Avg>2.5`/`AvgC>2.5` exist ONLY from 2026/27 — historical totals odds are in the **Pinnacle** `P>2.5`/`PC>2.5` columns, so anything reading `Avg` for an old round silently gets NaN). Market+features log-loss 0.68245 vs market-only 0.68194 (WORSE), LR chi2(7)=0.00 p=1.0000; closing line 0.68121 beat everything. Harness validated 3 ways (planted signal -> log-loss 0.027; features do correlate, SOT r=+0.082 p<0.0001; features explain R2=0.36 of the closing price — i.e. the market has already priced them). **Vs the OPENING line** (the operative benchmark — user bets early), calibrator refit on prior seasons only: 2022/23 level, 2023/24 and 2024/25 worse, never better; pooled open .6823 vs model .6902. Staking at the opening Pinnacle price: EV>=5% 773 bets -2.46% ROI / CLV -1.24%; EV>=10% 480 bets -5.94% / -1.28%; EV>=20% 198 bets -3.86% / -1.91% — **CLV negative at every threshold**, 70-83% of picks Unders. Production D-C totals also loses to the close in all 4 seasons and to a constant base-rate guess in 2021/22 (.7090 vs .6909). **On return (~Oct 2026): (1) re-run the probe with real xG** (`HxG`/`AxG` now ship in the live E1 file and accumulate each round — shared with the EPL xG fix), **(2) re-test mean reversion at GW12-15** — as of GW6 the 3.028->2.606 g/g decline is p=0.23 and the season mean is NOT significantly above long-run (z=1.48, p=0.14) though the over-rate is (p=0.008); Championship seasons do NOT normally start hot (first-69 vs rest -0.021 g/g, 5/12 hotter), closest comparator 2023/24 opened identically at 2.826 and settled to 2.660 — **(3) grade GW7**. Scope: rules out goals/shots/SOT/corners/rest/referee only; says nothing about xG, lineups or weather. Git reconciled 2026-09-10: local `7f413ed` was a duplicate of origin `ec68073` (identical patch-id), rebase skipped it, main in sync and pushed; `pull.ff only` NOW SET on this Mac. See `handover/sessions/2026-09-10_efl-championship-gw7-pricing-totals-calibrator-fault.md`. Prior state 2026-09-10 AM below: **EPL GW4 priced. Two model faults found: promoted clubs are rated as average PL teams, and the totals model over-predicts by ~0.6-1.1 goals/game.** ⚠️ **ODDS API IS LIVE AGAIN** — memory had it deactivated since 26 Aug; `soccer_epl` returned 20 events / 42 books / h2h+totals, 19,472 requests left. Check the twice-daily snapshot tasks resumed and whether the soccer hook-up tasks can proceed. **TOTALS BIAS (new):** GW4 model mean total xG 3.53 vs an EPL running 2.84 (2025/26 2.75); model mean P(O2.5) 0.661 vs no-vig market 0.559, higher in 8/10; D-C predicts 3.59 against its own fit target mean of 2.78; GW1+GW3 priced vs actual = 3.28 predicted / 2.65 actual, over in 15/20. Tiers are NOT the cause (−0.07). **Mechanism: Understat xG died 2025-05-25, so D-C is fitted on real xG to 2024/25 (target 3.20 vs 2.93 actual) then `FTHG×0.85` from 2025/26 (2.34 vs 2.75) — a ~28% scale break straddled by the 693-day decay window.** Merge coverage measured: 100% through 2024/25, **0% for 2025/26 + 2026/27**. Consequence: all 7 O/U-2.5 selections over 10% EV this round are Overs and NONE is a bet — do not back Over 2.5 on this spine in any league (check UCL; Championship is goals-fed so may be exempt). **Fixing the xG source is now the top football priority** — football-data's live E0 file now carries HxG/AxG non-null for all 30 season matches, which the local CSV schema lacks; cost that before resuming Understat. Prior finding, still open: **EPL GW4 priced — and a structural rating gap found for promoted clubs.** Full 1X2 + O/U 2.5 normal and shadow prices for MW4 (12–14 Sep) in `BettingEngine/outputs/football/epl/2026-27/gw04/` (`1_model.md`, `2_bets.md`, `_supporting/`), script `scripts/price_epl_week4_normal_shadow_2026.py`. **No bets approved.** Seven candidates cleared 10% EV; three are artefacts of promoted clubs being rated as average PL teams, three collapse to ≈+5–10% once T5 is removed. **The finding: `_reset_new_team_dc_ratings` sets a club new to the division to exact league average (att=1.00 def=1.00) and also discards their current-season results — Coventry are rated average after 0 pts / 0 GF / 5 GA — while Elo, which only tracks EPL matches, reverted Hull to 1493.1 at season start after nine years outside the division (Chelsea 1521.5, i.e. effectively level). T8, the ClubElo prior built for exactly this, is DISABLED for EPL (`epl.yaml` has no `t8_decay_games`; Championship uses 15).** Treat any EV on Coventry/Hull/Ipswich as unpriced until that is decided. Also measured: the O/U 2.5 isotonic calibrator is quantised and censored above raw ~0.77 (four GW4 games share fair 1.48, three share 1.29 — rank on the raw column, which `1_model.md` now reports); `get_ppda` has NO recency guard so T2 fired on Hull's and Sunderland's **2017** PPDA (only decisive in Crystal Palace v Ipswich: 2.59→2.80 total xG with PPDA suppressed); T6 not injected (PGMOL published the 10 MW4 refs but not the fixture mapping — worth up to ~0.08 raw O2.5); no totals market obtainable so no O/U EV screen. Data refreshed: EPL player feeds GW2+GW3 fetched (shadow had been running on GW1 XIs) and `player_match_stats_espn_epl_2026.csv` built so rolling player form is current-season. No engine code modified; 255 tests pass, 3 pre-existing failures (AFL/NFL, missing pyarrow). See `handover/sessions/2026-09-10_epl-gw4-pricing-and-promoted-team-rating-gap.md`. Prior state 2026-08-29 below: **Repo hygiene, no pricing/model work.** Moved this machine's working copy out of OneDrive → `F:\dev\BetMate` (OneDrive was locking `.git/objects`). Committed a full uncommitted 28 Aug RacingEngine V2 build day (`b899593`) + a Codex exit-handover (`5ec2a32`). Fast-forwarded `main` to the old `local-sandbox` head and **deleted `local-sandbox`** (local + remote) — this machine is back on the two-machine `main` protocol. Deleted the absorbed `racing-engine/step2-research` remote branch is still pending on GitHub. Removed the stale standalone `BettingEngine` checkout (fully pushed to its own repo first). Rebuilt both `.venv`s at the new path; RacingEngine 141 tests pass / 1 skip, BettingEngine 95 pass; DB integrity `ok`. See `handover/sessions/2026-08-29_*` and the "Where the repo lives" note above. Prior state 2026-07-28 below: Resumed after a session crash mid-round-pricing. **NRL R22 fully priced** — 7/9 tiers real (78%), backfilled a skipped R21 (fixture+results never loaded, reconstructed from NRL.com purely to keep ELO current — not a priced round). Writeup `BettingEngine/outputs/results/r22_nrl_pricing_2026.md`, CSV `results/r22_pricing_2026.csv`. T6 refs not yet announced (normal, Wednesday), T10 correctly dormant (no Origin). **AFL R21 fully priced** — writeup `BettingEngine/outputs/results/r21_afl_pricing_2026.md`, CSV `results/r21_afl_2026.csv`. 3 of 9 games are rules/ML model-alignment no-plays (Collingwood/Geelong, St Kilda/Sydney, Richmond/West Coast). Flagged Port Adelaide vs GWS as a genuine T9-matrix-vs-both-models conflict (same shape as the R19 Power/Dockers case) — worth a second look once market data returns. **Found this session: AFL T5 injury tagging regressed to 100% generic utility/average** (no hand-curation, unlike R19's manual elite/key tagging) — Port Adelaide (Butters, Rozee both elite last round) and GWS (Green/Kelly/Hogan, all elite/season-ending last round) are pricing with near-zero injury impact that's very likely understated; recommend a manual re-tag before betting on either. Also found: AFL emotional scraper introduced a new `losing_streak` flag_type that isn't in `AFL_T6_CONFIG`'s supported list — Gold Coast's flag silently no-op'd this round, needs a code fix. ⚠️ **Odds API still down** — now 25 days past the Jul 3 outage and 2 weeks past the user's own expected ~Jul 14 renewal; worth checking on rather than assuming it resolves itself. Prior state below, 2026-07-09 EVE (**Championship engine Phase 1 DONE** — EPL engine refactored league-parameterised: `WorldCupEngine/ml/epl/` → `ml/football/` + `leagues/epl.yaml`, entry points take `--league`, **regression gate passed exactly** (RPS 0.1319/0.1399/0.1287, agg 0.1335). Plan + approved decisions in `ml/football/CHAMPIONSHIP_PLAN.md` — Phase 2 next: E1 fetcher + championship.yaml + goals-fed refit; **2025/26 is a VAULT hold-out, never use in development**. Also today: **Baz v2 direction set** — answer ALL bet-related questions per game, plan in `handover/baz_v2_direction.md` (May 2026 Baz roadmap abandoned); Jai Arrow T7 flag found via web double-check after scraper missed it → both emotional scrapers now do per-team news queries; BetMate + Odds API paused until ~Jul 14 payday (see warning below). Earlier today: **NRL R19 fully re-priced, 100% tier coverage T1–T8+T10+T9** — supersedes Jul 7 auto-run which had no refs. Writeup with mandatory can't-price report: `BettingEngine/outputs/results/r19_nrl_pricing_2026.md`, CSV `results/r19_pricing_2026.csv`, matrices+confluence pushed to Supabase. Refs hand-sourced from web (NRL.com never published R19 appointments — scraper 0/7 both Wed+Thu); emotional scrape fresh = genuine 0 flags; weather clear 7/7; T10 dormant (camp ended Jul 9). **Can't price: market EV (Odds API down), NRL ML shadow (predict.py still Phase-3 stub → model-alignment rule unverifiable for NRL), Origin G3 backup fatigue (Roosters 6 players Wed→Sat on a -14.1 line — biggest unmodeled risk of round)**. Rabbitohs/Knights = model-vs-matrix conflict, no-play. Same day: AFL R18 fully re-priced, all tiers T1–T7 + ML shadow + T9 — supersedes the Jul 7 start-of-week run. Writeup: `BettingEngine/outputs/results/r18_afl_pricing_2026.md`, CSV `BettingEngine/results/r18_afl_2026.csv`, predictions pushed live to betmate.au ✅. Session fixes: (1) **ML shadow was silently broken since the Jul 5 EMA/split-feature retrain** — `prepare_afl_round.py` fed the old 29-col feature row to models now expecting 38/30 cols; fixed with split feature sets + deploy-time EMA computation + `mkt_home_prob_open` (ELO fallback). (2) T2 Footywire scraped fresh today — the Jul 7 run had silently used R9 (May 12) style data. (3) Bogus Adelaide "personal_tragedy" T6 flag removed — scraper recycled April headlines; Dawson played R17. (4) Brisbane T5: Payne→season-ending, Gardiner added. ⚠️ **BETMATE + ODDS API DOWN UNTIL ~TUE 2026-07-14 (payday) — DO NOT DEBUG, DO NOT PUSH PREDICTIONS.** User confirmed 2026-07-09: the Odds API subscription lapsed (hence the 401s since Jul 3) and betmate.au is intentionally down until they renew after payday next Tuesday. Nothing is broken locally — don't investigate the 401s, don't re-push predictions to the site, don't run snapshot cycles (they'll just 401). When the user says the API is renewed: (1) run a snapshot cycle, (2) re-push NRL R19 + AFL R18 predictions (site currently has the stale Thu-09:00 NRL numbers — no refs, no Jai Arrow flag), (3) compare R18/R19 model prices vs market for EV before any bets, (4) verify scheduled snapshot tasks resume clean. R18 model alignment: all 9 games agree on winner; H2H OFF-LIMITS on GWS/Geelong + Carlton/Hawthorn (rules vs ML H2H disagree). Prior 2026-07-09 AM state: Post-reconcile cleanup on work machine: AFL ML pkl models **regenerated with the Jul 5 EMA/split-feature code** ✅ (margin MAE 29.3 / H2H 68.5% on 2025 holdout, Jul 7 xlsx); stale nested `BettingEngine/.git` (pre-monorepo repo, fully pushed to github.com/elliotbladen/BettingEngine) moved out of the tree to `C:\Users\ElliotBladen\Backups\BettingEngine-pre-monorepo.git` — git commands inside BettingEngine now correctly hit the monorepo; root `.pytest_cache/` gitignored (was an unreadable elevated-process dir spamming warnings). Missing reconcile diary written retrospectively. Prior, 2026-07-08: git divergence between work/home machines reconciled — commit `cefe758`, see TWO-MACHINE RULE above and handover `2026-07-08_machine-reconcile-architecture.md`. EPL engine (built at home Jul 5) restored to `BettingEngine/WorldCupEngine/ml/epl/`. Baz tunnel now requires an auth token (`BAZ_TUNNEL_TOKEN` — **must still be set in Vercel env**). Root README rewritten to match actual architecture. Prior state, 2026-07-03: built the market-event causal-tagging pipeline — see section below. Also: AFL R17 fully re-priced 2026-07-02, T1–T7 + ML shadow + T9 matrix, writeup at `BettingEngine/outputs/results/r17_afl_pricing_2026.md`. Extensive model-vs-market backtesting this session: real production model (not naive ELO proxy) is at genuine parity with market on handicap accuracy once stale-model rounds are excluded (AFL R14-16: 11-10 closer, essentially tied avg error). The "model undercooks market at extreme ELO gaps" pattern does NOT indicate an exploitable market inefficiency — large-sample ATS backtest on the exact rules+ML-agree pattern went 4-8 (33%) for AFL. Do not bet big rules/ML-vs-market disagreements. NRL same window showed a genuine 60% ATS cover rate (21-14) — worth continued tracking, not yet proven at scale. Running CLV: NRL +4.99% (58 bets), AFL +0.77% (48 bets).)

**Branch closeout 2026-09-12:** Owner approved closing PRs #2, #13 and #15; keep fitness/trials PR #14 open for continued work. Next.js 16 and tipping reminder code are merged. The September 11 end-of-day handover records unverified Railway execution and reminder delivery; do not infer runtime success from deployment status. Analytics passes three focused tests and a Next.js 16 webpack production build after its route-export repair. No production analytics migration has been applied during this closeout. See `handover/sessions/2026-09-12_branch-cleanup-and-racing-state.md` for final branch state. ⚠️ **That note predates this session — Railway execution IS now verified** (worker `betmate-market-worker-1`, all 7 codes, 8,481 quotes, 0 errors). The standing rule still holds: deployment status is not runtime success. Tipping reminder delivery remains unverified.
**Update this section at the end of every session, before writing the handover diary.**

### NRL Season Phase Tagging — LIVE 2026-07-10 (evidence base for phase-weighted pricing 2027)
User plans to split next NRL season into 4 phases and weight-adjust per phase. Before fitting any weights, the 2026 evidence base is now being built: `BettingEngine/scripts/season_phases.py` tags every round **event-anchored** (early / origin / late / finals + `origin_window` bool), with Origin windows = camp_start → game date + 7 days (covers the backup-fatigue round — R19 was the proof case). Phases are driven by `data/nrl/origin/{season}.json` + round dates in `model.db`, NOT fixed round numbers. AFL gets a descriptive round split only (early ≤8 / mid ≤16 / late ≤23 / finals). `update_clv_running.py` + `generate_model_accuracy.py` now emit `phase`/`origin_window` columns (files regenerate fully, so backfill is automatic). ⚠️ First-read caveat: the running file's "early +9.0% vs origin +2.6%" split is CONTAMINATED — R8/R9 rows are model-CLV supplement (no bets placed). On actual bets (`scripts/clv_phase_report.py`): early +3.8% (7), origin +2.6% (32, incl. R13) — and within Origin, **camp/backup window weeks were the BEST CLV of the season (+5.1%, 13 bets)**; clean Origin-era weeks +2.6% (7). The damage is R13 (12 bets, G1 backup week, ~-0.2% avg) — placed BEFORE backup fatigue was modeled (0.34× rule didn't exist until Jul 7) and its bets have no `placed_date` in the ledger (fill them to test the timing hypothesis). Path to 5-10% Origin CLV: build the T10 post-Origin fatigue mode + post-team-list-only bet timing in Origin weeks. **Rule agreed: one mechanism per phase, no per-tier phase weight sets; fit only to measured per-phase bias at end of season, pooled multi-season, walk-forward.** Late-season phase's missing mechanism = ladder context (resting/tanking) — no tier sees it today.

### Soccer Expansion (EPL / Championship / UCL) — SCAFFOLDED 2026-07-10, HOOK-UP NEXT WEEK
Three new odds-board tabs plumbed end to end, deliberately data-light until the Odds API renews (~Tue Jul 14). Build passing ✅.
- **`lib/sports.ts` — single source of truth for all 5 sports.** Tab order, Odds API keys, endpoints, per-sport feature flags (weather/refs/team-news/predictions/history/BVI/movements — all OFF for soccer). To light up a feature on a soccer tab: flip the flag + wire the data source.
- **`app/api/odds/[league]/route.ts`** — dynamic route serving `/api/odds/{epl|championship|ucl}` (allowlist), same snapshot-fallback pattern as NRL/AFL. `/api/odds` prefix already covers it in middleware PUBLIC_PATHS — no middleware change needed.
- **`lib/soccerTeams.ts`** — EPL (20) / Championship (26) / UCL (28) badge meta. ⚠️ Names seeded blind while the feed is down — **VERIFY against the first live API response** (exact-name rule, same as AFL). Unknown teams degrade to plain text.
- **`app/odds/page.tsx` + `components/layout/Header.tsx`** — tabs driven by `enabledSports()`; soccer tabs share one `soccerGames` state map; refs/venue/weather/predictions/team-news all sport-gated.
- **`scrapers/odds_snapshot.py`** — soccer keys added; snapshots auto-start once the API key works. Monday opening-baseline push stays NRL/AFL only.
- **`lib/affiliate.ts`** — soccer bookmaker landing URLs (competition deep links = hook-up task).

**HOOK-UP TASKS (next week):** (1) verify team names vs live feed, (2) **Draw column** — soccer H2H is 3-way, `extractH2HOdds` currently drops the Draw outcome, (3) totals label (goals 2.5, not points), (4) predictions from BettingEngine `ml/football` (EPL model built Jul 5, Championship Phase 2 in progress) + new `/api/epl-predictions` style routes (**ADD TO PUBLIC_PATHS**), (5) soccer opening baselines if movement arrows wanted, (6) verify bookmaker soccer landing URLs, (7) reconcile 2026-27 promotions/relegations. Note: EPL/Championship are off-season until August; UCL league phase starts September — empty tabs until then are expected, not a bug.

### App State
- Dev server: `npm run dev` → http://127.0.0.1:3000 (use 127.0.0.1 not localhost on Windows)
- Build: passing ✅
- Theme: dark (RacingZone-inspired, black/white/green) — do not revert
- Working pages: `/odds` (NRL + AFL tabs), `/research`, `/tools`
- **Mobile layout: FIXED 2026-05-26** ✅ Root cause was missing `min-w-0` on the CSS Grid item wrapping OddsBoard — chips bar text was inflating the grid track to 978px on a 375px phone, making half of every button row off-screen. All mobile controls (Ask Baz, Details, BVI, H/A Value) now visible and correctly sized. Verified with Playwright.

### Scheduled Tasks (Task Scheduler)
| Task | Schedule | Status |
|------|----------|--------|
| "BetMate Odds Snapshot" | 09:00 + 18:00 daily | ✅ Running |
| "BettingEngine NRL Injuries Fetch" | Tuesday 10:00 | ✅ Fixed path (Apps not Apps\BetMate) |
| "BetMate NRL Historical Results" | Tuesday 16:00 | ✅ Fixed — also runs AFL download |
| "BetMate NRL Style Stats Scrape" | Tuesday 16:15 | ✅ Fixed path |
| "BetMate NRL Round Prep" | Tuesday 16:20 | ✅ Fixed path, time 16:20 |
| "BettingEngine NRL Pricing" | Tuesday 16:45 | ✅ FIXED — now uses wrapper scripts/run_nrl_pricing.ps1 with BETMATE_ROOT |
| "BetMate NRL Emotional Flags" | Tuesday 16:40 | ✅ Runs before pricing so T7 flags are ready; added _load_env, Google News feed, bye-team validation |
| "BetMate AFL Emotional Flags" | Tuesday 16:40 | ✅ Fixed — _load_env, Google News feed, bye-team validation, runs before pricing |
| "BetMate NRL Weekend Injuries" | Monday 07:30 | ✅ NEW — run_weekend_injuries_nrl.ps1 — NRL only (casualty ward updates Sun/Mon) |
| "BetMate AFL Weekend Injuries" | Monday 15:00 | ✅ NEW — run_weekend_injuries_afl.ps1 — scrapes Fox Sports match report articles (server-rendered, available Mon afternoon). Footywire/AFL.com.au don't update until Tue/Wed so we read game write-ups instead. |
| "BetMate AFL BVI" | Monday 08:00 | ✅ Weekly — scrapers/afl_bvi.py → Supabase afl_bvi |
| "BetMate AFL Home Away Value" | Monday 08:10 | ✅ Weekly — scrapers/afl_home_advantage.py → Supabase afl_home_away |
| "BetMate NRL BVI" | Monday 08:20 | ✅ Weekly — scrapers/nrl_bvi.py → Supabase nrl_bvi |
| "BetMate NRL Home Away Value" | Monday 08:30 | ✅ Weekly — scrapers/nrl_home_advantage.py → Supabase nrl_home_away |
| "BettingEngine NRL Referees Fetch" | Wednesday 14:00 | ✅ Moved to Wednesday (refs announced Wed) |
| "BetMate AFL Injuries Fetch" | Tuesday 11:30 | ✅ NEW — scrapers/afl_injuries.py |
| "BetMate NRL Team News" | Tuesday 10:30 | ✅ NEW — scrapers/nrl_team_news.py (auto-generates injuries section; suspensions stay manual) |
| "BetMate AFL Style Stats Scrape" | Tuesday 16:15 | ✅ NEW — scrapers/afl_style_stats.py |
| "BetMate AFL Footywire T2 Snapshot" | Tuesday 16:05 | ✅ NEW 2026-07-09 — BettingEngine/scripts/run_afl_footywire_snapshot.ps1 → footywire_snapshots.csv (the file AFL T2 pricing actually reads; was orphaned — nothing fed it since May 12). Auto round label, append-only, logs to BettingEngine/outputs/logs/ |
| "BetMate AFL Round Prep" | Tuesday 16:20 | ✅ NEW — scrapers/afl_round_prep.py |
| "BetMate Baz Brain" | At logon | ✅ NEW — scripts/start_baz.ps1 (Baz server + CF tunnel) |
| "BetMate NRL History Push" | Wednesday 08:00 | ✅ NEW — scripts/run_push_nrl_history.ps1 → Supabase nrl_match_history |
| "BetMate AFL History Push" | Tuesday 12:00 | ✅ NEW — scripts/run_push_afl_history.ps1 → Supabase afl_match_history (30 min after AusSportsBetting AFL Download at 11:30) |
| "BetMate NRL Predictions Push" | Thursday 09:00 | ✅ NEW — scripts/run_push_nrl_predictions.ps1 → reads r{round}_pricing_2026.csv via fixture, writes data/nrl/predictions/latest.json + Supabase nrl_predictions |
| "BetMate AFL Predictions Push" | Thursday 09:00 | ✅ NEW — scripts/run_push_afl_predictions.ps1 → reads r{round}_afl_2026.csv (highest round by filename), derives scores from rules margin+total, writes data/afl/predictions/latest.json + Supabase afl_predictions |

**Pipeline day is now TUESDAY** (shifted 2026-05-11 — historical odds not ready until Tuesday).
All BetMate tasks use full path `C:\Users\ElliotBladen\.local\bin\uv.exe`.

**CRITICAL RULE — MIDDLEWARE PUBLIC_PATHS (learned 2026-06-04)**
Any new `/api/*` route that a public page fetches MUST be added to `PUBLIC_PATHS` in `middleware.ts` or it returns 401 silently. Client-side fetches catch the error and return null — predictions/data simply don't appear with no visible error. Always add the route to `middleware.ts` in the same commit as the route itself. Both push scripts now run a live endpoint health-check after each push — if you see a WARNING in the log, check middleware first.

**CRITICAL FIX 2026-05-19: BETMATE_ROOT**
BettingEngine's `_find_betmate_root()` was resolving to `Apps\BetMate` (old split repo, no data) instead of `Apps` (actual data location). Fixed by:
- Wrapper script: `BettingEngine/scripts/run_nrl_pricing.ps1` — sets `BETMATE_ROOT=C:\Users\ElliotBladen\Apps` + `PYTHONUTF8=1`, runs prepare_round.py then export_round_csv.py
- Task Scheduler "BettingEngine NRL Pricing" now calls this wrapper via `powershell.exe -File run_nrl_pricing.ps1`
- `ephem` module installed into BettingEngine venv (was missing — caused Step 8 matrix failures)

### Scrapers — Output Locations
| Scraper | Output | Consumed by |
|---------|--------|-------------|
| `scrapers/odds_snapshot.py` | `data/odds_snapshots/YYYY/YYYY-MM-DD.csv` | UI + study |
| `scrapers/odds_movement_tracker.py` | `data/odds_movements/YYYY/YYYY-MM-DD.csv` | UI alerts |
| `scrapers/nrl_injuries.py` | `data/nrl/injuries/processed/latest-injuries.json` | BettingEngine T5 |
| `scrapers/weekend_injury_diff.py` | `data/{nrl\|afl}/injuries/processed/new-this-week.json` + updates `latest-injuries.json` | Monday pipeline step 1 |
| `scrapers/afl_match_reports.py` | `data/afl/injuries/processed/new-this-week.json` | Scrapes Fox Sports AFL Report Card for injury mentions per team. Server-rendered, available Mon afternoon. Known limitation: cross-team mentions in game write-ups may mis-attribute a player. |
| `scripts/update_team_news_injuries.py` | `data/{nrl\|afl}/team-news/latest.json` + Supabase `team_news_nrl`/`team_news_afl` | Monday pipeline step 2 — auto-populates injury section, preserves manual suspensions |
| `scrapers/nrl_emotional.py` | `data/nrl/emotional/processed/latest-emotional.json` | BettingEngine T7 |
| `scrapers/afl_emotional.py` | `data/afl/emotional/processed/latest-emotional.json` | future AFL BettingEngine T7 |
| `scrapers/afl_bvi.py` | `data/afl/bvi/processed/latest-bvi.json` | `/api/afl-bvi` → odds page BVI filter |
| `scrapers/afl_injuries.py` | `data/afl/injuries/processed/latest-injuries.json` | future AFL BettingEngine T5 |
| `scrapers/afl_style_stats.py` | `data/afl/style-stats/processed/latest-style-stats.csv` | future AFL BettingEngine T2 |
| `scrapers/afl_round_prep.py` | orchestrates AFL injuries scrape | runs afl_injuries.py |
| `scrapers/nrl_team_news.py` | `data/nrl/team-news/latest.json` + Supabase `team_news_nrl` | team news UI tab |

### Injury Scraper — Current Source
Source changed 2026-05-05: NRL.com casualty ward (Fox Sports broke).
URL: `https://www.nrl.com/news/{season}/01/01/nrl-casualty-ward-...`
Last scraped: 2026-05-19 (R12, 109 records)

### Weather System

**Provider:** Tomorrow.io (`TOMORROW_API_KEY` in `.env.local`)
**API route:** `app/api/weather/route.ts` — server-side 30-min cache (`revalidate = 1800`, inner fetch is `cache: 'no-store'`)
**Venue lookups:**
- NRL → `lib/venues.ts` (`getVenue`)
- AFL → `lib/aflVenues.ts` (`getAFLVenue`) — all 18 venues wired

**Per-game fetch schedule** (client-side `setTimeout` in `OddsBoardCard`):
| Trigger | When |
|---------|------|
| On load | Immediately when game card renders |
| Pre-game | Exactly 1 hour before kickoff |
| Halftime | 45 min post-kickoff (NRL) / 65 min post-kickoff (AFL) |

**Logging:** Every ping appended to `data/weather/YYYY/YYYY-MM-DD.csv`
Columns: `timestamp, lat, lon, commence_time, temperature, wind_speed, wind_gust, precip_prob, precip_intensity, dew_point, humidity, condition, flags`
Header written once on first ping of the day. Log writes are fire-and-forget (never block the response).

### Odds Board — UI State
- Bookmakers shown: **10** (grid is `repeat(10, minmax(72px,1fr))`, min-w 1100px, horizontal scroll on small screens)
- Team badge rows show **nickname only** (last word of team name) — full name stays in the card header
- Team badges: `lib/teams.ts` exports both `NRL_TEAMS` and `AFL_TEAMS`; `getTeamMeta(name)` checks NRL first then AFL

**IMPORTANT — AFL team name format:** The Odds API sends full mascot names. Keys in `AFL_TEAMS` must match exactly:
`"Fremantle Dockers"`, `"Carlton Blues"`, `"Collingwood Magpies"`, `"Hawthorn Hawks"`, `"Melbourne Demons"`, `"North Melbourne Kangaroos"`, `"Port Adelaide Power"`, `"Richmond Tigers"`, `"St Kilda Saints"`, `"Essendon Bombers"` — NOT the short forms.

### Odds API Budget
~30,000 calls/month. Snapshot task reduced from every-10-min to twice daily (09:00 + 18:00).
Estimated snapshot usage now ~1,440/month. Significant headroom freed up.

### AFL BVI Filter
Checkbox toggle on the AFL odds tab. Badges teams as ▲ Value or ▼ Fade using **role-aware logic**:
1. Determine fav/dog per game from average H2H odds
2. Fav → use `fav_profit`; Dog → use `und_profit` (from aussportstipping.com BVI)
3. Positive role profit → ▲ Value. Negative → ▼ Fade.
4. If both teams compute the same badge (both fade or both value) → suppress both. No actionable signal.
5. Neutral-vs-neutral games are hidden when filter is on.

BVI JSON fields per team: `rank`, `score` (Profit %), `tier`, `fav_profit`, `und_profit`

**SCRAPER BUG HISTORY:** Original scraper was capturing game count (#) not profit — values were 28/27/26... (games played). Fixed 2026-05-11 to specifically parse `$`-prefixed values under `Fav:` / `Und:` labels.

- API: `/api/afl-bvi` → serves `data/afl/bvi/processed/latest-bvi.json`
- Scraper: `scrapers/afl_bvi.py` — run manually or via Task Scheduler
- **Pending:** weekly Task Scheduler task to auto-refresh BVI data (not yet installed)

### Model Predicted Scores — LIVE 2026-05-28
- `data/nrl/predictions/latest.json` — NRL predictions (keyed by Odds API home team name)
- `app/api/nrl-predictions/route.ts` — GET `/api/nrl-predictions` → returns `{ predictions: [...] }`
- `OddsBoardCard` — shows "Model: SHARKS 28.9 – EAGLES 23.9" line below venue on each card (mobile + desktop)
- **Team name mapping critical:** Odds API names differ from BettingEngine CSV names:
  - `"Cronulla-Sutherland Sharks"` → `"Cronulla Sutherland Sharks"` (no hyphen)
  - `"Manly-Warringah Sea Eagles"` → `"Manly Warringah Sea Eagles"` (no hyphen)
  - `"Canterbury-Bankstown Bulldogs"` → `"Canterbury Bulldogs"` (short form)
  - `"St. George Illawarra Dragons"` → `"St George Illawarra Dragons"` (no period/hyphen)
- **To update each round:** edit `data/nrl/predictions/latest.json` with new round scores (use Odds API names, not BettingEngine CSV names). AFL automation TBD.

### History Tab — LIVE 2026-05-27
- `app/api/form/route.ts` — GET `/api/form?home=X&away=Y&sport=S` → reads `nrl_match_history` from Supabase, returns `{ homeForm, awayForm, h2h }` (last 6 each)
- `scripts/push_nrl_history.py` — reads `data/nrl/historical/latest.xlsx` (2024+), pushes 514 matches to Supabase key `nrl_match_history`. Re-run weekly after Tuesday download.
- `HistoryTab` in `app/odds/page.tsx` — fetches `/api/form` on mount, shows three tables: home team last 6, away team last 6, H2H last 6
- Nickname matching: last word of full Odds API name (e.g. "Cowboys") used for case-insensitive contains match against Excel team strings
- AFL: **LIVE 2026-06-05** ✅ — `scripts/push_afl_history.py` pushes 961 matches (2022+) to Supabase `afl_match_history`. Team name mapping critical: xlsx uses short names ("Hawthorn") → push script normalises to full Odds API names ("Hawthorn Hawks") so nickname matching works for all 18 teams. Automation TBD (discuss with user).

### Team News System — AUTO-INJURIES 2026-06-01
- `data/nrl/team-news/latest.json` — NRL team news (injuries auto-populated, suspensions manual)
- `data/afl/team-news/latest.json` — AFL team news (injuries auto-populated, suspensions manual)
- `app/api/team-news/nrl/route.ts` + `app/api/team-news/afl/route.ts` — API routes (public)
- UI: DetailDrawer Team News tab shows real data; chip shows Alert/Monitor status
- **Monday 07:30 (automated):** `scripts/run_weekend_injuries.ps1` runs two steps:
  1. `scrapers/weekend_injury_diff.py` — scrapes fresh, diffs vs last known, writes `new-this-week.json`
  2. `scripts/update_team_news_injuries.py` — reads `new-this-week.json`, puts ONLY weekend-new injuries into team news, pushes to Supabase
- **Source is `new-this-week.json` (the diff), NOT the full casualty ward** — team news = what's fresh this weekend only
- Each Monday resets injury items to that week's new/worsened batch. Old injuries drop off automatically.
- **Suspensions stay manual** — edit `latest.json` directly, then run `scripts/update_team_news_injuries.py --sport NRL` to push
- Severity: NRL uses `importance_tier` from scraper (elite→high, key→medium, rotation→low). AFL defaults to low.
- Teams with any high/medium severity item → status `"alert"`. Others → `"monitor"`.

### BVI + H/A Value Controls — moved to per-card (2026-05-18)
- Removed from global header (no more header toggles or Search button)
- Each game card now has independent BVI and H/A Value toggle controls
- Design: split-box top-right (left=checkbox, divider, right=ℹ️ popup), stacked below Ask Baz/Details

### Vercel Deployment — LIVE 2026-05-20
- URL: `bet-mate-ten.vercel.app` ✅ (custom domain pending)
- GitHub: `github.com/elliotbladen/BetMate` ✅ — auto-deploys on push to main
- Supabase `betmate_data_store` table: keys include afl_bvi, afl_home_away, nrl_bvi, nrl_home_away, nrl_fixture, team_news_nrl, team_news_afl, nrl_opening_baseline, afl_opening_baseline, odds_movements ✅
- All API routes migrated to Supabase-first with local fallback ✅
- `lib/matrixEV.ts` — Vercel guard added (returns [] if BettingEngine outputs missing) ✅
- `lib/referees.ts` — static JSON imports removed (refs show blank on Vercel) ✅
- `data/` excluded from git (gitignore updated) ✅
- EV signals (arrows) blank on Vercel — intentional, BettingEngine IP stays local. Fix via Cloudflare Tunnel when ready.
- **Odds movement arrows WORKING on Vercel as of 2026-05-22** ✅ — Monday baseline → Supabase → arrows on every price cell

### Odds Movement System — HOW IT WORKS (2026-05-22)
**Monday 09:00 snapshot** → `odds_snapshot.py` runs (via Task Scheduler) → also calls `push_opening_baseline()` which stores NRL + AFL prices under `nrl_opening_baseline` / `afl_opening_baseline` keys in Supabase.

**Every subsequent snapshot** (09:00 + 18:00 Tue–Sun) → `odds_movement_tracker.py` runs via wrapper → reads `latest.csv`, fetches baselines from Supabase, detects movements, pushes to Supabase key `odds_movements`.

**Vercel frontend** → `/api/odds/movements` → `getDataStore('odds_movements')` → returns movement map → arrows shown on price cells.

**Key format:** `{game_id}:{market}:{bookmaker}:{side}` where market = `h2h` / `spreads` / `totals` and side = `home` / `away` / `over` / `under`.

**CRITICAL BUG FIXED (2026-05-22):** `getDataStore` used `.single()` which fails when duplicate rows exist for a key. Changed to `.limit(1)` so any duplicate rows are tolerated. Root cause: tracker was run twice (no UNIQUE constraint on `key` column in Supabase).

**To manually refresh movements:**
```powershell
cd C:\Users\ElliotBladen\Apps
& C:\Users\ElliotBladen\.local\bin\uv.exe run --with requests --with tzdata python scrapers/odds_movement_tracker.py
```

**To seed baseline manually** (if Monday task missed or for testing):
```powershell
& C:\Users\ElliotBladen\.local\bin\uv.exe run --with requests python scripts/seed_test_baseline.py
```

### Market Event Causal-Tagging Pipeline — BUILT 2026-07-03
**Why:** The odds movement system above tells you a line moved, not why. This pipeline is the first step toward a line-movement prediction engine (bet early/late based on which way a line will move) — it links price moves to the news events that plausibly caused them, building a labelled dataset over time.

**Three scripts, in order:**
1. `scripts/build_market_event_log.py --season 2026` — scans dated archives from the injury scrapers (`data/{sport}/injuries/processed/{season}/round-*-injuries.json`), emotional-flag scrapers (`round-*.json`), and team-news archive (see below) → writes `data/market_events/{season}_events.csv` (timestamp, sport, event_type, team, player, detail).
2. `scripts/compute_snapshot_deltas.py --season 2026` — reads every raw snapshot in `data/odds_snapshots/{season}/*.csv` and computes **every consecutive snapshot-to-snapshot delta** per (sport, game_id, bookmaker, market, outcome) series — not just "now vs Monday baseline" like the movement tracker above. Writes `data/odds_movements/deltas/{season}_deltas.csv`.
3. `scripts/tag_odds_movements.py --season 2026` — joins deltas (≥3% change, filters exchange lay bad-ticks >300%) against the event log: does a same-sport, same-team event fall inside the delta's time window? Writes `data/odds_movements/tagged/{season}_tagged.csv` with a `drivers` column (or `unexplained`).

**Current state (first backfill, 2026-07-03):** 5154 significant moves found season-to-date, only ~10% get a driver tag. That's expected and honest — most of what we scrape is injuries; we don't yet tag weather updates, public-betting-% shifts, or sharp-money signals, and our snapshot cadence (3x/day) means windows can span many hours early in the season. The 90% "unexplained" bucket is exactly what a real line-movement model would need to explain via other means (momentum/steam-following, scheduled-news timing) — this pipeline's job is to shrink that bucket over time, not solve it in one pass.

**Team-news archiving added:** `scripts/update_team_news_injuries.py` previously only wrote `latest.json` (overwritten every run, no history). Now also writes a dated copy to `data/{sport}/team-news/archive/{season}/r{round}_{timestamp}.json` so future team-news updates feed the event log too. No backfill possible for past weeks — this starts building history from now.

**Reactive snapshots — 7 new scheduled tasks (2026-07-03), ~10min after each causal-driver scraper**, so future weeks get tight before/after windows instead of relying on the flat 09:00/12:00/17:40 cadence:
| Task | Fires |
|------|-------|
| BetMate Odds Snapshot - React NRL Injuries | Tue 10:10 (10min after NRL Injuries Fetch) |
| BetMate Odds Snapshot - React NRL Team News | Tue 10:40 |
| BetMate Odds Snapshot - React AFL Injuries | Tue 11:40 |
| BetMate Odds Snapshot - React Emotional Flags | Tue 16:30 (covers both NRL+AFL, both fire 16:20) |
| BetMate Odds Snapshot - React NRL Referees | Wed 14:10 |
| BetMate Odds Snapshot - React NRL Weekend Injuries | Mon 07:40 |
| BetMate Odds Snapshot - React AFL Weekend Injuries | Mon 08:10 |

All just call the existing `run_odds_snapshot_cycle.ps1` — safe to run anytime, purely additive.

**Weekly rebuild:** `BetMate Market Event Pipeline` task, Thursday 08:00 — runs all 3 scripts above via `scripts/run_market_event_pipeline.ps1`.

**Reality check on timeline:** this is instrumentation, not a finished predictive engine. AFL+NRL combined is ~350-400 games/season with multiple distinct movement mechanisms (news-driven, weather, pure money flow) — expect this needs a full season of properly-tagged data before there's enough to train anything trustworthy, not just "wait until October."

### Cloudflare Tunnel — LIVE ✅
- Tunnel: `betmate-baz` (ID: `ce4bfb19-82f6-4ffe-af06-e2c65636a323`)
- DNS: `baz.betmate.au` → Cloudflare IPs → `localhost:8765` ✅
- Config: `C:\Users\ElliotBladen\.cloudflared\config.yml`
- `BAZ_TUNNEL_URL=https://baz.betmate.au` set in Vercel production env ✅
- `app/api/chat/route.ts` uses `BAZ_TUNNEL_URL ?? BAZ_LOCAL_API ?? localhost:8765`
- Start script: `scripts/start_baz.ps1` — kills stale cloudflared, starts Baz server, starts tunnel, health checks
- **Baz is ONLINE on betmate.au** — `X-Baz-Brain: online` confirmed ✅

**To start Baz + tunnel:**
```powershell
& C:\Users\ElliotBladen\Apps\scripts\start_baz.ps1
```

**If tunnel drops:** re-run `start_baz.ps1`. Baz will show "Brain offline" banner on site until tunnel reconnects.

### Supabase Push — Weekly scraper updates
Scrapers now push to Supabase automatically after local write:
- `afl_bvi.py` → key `afl_bvi`
- `afl_home_advantage.py` → key `afl_home_away`
- `nrl_fixture.py` → key `nrl_fixture`
- Team news (manual): run `uv run --with requests python scripts/push_team_news.py` after editing JSON files
- Requires `SUPABASE_SERVICE_ROLE_KEY` in `.env.local`

### Round Pricing — Current Files
| File | Location | Generated | Notes |
|------|----------|-----------|-------|
| `r12_pricing_2026.csv` | `BettingEngine/results/` | 2026-05-21 | NRL R12 — 5 games, T1–T8 |
| `r11_afl_2026.csv` | `BettingEngine/results/` | 2026-05-21 | AFL R11 — 9 games, T1–T4 rules + ML shadow |
| `r12_round_pricing_2026.md` | `BettingEngine/outputs/results/` | 2026-05-21 | NRL R12 full analysis + Origin overlays + matrix signals |
| `r11_afl_pricing_2026.md` | `BettingEngine/outputs/results/` | 2026-05-21 | AFL R11 full analysis + ML divergence + injury notes |

**To run pricing manually:**
```powershell
# NRL — sets BETMATE_ROOT, runs prepare_round + export
& C:\Users\ElliotBladen\Apps\BettingEngine\scripts\run_nrl_pricing.ps1

# AFL — rebuild ELO first, then price
cd C:\Users\ElliotBladen\Apps\BettingEngine
$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"; $env:PYTHONUTF8 = "1"
& ".\.venv\Scripts\python.exe" ml\afl\game_log.py --xlsx outputs\afl_weekly_review\historical\latest.xlsx
& ".\.venv\Scripts\python.exe" scripts\prepare_afl_round.py --season 2026 --round 12
& ".\.venv\Scripts\python.exe" scripts\_export_afl_prices.py
```

### NRL R13 — Results + CLV (2026-05-29–31) ⚠️ NEGATIVE CLV ROUND
- **Net result: -$38.50 (~-0.77 units). All lines/totals/H2H moved against bets placed.**
- **CLV flag:** Every market (H2H, handicap, totals) shifted in the unfavourable direction after bets were placed. Pattern to watch — if this repeats across R14/R15 it suggests timing issue (betting too early before sharp money arrives) or model overconfidence on handicap signals.
- **What landed:** Cronulla H2H ✅ (7-way confluence paid off), Under 46.5/47.5 Panthers/Warriors ✅ (model 44.1 was correct)
- **What missed:** Panthers -3.5/-5.5 ❌ (model had by 12.7 — significant miss), Cowboys +4.5 ❌ (Raiders/Cowboys 3-way matrix failed), Carlton/Geelong OVER 178.5 AFL ❌
- **Key pricing notes (original):** 4/7 refs loaded, T8 weather Suncorp wind -2.0 on Broncos/Dragons total. Cronulla -2.5 HIGH (7-way matrix + model -4.9). Panthers/Warriors UNDER 48.5 HIGH (8-way matrix + model 44.1). Panthers -7.5 MEDIUM (model 12.7 — market was right, Panthers barely won or lost).
- Pricing files: `BettingEngine/results/r13_pricing_2026.csv` + `BettingEngine/outputs/results/r13_nrl_pricing_2026.md`

### AFL R12 — Results + CLV (2026-05-28–31) ⚠️ MIXED
- **Net result (AFL bets only): -$57.52. Lines moved against positions.**
- **What landed:** Hawthorn -19.5 ✅ ($25), Essendon H2H cash out ✅ (+$19.98 — smart exit, Eagles won the game)
- **What missed:** Carlton/Geelong OVER 178.5 ❌ (4-way confluence failed), Collingwood H2H vs Bulldogs ❌, Essendon H2H @ 2.39 ❌ (West Coast won — model Bombers by 0.5 was wrong)
- **CLV note:** Eagles +10.5 was the strong signal but user didn't take it — instead backed Essendon H2H which was against the model's handicap signal. The model correctly priced West Coast as live but was beat.
- **Key pricing notes (original):** T6 emotional (Essendon new_coach_bounce +2.5). T7 weather Optus wind -2.8 on total. Collingwood +7.5 HIGH (ruck crisis). Eagles +10.5 HIGH. Hawks -12.5 MEDIUM.
- Pricing files: `BettingEngine/results/r12_afl_2026.csv` + `BettingEngine/outputs/results/r12_afl_pricing_2026.md`

### NRL R12 — Key Pricing Notes (2026-05-21)
- Refs confirmed: Todd Smith (Raiders/Dolphins), Wyatt Raymond (Bulldogs/Storm), Grant Atkins (Cowboys/Rabbitohs)
- **Origin overlay applied manually** — casualty ward scraper misses Origin absences. See .md file for full adjustments.
- Cowboys/Rabbitohs: **triple matrix confluence backing Cowboys** (Sunday + long rest + H2H). Bet signal.
- Bulldogs/Storm: Handicap triple confluence → Bulldogs cover. H2H conflicted (no bet).
- Totals: model known to run 5–10pts high. Use with caution vs market lines.

### AFL R11 — Key Pricing Notes (2026-05-21)
- **T9 note:** ML shadow divergences are the key signal this round — rules model overcooks home teams
- Top signals: Cats/Swans UNDERS (ML 158 vs rules 209, 51pt gap) | Giants cover vs Lions | Kangaroos cover vs Suns | Crows cover vs Hawks
- Injury scraper classifies all players as "average" — manual overlays needed for elite absences (Connor Rozee out for Port, Sean Darcy out for Fremantle, Tim English out for Bulldogs)
- AFL totals model runs ~5.8pts BELOW actual after 2026-05-27 retrain (was ~8pts). On a game-by-game basis direction varies significantly.

### BettingEngine Data Folder Structure (updated 2026-05-25)

All output data lives in `BettingEngine/data/` with consistent naming: `{SPORT}_{TYPE}_R{rr:02d}_{YYYY-MM-DD}[_suffix].csv`

```
BettingEngine/data/
├── bets/
│   ├── actual_bets_2026.csv              master ledger (44 bets as of R12)
│   └── weekly/                           YYYY-MM-DD_AFL-RXX_NRL-RXX.csv
├── clv/
│   ├── nrl/                              NRL_CLV_R{rr}_{date}[_ml_comparison|_ml_shadow|_rules_vs_ml|_manual].csv
│   ├── afl/                              AFL_CLV_R{rr}_{date}[_suffix].csv
│   └── running/
│       ├── actual_bets_clv_2026.csv      per-bet CLV (fill after each round)
│       ├── model_clv_supplement_nrl_2026.csv  R8/R9 model CLV (no actual bets)
│       ├── NRL_CLV_running_2026.csv      running total — currently +5.27% LINE-ADJ (R8–R15, 55 bets, 70.9% +ve)
│       └── AFL_CLV_running_2026.csv      running total — currently +0.76% LINE-ADJ (R8–R14, 43 bets, 46.5% +ve)
├── model_accuracy/
│   ├── nrl/                              NRL_MODEL_ACCURACY_R{rr}_{date}.csv
│   ├── afl/                              AFL_MODEL_ACCURACY_R{rr}_{date}.csv
│   └── MODEL_ACCURACY_RUNNING_2026.csv   rules vs ML vs market — running bias table
└── pricing/
    ├── nrl/                              NRL_PRICING_R{rr}_{date}[_ml_shadow|_tier_breakdown].csv
    └── afl/                              AFL_PRICING_R{rr}_{date}[_suffix].csv
```

**Post-CLV scripts (run Tue after closing lines filed):**
```powershell
cd C:\Users\ElliotBladen\Apps\BettingEngine
& C:\Users\ElliotBladen\.local\bin\uv.exe run python scripts\update_clv_running.py
& C:\Users\ElliotBladen\.local\bin\uv.exe run python scripts\generate_model_accuracy.py
# After new round priced — add to SOURCES list first:
& C:\Users\ElliotBladen\.local\bin\uv.exe run python scripts\convert_pricing_files.py
```

### AFL Pricing Model — Calibration State (updated 2026-06-10)
**Key constants in `BettingEngine/scripts/prepare_afl_round.py`:**
| Constant | Value | Notes |
|----------|-------|-------|
| `POINTS_PER_ELO` | `0.09` | was 0.13 — reduced to stop mid-range ELO gaps overcooking margins |
| `HOME_ADV_ELO` | `46.0` | used for dedicated venues (~4.1 pts) |
| `VENUE_HOME_ADV_OVERRIDES` | MCG/Marvel = 15 | shared venues get 1.4 pts home advantage |
| `T2_MAX` | `4.0` | was 7.0 — was hitting cap constantly and piling 7pts onto already-large T1 |
| `T2_TOT_MAX` | `2.0` | was 3.0 |

**T5 Injury Impact Table — current values (`BettingEngine/pricing/afl_tier5_injury.py`):**
| Position | Elite | Good | Average |
|----------|-------|------|---------|
| key_forward | -5.0 hcp / -4.0 tot | -3.0 / -2.0 | -2.0 / -1.5 |
| ruck | -3.5 / -2.0 | -2.0 / -1.0 | -1.0 / -0.5 |
| key_defender | -2.5 / +1.5 | -1.5 / +1.0 | -0.5 / +0.5 |
| midfielder | -3.0 / -1.5 | -1.5 / -0.5 | -0.5 / -0.5 |
| small_forward | -1.5 / -0.5 | -1.0 / -0.5 | -0.5 / 0.0 |
| winger | -1.5 / -0.5 | -1.0 / -0.5 | -0.5 / 0.0 |

Changes made 2026-06-10: key_forward good −3.5→−3.0, midfielder elite −3.5→−3.0, midfielder good −2.0→−1.5. Research shows midfielder importance declining in modern AFL (contested ball only 60% predictive vs 70%+ historical). Cap remains ±8 hcp / ±6 tot. Compound dampener 0.85× at 2+ key players out.

**CRITICAL DATA ENTRY RULE — INJURIES:** Season-ending injuries (knee — season, ACL etc.) must be re-entered in EVERY subsequent round's INJURIES dict manually. They do NOT carry forward automatically. Missing a season-ender (e.g. Tom Green missing from R14) can inflate the injury delta by 3-4pts. Check each round's GWS, Brisbane, Bulldogs etc. for known season-enders.

**Known remaining gap vs market:** ~9-10pt average after all fixes. Root cause is linear ELO→margin conversion can't handle both moderate and extreme ELO gaps simultaneously. True fix is probability-based sigmoid mapping (`(win_prob-0.5) × 95`) — flagged for next AFL session.

**AFL R14 final prices (post all fixes):**
| Game | Model | Market |
|------|-------|--------|
| Bulldogs vs Crows | Crows -7.4 | Bulldogs -4.5 |
| Cats vs Suns | Cats -36.8 | Cats -25.5 |
| Demons vs Bombers | Demons -34.9 | Demons -30.5 ✅ |
| Kangaroos vs Eagles | NM -27.4 | NM -6.5 |
| Power vs Swans | Swans -16.2 | Swans -17.5 ✅ |
| Tigers vs Lions | Lions -30.5 | Lions -46.5 |
| Saints vs Giants | Giants -12.2 | Giants -2.5 |

### BETTING RULE — Model Alignment Required (established 2026-06-17)
Only take a handicap, H2H, or totals bet if **both** the rules model AND the ML model agree on the direction:
- **Handicap:** both `rules_margin` and `ml_margin` must point to the same team winning
- **H2H:** both `rules_home_odds` and `ml_h2h` must favour the same side
- **Totals:** both `rules_total` and `ml_total` must be on the same side of the market line
- If models disagree (e.g. rules has GWS -28, ML has Carlton +5) → **DO NOT BET** either side
- Reason: CLV analysis showed AFL handicap at -2.41% avg. Several misses involved rules/ML disagreement.

### Pending Work
- **Market event pipeline check-in — due 2026-07-24:** scheduled task "BetMate Market Event Pipeline Checkin" fires that day and writes a report to `data/market_events/checkins/2026-07-24.md` (also Windows toast notification). Review: has the ~90% unexplained rate shrunk, have snapshot windows tightened since reactive snapshots went live, are all 7 reactive tasks + weekly rebuild actually firing. Run `uv run python scripts/check_market_event_pipeline.py` manually any time for a fresh read. See handover `2026-07-03_market-event-tagging-pipeline.md`.
- ~~**T10 Origin Layer**~~ ✅ **LIVE 2026-06-09** — `BettingEngine/pricing/tier10_origin.py` + `data/nrl/origin/2026.json`. Auto-detects Origin camp windows, applies same formula as T5. G1 squad fully populated. G2 (Jun 17, camp Jun 12) + G3 (Jul 8, camp Jul 3) squads need populating before those rounds. DB migration 024 applied. See handover `2026-06-09_t10-origin-layer.md`.
- **Custom domain betmate.au:** DNS resolving ✅, SSL cert provisioning. `www.betmate.au` CNAME still points to wrong site — needs updating in Cloudflare + Vercel domain added
- **EV signals on Vercel:** wire via Cloudflare Tunnel once domain + tunnel ready
- ~~BVI weekly task~~ ✅ All 4 tasks installed — "BetMate NRL BVI" (Mon 08:20) + "BetMate NRL Home Away Value" (Mon 08:30) first run 2026-05-25
- Odds movement alerts: add threshold filter (only alert if change_pct >= 10%)
- **AFL rules model — sigmoid ELO scaling (next AFL session):** `POINTS_PER_ELO` linear mapping can't calibrate both moderate and extreme ELO gaps simultaneously. Replace with `(win_prob - 0.5) × SCALE` where win_prob is logistic from ELO diff. Calibrate SCALE against 2026 closing lines after R18. Estimate SCALE ≈ 90-100. See handover `2026-06-10_afl-calibration-overhaul.md`.
- **AFL rules model — set-shot conversion tracker (medium term):** pull weekly team kicking % from AFL Tables, apply ±2-3pt adjustment per 5% deviation from 52.5% league average. AFL-specific, no NRL equivalent.
- **AFL rules model — xScore ELO inputs (next pre-season, Oct 2026):** Currently ELO updates on raw score margin, which bakes in kicking accuracy variance. Replace with expected score margin: `xScore = scoring_shots × 3.70` (where 3.70 = 6×0.54 + 1×0.46, league avg conversion). Freo R15 example: 29 shots = 107 xScore vs actual 99 — ELO would correctly reflect their dominance. Data needed: scoring shots per team per game (already in AFL Tables xlsx). No new data source required for basic version. Enhanced version (per-shot distance/angle) needs Champion Data or scraping AFL.com.au shot maps. Build basic version first, assess improvement before investing in per-shot data. Mid-season accuracy dip (R13-17) is seasonal/weather-driven not streak-based — xScore normalises this automatically.
- **AFL ML model RETRAINED 2026-06-04** — training window extended to **2022–2024** (was 2022–2023). Train games: 639 (was 423, +51%). Test holdout: 2025 (n=216). New metrics: Margin MAE 30.45 (was 31.72), Total MAE 24.31 (was 24.61), H2H Acc 66.7% (was 65.7%), H2H LogLoss 0.673 (was 0.830). Fresh xlsx (`outputs/afl_weekly_review/historical/latest.xlsx`, Jun 2 download, 816KB, covers R1–R12 2026) used — deploy set now 106 games (was 63). `game_log.py` default XLSX now points to `outputs/afl_weekly_review/historical/latest.xlsx` (auto-uses weekly download). End-of-season retrain (Oct 2026): add 2025 to train, make 2026 test.
- **NRL H2H home bias:** Rules model overrates home teams by +9–11% vs market. ML shadow much better (+1–6%). Consider T4 venue calibration review.
- **R12 CLV:** Not yet filed — opening/closing lines pending. Run scripts after filing.
- **Refs on Vercel:** wire `lib/referees.ts` to an API route + Supabase key so ref badges show on live site
- **T9 Matrix tier:** end-of-2026 review. Weighted by sample size (N<10=0.3, N10-25=0.6, N25+=1.0). Triple confluence cap 10%. See memory file.
- **Supabase UNIQUE constraint:** Add UNIQUE constraint on `key` column in `betmate_data_store` so `resolution=merge-duplicates` actually merges instead of inserting duplicates. Currently `getDataStore` works around this with `.limit(1)` but the root cause should be fixed in Supabase SQL editor: `ALTER TABLE betmate_data_store ADD CONSTRAINT betmate_data_store_key_unique UNIQUE (key);`

### Baz Agent — MCP PHASE 1 LIVE 2026-06-01
- `BettingEngine/baz_server.py` — FastAPI local context server, localhost:8765. Endpoints: `/health`, `/meta?sport=`, `/context/round?sport=NRL|AFL`, `/context/game`, `/signals?sport=`, `/clv`, `/context/team`
- **MCP Phase 1 (2026-06-01):** `app/api/chat/route.ts` now uses Claude Tool Use agentic loop. Slim system prompt (~600 tokens) + 4 tools: `get_round_signals`, `get_game_context`, `get_team_context`, `get_performance`. Claude fetches only what it needs per question instead of a static full-round data dump.
- **`/signals?sport=` enriched:** returns matrix signals (H2H + handicap aligned) + totals signals (clean confluence) + H2H EV signals ≥20% + games summary with model lines
- **`/meta?sport=`:** returns `{round, season, sport}` only — ~5ms call to seed system prompt round number
- **AFL context:** `/context/round?sport=AFL` reads latest `r*_afl_*.csv`, includes ML model data alongside rules model. AFL confluence from `outputs/afl_t9_confluence_latest.json`
- `app/api/chat/route.ts` — fetches from `BAZ_TUNNEL_URL` (Vercel) or `BAZ_LOCAL_API` (local). Tool executor `bazFetch()` has 3s timeout. `sport` forwarded to all tool calls.
- `BAZ_TUNNEL_URL=https://baz.betmate.au` — set in Vercel ✅
- Cloudflare tunnel: `betmate-baz` (ID: ce4bfb19-82f6-4ffe-af06-e2c65636a323) → `baz.betmate.au` → `localhost:8765` ✅
- `components/chat/ChatPanel.tsx` — parses brain status token from stream, shows "Brain offline" amber banner when BettingEngine is down. Sends `sport: games[0]?.sport ?? 'NRL'` in every fetch body.
- ChatPanel.tsx has a double-encoding issue with box-drawing chars (pre-existing, not introduced here). Future edits to this file: use PowerShell file manipulation, NOT the Edit tool — it inserts curly quotes.

**Baz auto-starts on login via Task Scheduler ("BetMate Baz Brain")**
Script: `scripts/start_baz.ps1` — starts baz_server.py + cloudflared tunnel

**To start Baz manually (if task didn't fire):**
```powershell
& C:\Users\ElliotBladen\Apps\scripts\start_baz.ps1
```

**To verify Baz is online:**
```powershell
Invoke-RestMethod https://baz.betmate.au/health
```

### Product Vision — SaaS + Crypto Agent
**⚠️ Baz roadmap replaced 2026-07-09** — the May 2026 plan (alert types, Telegram delivery, crypto-twin agent, self-learning tiers) is abandoned. **The new direction is Baz v2: answer ALL bet-related questions for a game** — full plan, question taxonomy, and build phases in `handover/baz_v2_direction.md`. Read that doc before any Baz work. The deployment architecture below is built reality and still stands.

BetMate is being built as a SaaS community product. Baz is the lead AI agent across both BetMate (sports) and a planned crypto AI agent.

**Target architecture:**
- **Vercel** — Next.js frontend (always on, public)
- **Supabase** — all data storage (odds, team news, BVI, user accounts, snapshots)
- **Cloudflare Tunnel** — exposes Baz (local → internet, IP stays private)
- **VPS ($5-10/mo)** — when traffic justifies, move BettingEngine + Baz off local machine
- **MCP layer** — makes Baz domain-agnostic (sports MCP server + crypto MCP server, same brain)

**Key principle:** The pricing IP (BettingEngine) never lives on the public internet. Cloudflare Tunnel routes requests to wherever the brain is running (local or VPS). "Brain offline" banner already handles graceful degradation.

**Pre-launch blocker resolved 2026-05-20:** Supabase migration complete, site live on Vercel. Cloudflare Tunnel pending domain.

---

## HANDOVER RULE
Write a diary entry to `handover/sessions/YYYY-MM-DD_description.md` at the end of EVERY session.
No exceptions.

---

## PROJECT OVERVIEW

BetMate is a Next.js frontend that:
1. Shows live odds from The Odds API (NRL + AFL)
2. Runs Python scrapers that feed data into BettingEngine (injuries, style stats)
3. Tracks odds snapshots and price movements intraday

### Tech Stack
- Next.js (TypeScript)
- The Odds API for market data
- Python scrapers (run via `uv`, Task Scheduler on Windows)
- Supabase (auth + some data)

### Environment Setup (NEW MACHINE)
**Do this EVERY time on a fresh pull. Missing .env.local = everything broken.**

1. Copy `.env.local.example` → `.env.local`
2. Fill in:
   ```
   ODDS_API_KEY=<key>
   NEXT_PUBLIC_SUPABASE_URL=<url>
   NEXT_PUBLIC_SUPABASE_ANON_KEY=<key>
   ```
3. `npm install`
4. `npm run dev`

"No games" or empty odds = missing `.env.local`. This is NEVER a code bug.

### Running Python Scrapers
```powershell
# Use uv — full path required for Task Scheduler:
& C:\Users\ElliotBladen\.local\bin\uv.exe run python scrapers/odds_snapshot.py
& C:\Users\ElliotBladen\.local\bin\uv.exe run python scrapers/nrl_injuries.py

# uv cache is local to avoid permission issues:
# BetMate\.uv-cache
```

### Key Files
| File | Purpose |
|------|---------|
| `scrapers/odds_snapshot.py` | Pulls odds from API, appends to dated CSV |
| `scrapers/odds_movement_tracker.py` | Diffs last two snapshots, writes movements CSV |
| `scrapers/nrl_injuries.py` | Scrapes NRL.com casualty ward |
| `scripts/run_odds_snapshot_cycle.ps1` | Wrapper: runs snapshot + movement tracker |
| `scripts/install_odds_snapshot_task.ps1` | Installs twice-daily snapshot task (09:00 + 18:00, StartWhenAvailable) |
| `app/api/weather/route.ts` | Weather API proxy (Tomorrow.io) + ping logger |
| `lib/teams.ts` | NRL + AFL team badge colours/abbrs — keys must match Odds API names exactly |
| `lib/venues.ts` | NRL home team → venue coords |
| `lib/aflVenues.ts` | AFL home team → venue coords |
| `data/weather/YYYY/YYYY-MM-DD.csv` | Weather ping log (auto-created) |
| `scrapers/afl_bvi.py` | Scrapes AFL BVI from aussportstipping.com — run weekly |
| `app/api/afl-bvi/route.ts` | Serves BVI JSON to the odds page |
| `data/afl/bvi/processed/latest-bvi.json` | BVI data (18 teams, rank + score + tier) |
| `BettingEngine/scripts/matrix_confluence.py` | T9 confluence analyser — run after fixture loads, flags games with 3+ matrix edges ≥20% same direction |
| `BettingEngine/scripts/generate_clv_txt.py` | Generates formatted CLV TXT from weekly CLV report CSV — `python generate_clv_txt.py --sport NRL --season 2026 --round 11` |
| `BettingEngine/scripts/rolling_clv_summary.py` | Rolling CLV across rounds — reads ml_comparison CSVs, writes `outputs/clv_running/running_clv_summary.csv` |
| `BettingEngine/outputs/clv_running/running_clv_summary.csv` | Running CLV R9–R11 (NRL). Update after each round's ml_comparison is generated. |

### Dev Server Issues
If `.next` build cache corrupts (symptom: `Cannot find module './948.js'`):
```powershell
Stop-Process -Name node -Force
Remove-Item -Recurse -Force .next
npm run dev
```
