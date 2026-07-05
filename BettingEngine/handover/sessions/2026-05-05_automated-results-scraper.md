# Session: Automated NRL Results Scraper
**Date:** 2026-05-05
**Goal:** Build a Monday 9AM automated scraper to fetch NRL results so the DB is populated before the Monday 7PM pricing run, removing the need to fill CSV scores manually.

---

## What Was Built

### 1. `scripts/fetch_nrl_results.py` (new)
Automated results scraper. Hits the NRL.com draw API for rounds missing results in the DB.

Key behaviour:
- Auto-detects which DB rounds have NULL results (`rounds_missing_results()`)
- Applies `NRL_API_ROUND_OFFSET = -1` to convert DB round → NRL API round
  - The DB has a pre-season R1 (Feb 28 World Club Challenge games) that the NRL API doesn't count
  - DB R10 = NRL API R9, etc.
- Tries primary offset then ±1 as fallback (robust to future drift)
- Parses scores from `fixture.homeTeam.score` / `fixture.awayTeam.score`
  - Falls back to `.points`, `.totalScore`, top-level `homeScore`/`awayScore`
- Matches to DB `match_id` via team name join (`teams` table)
- Writes `data/import/rN_results_YYYY.csv`
- Calls `load_results.py` automatically
- Saves raw API response to `data/nrl/results/raw/YYYY/api-round-N.json`

Usage:
```
python scripts/fetch_nrl_results.py                    # auto-detect
python scripts/fetch_nrl_results.py --round 10         # specific round
python scripts/fetch_nrl_results.py --round 10 --dry-run
```

### 2. `scripts/load_results.py` (fixed)
Was broken — multiple schema mismatches:
- Had `source` column in INSERT (column doesn't exist in DB)
- Missing required NOT NULL columns `total_score` and `margin`
- Had `─` unicode chars in print statements (crashes on Windows cp1252 console)
- Used deprecated `datetime.utcnow()`

All fixed. Now correctly inserts `total_score = home + away`, `margin = home - away`.

### 3. `scripts/install_nrl_results_task.ps1` (new)
Windows Task Scheduler installer. Installs:
- Task name: "BettingEngine NRL Results Fetch"
- Schedule: every Monday at 09:00
- Command: `python scripts/fetch_nrl_results.py --season 2026 --round 0`
- Flags: StartWhenAvailable, WakeToRun

---

## R10 Results — LOADED
All 8 R10 results are now in the DB (was NULL before this session):

| Match | Home | Away | Score |
|-------|------|------|-------|
| 278 | Canterbury-Bankstown Bulldogs | North Queensland Cowboys | 12-28 |
| 279 | Dolphins | Melbourne Storm | 28-10 |
| 280 | Gold Coast Titans | Canberra Raiders | 12-28 |
| 281 | Parramatta Eels | New Zealand Warriors | 14-36 |
| 282 | Sydney Roosters | Brisbane Broncos | 38-24 |
| 283 | Newcastle Knights | South Sydney Rabbitohs | 42-38 |
| 284 | Cronulla-Sutherland Sharks | Wests Tigers | 52-10 |
| 285 | Penrith Panthers | Manly-Warringah Sea Eagles | 18-16 |

---

## Monday Pipeline (updated)

| Time | Task |
|------|------|
| 09:00 | **NEW** fetch_nrl_results.py — scrapes last round scores, loads into DB |
| 17:00 | nrl_historical_results.py — downloads aussportsbetting xlsx |
| 18:00 | style stats scraper |
| 19:03 | prepare_round.py — prices upcoming round |

---

## Pending

- **R11 (Magic Round, May 15-17)**: scraper will auto-run May 18 Monday and pick up R11 results
- **Round offset**: if NRL adds a mid-season bye or other special round, the offset may drift. The scraper tries ±1 as fallback, but worth monitoring each week
- **AFL results**: no equivalent scraper yet — AFL still priced manually
- **BetMate UI**: user said "still need to work on it" — no specific requests this session
