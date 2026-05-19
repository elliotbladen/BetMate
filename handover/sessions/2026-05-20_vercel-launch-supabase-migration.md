# Session 2026-05-20 — Vercel Launch + Supabase Migration

## What was done

### Phase 1 — Audit local file reads
Scanned all API routes and lib files for local filesystem reads that would break on Vercel.
Found 8:
- 5 API routes reading JSON files (afl-bvi, afl-home-away-value, odds/fixture, team-news/nrl, team-news/afl)
- `lib/matrixEV.ts` — reads BettingEngine xlsx matrices
- `lib/oddsSnapshotFallback.ts` — reads odds snapshot CSVs (already safe, existsSync guards)
- `app/api/odds/opening/route.ts` — reads odds snapshot CSVs (already safe, async catch guards)

### Phase 2 — Supabase migration
- Created `supabase/migrations/betmate_data_store.sql` — single key/value table with public read RLS
- Created `lib/supabaseServer.ts` — server-side Supabase client + `getDataStore(key)` helper
- Updated all 5 API routes: Supabase-first, local file fallback (local dev unaffected)
- Added `fs.existsSync(ENGINE_OUTPUTS)` early-return guard to `lib/matrixEV.ts`
- Created `lib/scraper/supabase_push.py` — shared push helper using requests (no new deps)
- Updated `afl_bvi.py`, `afl_home_advantage.py`, `nrl_fixture.py` to push to Supabase after local write
- Created `scripts/push_team_news.py` — manual push for team news files
- Created `scripts/seed_supabase.py` — one-time seed, run before Vercel deploy
- Seeded Supabase: all 5 keys pushed successfully (afl_bvi, afl_home_away, nrl_fixture, team_news_nrl, team_news_afl)
- Added `SUPABASE_SERVICE_ROLE_KEY` to `.env.local`

### Phase 3 — GitHub + Vercel deploy
- Updated `.gitignore` — excluded `data/`, `*.xlsx`, `__pycache__/`, `*.pyc`, `dev-server*.log`, `tsconfig.tsbuildinfo`
- Untracked previously committed data files from git
- Committed + pushed to `github.com/elliotbladen/BetMate`
- Deployed to Vercel — first build failed: `lib/referees.ts` used static JSON imports for files now excluded from git
- Fixed `lib/referees.ts` — removed static imports, replaced with empty-map defaults + optional `refMap` param
- Second build succeeded ✅
- **Site live at `bet-mate-ten.vercel.app`**

### Cloudflare Tunnel — started, not complete
- `cloudflared` installed via winget (v2026.5.0) at `C:\Program Files (x86)\cloudflared\cloudflared.exe`
- Logged in to Cloudflare account
- Blocked: no domain added to Cloudflare yet — user waiting on domain

## Known gaps on live site
- **EV signals (arrows) blank** — intentional. BettingEngine matrices are local-only. Fix via Cloudflare Tunnel.
- **Referee badges blank** — `lib/referees.ts` now returns null without data. Needs `/api/referees` route + Supabase key to work on Vercel.

## Pending
- Custom domain → point at Vercel + Cloudflare Tunnel setup
- Wire EV signals via Cloudflare Tunnel (BAZ_TUNNEL_URL → app/api/chat/route.ts)
- Wire refs via API route + Supabase
- nrl_team_news.py auto-scraper (task #1)
- BVI weekly Task Scheduler task (Monday 08:00)
