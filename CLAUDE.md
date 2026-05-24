# BetMate — Claude Context

---

## HOW TO START A SESSION

1. Read **Current State** below — this tells you what's happening right now
2. Check `handover/sessions/` for the latest diary if you need more detail
3. Do NOT ask "what were you working on?" — the answer is here

---

## CURRENT STATE
**Last updated:** 2026-05-22 (end of session)
**Update this section at the end of every session, before writing the handover diary.**

### App State
- Dev server: `npm run dev` → http://127.0.0.1:3000 (use 127.0.0.1 not localhost on Windows)
- Build: passing ✅
- Theme: dark (RacingZone-inspired, black/white/green) — do not revert
- Working pages: `/odds` (NRL + AFL tabs), `/research`, `/tools`

### Scheduled Tasks (Task Scheduler)
| Task | Schedule | Status |
|------|----------|--------|
| "BetMate Odds Snapshot" | 09:00 + 18:00 daily | ✅ Running |
| "BettingEngine NRL Injuries Fetch" | Tuesday 10:00 | ✅ Fixed path (Apps not Apps\BetMate) |
| "BetMate NRL Historical Results" | Tuesday 16:00 | ✅ Fixed — also runs AFL download |
| "BetMate NRL Style Stats Scrape" | Tuesday 16:15 | ✅ Fixed path |
| "BetMate NRL Round Prep" | Tuesday 16:20 | ✅ Fixed path, time 16:20 |
| "BettingEngine NRL Pricing" | Tuesday 16:40 | ✅ FIXED — now uses wrapper scripts/run_nrl_pricing.ps1 with BETMATE_ROOT |
| "BetMate NRL Emotional Flags" | Tuesday 14:00 | ✅ Updated to 14:00; fixed stale BetMate/ path in wrapper |
| "BetMate AFL Emotional Flags" | Tuesday 14:30 | ✅ NEW — scrapers/afl_emotional.py |
| "BetMate AFL BVI" | Monday 08:00 | ✅ Weekly — scrapers/afl_bvi.py → Supabase afl_bvi |
| "BetMate AFL Home Away Value" | Monday 08:10 | ✅ Weekly — scrapers/afl_home_advantage.py → Supabase afl_home_away |
| "BetMate NRL BVI" | Monday 08:20 | ✅ Weekly — scrapers/nrl_bvi.py → Supabase nrl_bvi |
| "BetMate NRL Home Away Value" | Monday 08:30 | ✅ Weekly — scrapers/nrl_home_advantage.py → Supabase nrl_home_away |
| "BettingEngine NRL Referees Fetch" | Wednesday 14:00 | ✅ Moved to Wednesday (refs announced Wed) |
| "BetMate AFL Injuries Fetch" | Tuesday 11:30 | ✅ NEW — scrapers/afl_injuries.py |
| "BetMate NRL Team News" | Tuesday 10:30 | ✅ NEW — scrapers/nrl_team_news.py (auto-generates injuries section; suspensions stay manual) |
| "BetMate AFL Style Stats Scrape" | Tuesday 16:15 | ✅ NEW — scrapers/afl_style_stats.py |
| "BetMate AFL Round Prep" | Tuesday 16:20 | ✅ NEW — scrapers/afl_round_prep.py |

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
**API route:** `app/api/weather/route.ts` — server-side 1-hour cache (`revalidate = 3600`)
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

### Team News System — BUILT 2026-05-18
- `data/nrl/team-news/latest.json` — NRL R12 fresh news (Rabbitohs, Wests Tigers, Manly)
- `data/afl/team-news/latest.json` — AFL R11 fresh news (Richmond, West Coast, Gold Coast)
- `app/api/team-news/nrl/route.ts` + `app/api/team-news/afl/route.ts` — API routes (public)
- UI: DetailDrawer Team News tab shows real data; chip shows Alert/Monitor status
- **Update weekly:** manually edit JSON files after weekend games (Monday for NRL, Wednesday after AFL tribunal)
- **Future automation:** `scrapers/nrl_team_news.py` — auto-generate injuries section from `latest-injuries.json`; suspensions stay manual

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

### Cloudflare Tunnel — IN PROGRESS
- `cloudflared` installed at `C:\Program Files (x86)\cloudflared\cloudflared.exe` ✅
- Logged in to Cloudflare account ✅
- **Blocked:** no domain added to Cloudflare yet — waiting on domain
- **Next steps when domain ready:**
  1. Add domain to Cloudflare, update nameservers at registrar
  2. `cloudflared tunnel create betmate-baz`
  3. Configure tunnel → localhost:8765
  4. Add `BAZ_TUNNEL_URL` to Vercel env vars
  5. Update `app/api/chat/route.ts` to use tunnel URL on Vercel
  6. Point custom domain at Vercel

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
& ".\.venv\Scripts\python.exe" scripts\prepare_afl_round.py --season 2026 --round 11
& ".\.venv\Scripts\python.exe" scripts\_export_afl_prices.py
```

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
- AFL totals model has same known bias as NRL — rules consistently 10–30pts above market

### Pending Work
- **Custom domain betmate.au:** DNS resolving ✅, SSL cert provisioning. `www.betmate.au` CNAME still points to wrong site — needs updating in Cloudflare + Vercel domain added
- **EV signals on Vercel:** wire via Cloudflare Tunnel once domain + tunnel ready
- ~~BVI weekly task~~ ✅ All 4 tasks installed — "BetMate NRL BVI" (Mon 08:20) + "BetMate NRL Home Away Value" (Mon 08:30) first run 2026-05-25
- Odds movement alerts: add threshold filter (only alert if change_pct >= 10%)
- **AFL totals model:** Both AFL and NRL show model consistently pricing totals 5–10pts+ above market. Needs T1 expected-points review.
- **Refs on Vercel:** wire `lib/referees.ts` to an API route + Supabase key so ref badges show on live site
- **T9 Matrix tier:** end-of-2026 review. Weighted by sample size (N<10=0.3, N10-25=0.6, N25+=1.0). Triple confluence cap 10%. See memory file.
- **Supabase UNIQUE constraint:** Add UNIQUE constraint on `key` column in `betmate_data_store` so `resolution=merge-duplicates` actually merges instead of inserting duplicates. Currently `getDataStore` works around this with `.limit(1)` but the root cause should be fixed in Supabase SQL editor: `ALTER TABLE betmate_data_store ADD CONSTRAINT betmate_data_store_key_unique UNIQUE (key);`

### Baz Agent — BUILT 2026-05-15
- `BettingEngine/baz_server.py` — FastAPI local context server, localhost:8765. Endpoints: `/health`, `/context/round`, `/context/game`, `/signals`, `/clv`, `/context/team`
- `app/api/chat/route.ts` — updated to fetch from `BAZ_LOCAL_API` before calling Claude. 1.5s timeout, graceful fallback.
- `.env.local` — `BAZ_LOCAL_API=http://127.0.0.1:8765` added
- `components/chat/ChatPanel.tsx` — parses brain status token from stream, shows "Brain offline" amber banner when BettingEngine is down
- FastAPI + uvicorn installed into `.venv` (bootstrapped pip first — bare venv had no pip)
- ChatPanel.tsx has a double-encoding issue with box-drawing chars (pre-existing, not introduced here). Future edits to this file: use PowerShell file manipulation, NOT the Edit tool — it inserts curly quotes.

**To start Baz's brain:**
```powershell
cd C:\Users\ElliotBladen\Apps\BettingEngine
& .\.venv\Scripts\python.exe baz_server.py
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
