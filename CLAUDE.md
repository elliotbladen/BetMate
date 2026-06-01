# BetMate — Claude Context

---

## HOW TO START A SESSION

1. Read **Current State** below — this tells you what's happening right now
2. Check `handover/sessions/` for the latest diary if you need more detail
3. Do NOT ask "what were you working on?" — the answer is here

---

## CURRENT STATE
**Last updated:** 2026-06-01 (MCP Phase 1: Claude Tool Use loop live)
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

**Pipeline day is now TUESDAY** (shifted 2026-05-11 — historical odds not ready until Tuesday).
All BetMate tasks use full path `C:\Users\ElliotBladen\.local\bin\uv.exe`.

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
- AFL: returns "coming soon" note — no data source yet

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
│       ├── NRL_CLV_running_2026.csv      running total — currently +7.94% (R8–R11)
│       └── AFL_CLV_running_2026.csv      running total — currently +0.72% (R8–R9)
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

### Pending Work
- **Custom domain betmate.au:** DNS resolving ✅, SSL cert provisioning. `www.betmate.au` CNAME still points to wrong site — needs updating in Cloudflare + Vercel domain added
- **EV signals on Vercel:** wire via Cloudflare Tunnel once domain + tunnel ready
- ~~BVI weekly task~~ ✅ All 4 tasks installed — "BetMate NRL BVI" (Mon 08:20) + "BetMate NRL Home Away Value" (Mon 08:30) first run 2026-05-25
- Odds movement alerts: add threshold filter (only alert if change_pct >= 10%)
- **AFL ML model RETRAINED 2026-05-27** on 2022–2023 data (modern-rule era). Key changes: `--min-year 2022` in `game_log.py` (ELO still warms up from 2009; records filtered to 2022+, 2020 excluded); `season_year` added as feature; XGBoost `sample_weight` exponential decay (decay=1.5, newest game weighted 4.5x oldest). Results vs old model: total MAE 24.6 (was 25.2), totals bias -5.8 pts (was -8 pts), totals strike ±10pt edge 61.3%. Next retrain: add 2024 to training window after 2026 season ends.
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
