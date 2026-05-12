# BetMate — Claude Context

---

## HOW TO START A SESSION

1. Read **Current State** below — this tells you what's happening right now
2. Check `handover/sessions/` for the latest diary if you need more detail
3. Do NOT ask "what were you working on?" — the answer is here

---

## CURRENT STATE
**Last updated:** 2026-05-11
**Update this section at the end of every session, before writing the handover diary.**

### App State
- Dev server: `npm run dev` → http://127.0.0.1:3000 (use 127.0.0.1 not localhost on Windows)
- Build: passing ✅
- Theme: dark (RacingZone-inspired, black/white/green) — do not revert
- Working pages: `/odds` (NRL + AFL tabs), `/research`, `/tools`

### Scheduled Tasks (Task Scheduler)
| Task | Schedule | Status |
|------|----------|--------|
| "BetMate Odds Snapshot" | 09:00 + 18:00 daily | ✅ Installed (StartWhenAvailable) |
| "BettingEngine NRL Injuries Fetch" | Tuesday 10:00 | ✅ Running |
| "BetMate NRL Historical Results" | Tuesday 17:00 | ✅ Fixed (was broken — bare `uv`) |
| "BetMate NRL Style Stats Scrape" | Tuesday 18:00 | ✅ Fixed (was broken — bare `uv`) |
| "BetMate NRL Round Prep" | Tuesday 18:05 | ✅ Fixed (was broken — bare `uv`) |
| "BettingEngine NRL Pricing" | Tuesday 19:03 | ✅ Shifted Mon→Tue |
| "BetMate NRL Emotional Flags" | Tuesday 11:00 | ✅ Installed 2026-05-12 |
| "BettingEngine NRL Referees Fetch" | Tuesday 14:00 + 17:00 | ✅ Installed 2026-05-12 |

**Pipeline day is now TUESDAY** (shifted 2026-05-11 — historical odds not ready until Tuesday).
All BetMate tasks that previously used bare `uv` now use full path `C:\Users\ElliotBladen\.local\bin\uv.exe`.

### Scrapers — Output Locations
| Scraper | Output | Consumed by |
|---------|--------|-------------|
| `lib/scraper/odds_snapshot.py` | `data/odds_snapshots/YYYY/YYYY-MM-DD.csv` | UI + study |
| `lib/scraper/odds_movement_tracker.py` | `data/odds_movements/YYYY/YYYY-MM-DD.csv` | UI alerts |
| `lib/scraper/nrl_injuries.py` | `data/nrl/injuries/processed/latest-injuries.json` | BettingEngine T5 |
| `lib/scraper/nrl_emotional.py` | `data/nrl/emotional/processed/latest-emotional.json` | BettingEngine T7 |
| `lib/scraper/afl_bvi.py` | `data/afl/bvi/processed/latest-bvi.json` | `/api/afl-bvi` → odds page BVI filter |

### Injury Scraper — Current Source
Source changed 2026-05-05: NRL.com casualty ward (Fox Sports broke).
URL: `https://www.nrl.com/news/{season}/01/01/nrl-casualty-ward-...`
Last scraped: 2026-05-11 (R11, 107 records)

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
- Scraper: `lib/scraper/afl_bvi.py` — run manually or via Task Scheduler
- **Pending:** weekly Task Scheduler task to auto-refresh BVI data (not yet installed)

### Pending Work
- BVI weekly task: install Task Scheduler entry to run `afl_bvi.py` Monday 08:00
- Emotional task install script (`scripts/install_nrl_emotional_task.ps1`) has stale BetMate/ paths — fix before rerunning (paths updated inline 2026-05-12)
- Odds movement alerts: add threshold filter (only alert if change_pct >= 10%)
- UI: no pending redesign — user reverted RacingZone polish on 2026-05-05, keep current look
- AFL scraper: no equivalent injury scraper yet

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
& C:\Users\ElliotBladen\.local\bin\uv.exe run python lib/scraper/odds_snapshot.py
& C:\Users\ElliotBladen\.local\bin\uv.exe run python lib/scraper/nrl_injuries.py

# uv cache is local to avoid permission issues:
# BetMate\.uv-cache
```

### Key Files
| File | Purpose |
|------|---------|
| `lib/scraper/odds_snapshot.py` | Pulls odds from API, appends to dated CSV |
| `lib/scraper/odds_movement_tracker.py` | Diffs last two snapshots, writes movements CSV |
| `lib/scraper/nrl_injuries.py` | Scrapes NRL.com casualty ward |
| `scripts/run_odds_snapshot_cycle.ps1` | Wrapper: runs snapshot + movement tracker |
| `scripts/install_odds_snapshot_task.ps1` | Installs twice-daily snapshot task (09:00 + 18:00, StartWhenAvailable) |
| `app/api/weather/route.ts` | Weather API proxy (Tomorrow.io) + ping logger |
| `lib/teams.ts` | NRL + AFL team badge colours/abbrs — keys must match Odds API names exactly |
| `lib/venues.ts` | NRL home team → venue coords |
| `lib/aflVenues.ts` | AFL home team → venue coords |
| `data/weather/YYYY/YYYY-MM-DD.csv` | Weather ping log (auto-created) |
| `lib/scraper/afl_bvi.py` | Scrapes AFL BVI from aussportstipping.com — run weekly |
| `app/api/afl-bvi/route.ts` | Serves BVI JSON to the odds page |
| `data/afl/bvi/processed/latest-bvi.json` | BVI data (18 teams, rank + score + tier) |

### Dev Server Issues
If `.next` build cache corrupts (symptom: `Cannot find module './948.js'`):
```powershell
Stop-Process -Name node -Force
Remove-Item -Recurse -Force .next
npm run dev
```
