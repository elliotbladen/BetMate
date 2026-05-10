# Session 2026-05-08 — AFL Badges, Weather Logging, Automation Audit

## What was done

### 1. AFL team colour badges
- Added `AFL_TEAMS` map to `lib/teams.ts` with all 18 clubs
- Updated `getTeamMeta()` to check NRL first then AFL — nothing else needed changing
- **Critical gotcha fixed mid-session:** The Odds API sends full mascot names, not short names.
  Keys must be `"Fremantle Dockers"`, `"Carlton Blues"`, `"Collingwood Magpies"` etc.
  Half the badges were missing until this was corrected.
- Note: `lib/aflTeams.ts` also exists with a separate `getAFLTeamMeta()` — this is a near-duplicate.
  `lib/teams.ts` is what the odds board uses. Don't confuse them.

### 2. Odds board — 10 bookmakers
- Grid changed from 5 → 10 columns (`repeat(10, minmax(72px,1fr))`)
- Scroll container widened from `min-w-[760px]` → `min-w-[1100px]`
- All three `slice(0, 5)` calls changed to `slice(0, 10)`

### 3. Team nickname in grid rows
- Added optional `label` prop to `TeamBadge` component
- Grid rows now pass `game.homeTeam.split(' ').pop()` as label → shows "Broncos", "Suns" etc.
- Card header still shows full team name — label prop only used in the bookmaker grid rows

### 4. AFL weather plumbing
- Imported `getAFLVenue` from `lib/aflVenues.ts`
- `OddsBoardCard` now uses: `game.sport === 'AFL' ? getAFLVenue(...) : getVenue(...)`
- All 18 AFL venues already existed in `lib/aflVenues.ts` — just wasn't wired

### 5. Weather ping schedule
Three fetches per game card (client-side `setTimeout`):
1. On mount (immediate)
2. 1 hour before kickoff
3. Halftime — NRL: kickoff + 45 min, AFL: kickoff + 65 min

If the tab isn't open at those times, the fetch doesn't happen — that's fine.

### 6. Weather logging
Every weather API response is appended to `data/weather/YYYY/YYYY-MM-DD.csv`.
- Implemented in `app/api/weather/route.ts` — fire-and-forget, never blocks response
- Header written on first ping of the day, rows appended after
- Columns: `timestamp, lat, lon, commence_time, temperature, wind_speed, wind_gust, precip_prob, precip_intensity, dew_point, humidity, condition, flags`
- Directory auto-created via `mkdir({ recursive: true })`

### 7. CLAUDE.md updated
- Last updated date → 2026-05-08
- Added Weather System section (schedule, logging, venue lookup)
- Added Odds Board UI State section (10 bookmakers, nickname rows, badge gotcha)
- Added `lib/teams.ts` and weather files to Key Files table

---

## Automation pipeline audit

### NRL — is it actually automated?
Checked Task Scheduler. Key finding: **Results Fetch and Injuries Fetch have never run** (Last: 1999). 
They were installed recently and will fire for the first time **Monday May 11**.

| Task | Last run | Next run |
|------|----------|----------|
| NRL Results Fetch | Never | Mon 11 May 09:00 |
| NRL Injuries Fetch (runs BetMate scraper) | Never | Mon 11 May 10:00 |
| NRL Referees Fetch | 07 May | Wed 13 May 12:00 |
| NRL Pricing | 05 May | Mon 11 May 19:03 |
| NRL Thursday Pricing | 08 May (today) | Thu 14 May 18:00 |

Monday May 11 will be the first fully hands-off NRL run.

**Still missing:** "BetMate NRL Emotional Flags" task has NOT been installed.
Run: `powershell -ExecutionPolicy Bypass -File scripts\install_nrl_emotional_task.ps1`

### AFL — automation status
Nothing automated yet. Umpires script exists (`afl_umpires.py`) but we're skipping umpires for V1 per AFL_PREP.md.

---

## AFL pricing — what BetMate still needs to build

5 scripts needed before BettingEngine can price AFL games:

| Priority | Script | Output | Notes |
|----------|--------|--------|-------|
| 1 — Critical | `afl_injuries.py` | `data/afl/injuries/processed/latest-injuries.json` | AFL.com.au `/matches/injury-list`, Tuesday 10:00. Server HTML, all 18 clubs, updates Tuesday. |
| 2 — Critical | `afl_style_stats.py` | `data/afl/style-stats/processed/latest-style-stats.csv` | T2 matchup tier. Source: Footywire or AFL.com.au stats |
| 3 | `afl_news_flags.py` | `data/afl/news_flags/processed/latest.json` | Feeds emotional tier. Same pattern as `nrl_news_flags.py` |
| 4 | `afl_emotional.py` | `data/afl/emotional/processed/latest-emotional.json` | Claude API, same pattern as `nrl_emotional.py` |
| 5 | `afl_round_prep.py` | `data/afl/fixture/processed/latest.json` | Fixture for upcoming round |

Weather is already handled by the existing weather API — no AFL-specific scraper needed.
Umpires: skip for V1 (AFL_PREP.md decision).

**Tuesday night AFL pricing is achievable** — AFL injury list updates Tuesday, not Wednesday.
Pipeline: Tue 10:00 injuries → Tue 19:30 `prepare_round.py --sport AFL`

Once BetMate scripts are built, BettingEngine just needs path resolvers in `prepare_round.py`
pointing at the new AFL data files — same pattern as NRL injuries/referees/emotional.

---

## Next session — start here

1. Install NRL Emotional Flags task (5 min): `scripts\install_nrl_emotional_task.ps1`
2. Build `afl_injuries.py` (AFL.com.au `/matches/injury-list`)
3. Build `afl_style_stats.py`
4. Then BettingEngine: DB migration + AFL Tier 1 + `prepare_round.py --sport AFL`
