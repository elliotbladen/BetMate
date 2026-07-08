# BetMate — Claude Context

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
- **Start of session:** `& scripts\git-sync-start.ps1` — refuses to pull over a dirty
  tree, fast-forward only, never auto-merges divergence.
- **End of session:** `& scripts\git-sync-end.ps1 "what happened"` — commits everything
  and pushes. NEVER leave a machine with uncommitted work.
- `git config pull.ff only` is set on the work machine — set it on the home machine too.
- If sync-start reports divergence: stop and reconcile deliberately (diff both sides,
  keep the newer of each file) — never `git checkout --` or `git reset --hard` blind.
- Untracked model artefacts (`ml/afl/results/models/*.pkl`) do NOT travel via git —
  retrain locally after pulling ML code changes.
- **Known outstanding:** diary `2026-07-05_afl-ema-form-split-models.md` exists only on
  the home computer — commit + push it from there.

---

## CURRENT STATE
**Last updated:** 2026-07-09 (Post-reconcile cleanup on work machine: AFL ML pkl models **regenerated with the Jul 5 EMA/split-feature code** ✅ (margin MAE 29.3 / H2H 68.5% on 2025 holdout, Jul 7 xlsx); stale nested `BettingEngine/.git` (pre-monorepo repo, fully pushed to github.com/elliotbladen/BettingEngine) moved out of the tree to `C:\Users\ElliotBladen\Backups\BettingEngine-pre-monorepo.git` — git commands inside BettingEngine now correctly hit the monorepo; root `.pytest_cache/` gitignored (was an unreadable elevated-process dir spamming warnings). Missing reconcile diary written retrospectively. Prior, 2026-07-08: git divergence between work/home machines reconciled — commit `cefe758`, see TWO-MACHINE RULE above and handover `2026-07-08_machine-reconcile-architecture.md`. EPL engine (built at home Jul 5) restored to `BettingEngine/WorldCupEngine/ml/epl/`. Baz tunnel now requires an auth token (`BAZ_TUNNEL_TOKEN` — **must still be set in Vercel env**). Root README rewritten to match actual architecture. Prior state, 2026-07-03: built the market-event causal-tagging pipeline — see section below. Also: AFL R17 fully re-priced 2026-07-02, T1–T7 + ML shadow + T9 matrix, writeup at `BettingEngine/outputs/results/r17_afl_pricing_2026.md`. Extensive model-vs-market backtesting this session: real production model (not naive ELO proxy) is at genuine parity with market on handicap accuracy once stale-model rounds are excluded (AFL R14-16: 11-10 closer, essentially tied avg error). The "model undercooks market at extreme ELO gaps" pattern does NOT indicate an exploitable market inefficiency — large-sample ATS backtest on the exact rules+ML-agree pattern went 4-8 (33%) for AFL. Do not bet big rules/ML-vs-market disagreements. NRL same window showed a genuine 60% ATS cover rate (21-14) — worth continued tracking, not yet proven at scale. Running CLV: NRL +4.99% (58 bets), AFL +0.77% (48 bets).)
**Update this section at the end of every session, before writing the handover diary.**

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
