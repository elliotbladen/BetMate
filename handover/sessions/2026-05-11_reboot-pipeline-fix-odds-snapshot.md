# Session 2026-05-11 — Post-Reboot Pipeline Fix + Odds Snapshot Rebuild

## What happened

System rebooted before the session started. Audited all scheduled tasks and fixed a pile of issues.

---

## Issues found and fixed

### 1. Pipeline day shifted Monday → Tuesday
Historical odds (aussportsbetting) are not available until Tuesday. All pipeline tasks moved 24 hours:

| Task | Was | Now |
|------|-----|-----|
| BetMate NRL Historical Results | Mon 17:00 | Tue 17:00 |
| BetMate NRL Style Stats Scrape | Mon 18:00 | Tue 18:00 |
| BetMate NRL Round Prep | Mon 18:05 | Tue 18:05 |
| BettingEngine NRL Pricing | Mon 19:03 | Tue 19:03 |

### 2. Broken uv paths — 4 BetMate tasks
All four BetMate scraper tasks were using bare `uv` as the Execute path. Task Scheduler can't find it without the full path. They had been silently failing since ~May 4. Fixed to `C:\Users\ElliotBladen\.local\bin\uv.exe`.

Affected tasks: NRL Historical Results, NRL Style Stats Scrape, NRL Round Prep, Daily Odds Snapshot.

**Rule:** Any BetMate Task Scheduler action that calls uv must use the full path. Never bare `uv`.

### 3. Odds snapshot rebuilt — twice daily
The 10-min snapshot task was overkill (burning ~25,920 API calls/month) and missed 5 days of data (May 6–10) because the machine went off. Replaced with a cleaner setup:

- **Removed:** "BetMate Odds Snapshot 10min" and "BetMate Daily Odds Snapshot"
- **Added:** "BetMate Odds Snapshot" — fires at 09:00 and 18:00 daily
- **StartWhenAvailable = true** — if machine was off at scheduled time, task fires on wake
- **`odds_snapshot.py`** — added retry logic: 3 attempts per sport, 5 min between retries, handles transient network failures
- **Purpose of snapshots:** training data collection, not CLV (CLV comes from aussportsbetting xlsx)
- **Install script:** `scripts/install_odds_snapshot_task.ps1` — re-run to reinstall

API budget impact: ~1,440 calls/month vs 25,920 previously.

### 4. R10 results NOT in DB
The `fetch_nrl_results.py` task fired at 09:00 but was killed by the reboot mid-run. R10 results CSV exists at `data/import/r10_results_2026.csv` (8 rows, all correct). Not loaded yet.

**Must load before Tuesday 19:03 pricing.** The Tuesday 09:00 auto-task should handle it, but verify it ran before pricing fires.

### 5. NRL Injuries — R11 scraped OK
Ran successfully at 10:00 today. 107 records. Source is NRL.com casualty ward (unchanged since May 5 fix).

---

## Still outstanding

- **R10 results → DB**: Tuesday 09:00 auto-task should handle it. Verify before 19:03.
- **R11 referees**: Not yet announced. Re-run `prepare_round.py` once they drop (usually Tue/Wed).
- **NRL Emotional Flags task**: Still not installed. Run `scripts/install_nrl_emotional_task.ps1`.
- **AFL build**: Still pending. AFL_PREP.md has the full build order. Start with DB migration.

---

---

## AFL BVI filter — built + fixed this session

### What it does
Checkbox toggle on the AFL odds tab. Badges teams as **▲ Value** or **▼ Fade** based on the AFL Betting Value Index (aussportstipping.com). Badges are **role-aware** — the signal is evaluated against whether the team is the favourite or underdog in the specific game, not just their season-level rank.

### Badge logic (final)
1. Determine fav/dog from average H2H price across all bookmakers
2. For the fav: use `fav_profit` (how profitable backing them as fav has been this season)
3. For the dog: use `und_profit` (how profitable backing them as dog has been this season)
4. Positive role profit → ▲ Value. Negative → ▼ Fade. Zero/no data → no badge.
5. **If both teams compute to the same badge** (both fade or both value) → suppress both. No actionable signal.
6. Badges only show when signals are **opposing** (▲ vs ▼) or **one-sided** (one badge, other null).

**Brisbane (fav, fav_profit=−2.30) vs Geelong (dog, und_profit=−2.00):** both fade → no badges shown ✓

### Bug fixed: scraper was capturing wrong column
Original scraper took the **first numeric value** after each team name. The page structure is:
`TeamName → Fav: → $value → games# → profit% → Und: → $value → All: → $value`
The first non-`$` number encountered was the **game count** (e.g., 28 for Brisbane), not the profit. All scores were game counts — Brisbane was #1 just because they'd played the most games.

Fixed parser specifically looks for `$`-prefixed values under `Fav:` and `Und:` labels, and `%`-suffixed value for the overall ranking score.

### Real BVI rankings (as of 2026-05-11)
| # | Team | Fav $ | Und $ |
|---|------|-------|-------|
| 1 | Fremantle | +2.60 | +8.25 |
| 2 | GWS | −2.13 | +7.43 |
| 3 | Sydney | +4.30 | +0.02 |
| 4 | Brisbane | −2.30 | +6.86 |
| 5 | Hawthorn | +1.66 | +0.05 |
| 6 | Melbourne | −1.70 | +1.40 |
| ... | | | |
| 18 | Essendon | −0.73 | −18.70 |

### Files changed
| File | Change |
|------|--------|
| `lib/scraper/afl_bvi.py` | Fixed column parsing; now captures `fav_profit`, `und_profit` + overall `score` (Profit %) |
| `app/api/afl-bvi/route.ts` | Unchanged — serves whatever JSON the scraper writes |
| `middleware.ts` | `/api/afl-bvi` in PUBLIC_PATHS |
| `app/odds/page.tsx` | `BviEntry` type extended with `fav_profit`/`und_profit`; `OddsBoardCard` now takes `bviHomeEntry`/`bviAwayEntry` (full objects); role-aware badge computation + same-signal suppression |

### Also fixed this session: Line + Totals market layout
Selection column for Line now shows team badge + reference handicap below.
Selection column for Totals now shows team badge + "Over"/"Under" label.
Totals price cells now show per-bookmaker total line stacked above the price (not just the price).

### Not yet done
BVI scraper needs a **weekly Task Scheduler task** — currently manual run only.
Add to Task Scheduler after AFL build is stable.

---

## Next session — start here

1. Confirm Tuesday pipeline ran cleanly (check Task Scheduler history after 19:03)
2. Verify R10 results loaded: `SELECT COUNT(*) FROM results JOIN matches ON ... WHERE round_number=10`
3. Check R11 pricing output: `results/r11_pricing_2026.csv`
4. If referees announced — re-run pricing
5. Install BVI weekly task: add Task Scheduler entry to run `afl_bvi.py` once a week (Monday morning)
6. Start AFL build: open `handover/AFL_PREP.md`, step 1 is DB migration
