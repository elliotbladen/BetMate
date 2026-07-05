# AFL Build Preparation
**Written:** 2026-05-06
**Updated:** 2026-05-11
**Status:** Architecture only — do not build until NRL pipeline is running smoothly on Tuesday cadence.
NRL R11 (Magic Round, May 15–17) is the current focus. Start AFL build the week after if Tuesday pipeline runs cleanly.

This document exists so we walk into the AFL build session already knowing the landmines,
the data sources, and the decisions. Do not repeat the NRL discovery process.

---

## Operational Lessons — Learned in NRL Season 2026 (added 2026-05-11)

These are not architectural gotchas — they are automation/ops lessons that cost real data loss
or debugging time during the NRL season. Apply all of these on day 1 for AFL.

### Task Scheduler

| Lesson | What happened | AFL rule |
|---|---|---|
| Full uv path — every single time | 4 BetMate tasks used bare `uv`. Task Scheduler can't find it. Silently failed for ~7 days before anyone noticed. | Every task that calls uv must use `C:\Users\ElliotBladen\.local\bin\uv.exe`. No exceptions. Check with `Get-ScheduledTask \| Select Actions` after install. |
| StartWhenAvailable on every task | Machine went to sleep. Odds snapshot task missed 5 days of data (May 6–10). No error, no alert — just a silent gap. | Set `-StartWhenAvailable` on the `ScheduledTaskSettingsSet` for every AFL task. Costs nothing, prevents silent gaps. |
| Never trust LastRunTime alone | Task Scheduler showed a task as "last run 09:00" with a clean timestamp but it had been killed mid-run by a reboot (exit code 3221225786). DB had zero rows. | After every new task's first run: check the actual output (DB row count, file contents, log file). Don't rely on the Task Scheduler success code. |
| Exit code 3221225786 = killed by reboot | Not a script error — means the process was running when Windows shut down. | If you see this code, the script didn't fail — it was interrupted. Re-run manually and investigate the output, not the script. |

### Pipeline design

| Lesson | What happened | AFL rule |
|---|---|---|
| Verify data availability before setting schedule times | NRL pipeline was set to Monday. Discovered in May that aussportsbetting historical xlsx isn't ready until Tuesday. Lost several weeks of bad timing before fixing. | Before installing the AFL Tuesday pipeline, manually download the AFL xlsx on a Tuesday and confirm it has the latest completed round. Only then lock in 17:00 Tue as the trigger. |
| Results fetch is a single point of failure | `fetch_nrl_results.py` ran at 09:00, got killed by a reboot, left R10 results at zero in the DB. Pricing would have run at 19:03 with stale ELO. | Add a pre-pricing check in `prepare_round.py` (or a standalone script) that asserts results exist for the previous round before proceeding. Warn loudly — don't silently price on stale data. |
| Manual CSV fallback for results | The auto-scraper failing doesn't mean the data is unavailable — scores are public. | Keep `data/import/rN_results_2026.csv` template ready. If auto-scraper fails, fill it manually and run `load_results.py`. Do this before 19:30 pricing fires. |

### Odds snapshot

| Lesson | What happened | AFL rule |
|---|---|---|
| 10-min snapshots are wasteful | ~25,920 API calls/month just for snapshots. Machine going off wasted all of it — 5-day gap anyway. | Twice daily (09:00 + 18:00) is enough for training data. Morning open + pre-game read covers what matters. |
| Snapshots ≠ CLV source | Snapshots are training data. CLV comes from the aussportsbetting historical xlsx. Don't confuse the two — they serve completely different purposes. | Same rule applies for AFL. Don't build CLV off snapshot CSVs. |

---

## NRL Pain Points → AFL Implications

Every item here burned at least one session on NRL. Do not repeat.

| NRL Pain Point | What Happened | AFL Rule |
|---|---|---|
| Pre-season round offset | Feb 28 games stored as R1, pushed every round +1 vs API. Took a full session to fix with a cascade migration. | Decide pre-season policy on day 1: pre-season games (AAMI Community Series) go in as R0 or are excluded entirely. Do NOT let them inflate round numbers. |
| `load_results.py` schema mismatch | Script had `source` column (doesn't exist), missing `total_score` + `margin` NOT NULL columns. Broke silently until run. | Write AFL results loader against the actual DB schema before first use. Run `--dry-run` against a real DB before ever using it live. |
| Injury scraper source broke | Fox Sports URL redirected to motorsport. Scraper returned 0 records silently. | Use AFL.com.au as primary (first-party, stable). Footywire as fallback. Add a record-count assertion — if scrape returns 0, fail loudly. |
| Team name mismatches everywhere | "Canterbury Bulldogs" vs "Canterbury-Bankstown Bulldogs" caused silent join failures throughout. | Build the full AFL canonical TEAM_MAP before writing any scraper. Every scraper must go through the map. See team list below. |
| Style stats stale in DB | Stats were 6 weeks old when pricing ran. `step0b` was bolted on as a fix mid-season. | Wire AFL style stats import into `prepare_round.py` as `step0b` from day 1. Do not add it retroactively. |
| `step6_validate` was fatal | Missing referee = pricing run dies completely. Blocked a time-sensitive run. | All validation steps for new sports default to warning-only until the pipeline has run at least 3 rounds cleanly. |
| Task Scheduler full path required | Plain `uv` not found by Task Scheduler. Took a session to diagnose. | Copy NRL install scripts exactly. Use `C:\Users\ElliotBladen\.local\bin\uv.exe` and repo-local `.uv-cache`. |
| API round vs DB round | NRL API round ≠ DB round until fixed. Caused wrong results to be scraped. | On day 1, print both the DB round number and the API round number side-by-side and confirm they match before writing any automation. |

---

## Data Sources (confirmed)

### Injuries
- **Primary:** `https://www.afl.com.au/matches/injury-list`
- Server-rendered HTML, no JS required
- All 18 clubs in one page, 3-column table: Player / Injury / Expected Return
- Updates: **Tuesday** consistently (confirmed across R7, R8, R9 2026)
- Has "In the Mix" narrative per club — useful additional context
- Fallback: `https://www.footywire.com/afl/footy/injury_list` (no timestamp, use as cross-check only)

### Results
- **Automation:** AFL.com.au draw API (same pattern as NRL scraper)
  - Round data: `https://www.afl.com.au/api/cfs/afl/matchItems/round?...`
  - Scores available Sunday night after round ends
- **Historical (for ELO seeding):** aussportsbetting.com.au — has AFL xlsx going back years, same site used for NRL historical results

### Fixtures
- AFL.com.au API (same source as results — fixtures and results come from same endpoint)
- BetMate already has AFL fixture data (AFL tab working in UI)

### Style Stats / Team Stats
- AFL.com.au stats pages
- Footywire stats (used by fitzRoy R package — reliable)
- BetMate style stats scraper will need an AFL equivalent built

### Umpires
- **SKIP for V1.** Three umpires per game dilutes individual signal. Revisit after one full season if systematic mispricing is observed.

---

## AFL Team Canonical Names + Slugs

Build this TEAM_MAP before writing any scraper. Every name variant must map to the canonical.

| Canonical DB Name | Common Short Names | API/URL Slug |
|---|---|---|
| Adelaide Crows | Adelaide, Crows | crows |
| Brisbane Lions | Brisbane, Lions | lions |
| Carlton Blues | Carlton, Blues | blues |
| Collingwood Magpies | Collingwood, Pies, Magpies | magpies |
| Essendon Bombers | Essendon, Bombers, Dons | bombers |
| Fremantle Dockers | Fremantle, Dockers, Freo | dockers |
| Geelong Cats | Geelong, Cats | cats |
| Gold Coast Suns | Gold Coast, Suns | suns |
| Greater Western Sydney Giants | GWS, GWS Giants, Giants | giants |
| Hawthorn Hawks | Hawthorn, Hawks | hawks |
| Melbourne Demons | Melbourne, Demons, Dees | demons |
| North Melbourne Kangaroos | North Melbourne, North, Kangaroos, Roos | kangaroos |
| Port Adelaide Power | Port Adelaide, Port, Power | power |
| Richmond Tigers | Richmond, Tigers | tigers |
| St Kilda Saints | St Kilda, Saints | saints |
| Sydney Swans | Sydney, Swans | swans |
| West Coast Eagles | West Coast, Eagles | eagles |
| Western Bulldogs | Western Bulldogs, Bulldogs, Doggies | bulldogs |

---

## Scoring System

AFL uses goals + behinds. The DB must store both.

```
score = (goals × 6) + behinds
```

| Parameter | AFL Value | NRL Value |
|---|---|---|
| Average game total | ~160–200 pts | ~47 pts |
| Average margin | ~35–45 pts | ~12 pts |
| Home advantage (pts) | ~6–8 pts | ~3–4 pts |
| Teams | 18 | 17 (NRL) |
| Pythagorean exponent | Needs calibration | Calibrated |

Tier 1 constants all need AFL-specific calibration. Do not copy NRL values.

---

## Tuesday Pipeline (AFL)

AFL rounds run Thursday–Sunday. Results available Sunday night. Injury list updates Tuesday.

| Time | Script | Notes |
|------|--------|-------|
| 09:00 Tue | `scripts/fetch_afl_results.py` | Scrapes Sunday's results, loads to DB |
| 10:00 Tue | BetMate `lib/scraper/afl_injuries.py` | Scrapes AFL.com.au Medical Room |
| 17:00 Tue | `scripts/afl_historical_results.py` | Downloads aussportsbetting AFL xlsx |
| 19:30 Tue | `prepare_round.py --sport AFL --season 2026` | Prices next AFL round (offset 30 min from NRL run) |

**Wednesday:** Re-scrape injuries after final Medical Room update, re-run prepare_round.

---

## Build Order (when ready)

Do not skip steps or reorder. Each depends on the previous.

1. **DB migration** — AFL teams + venues schema. 18 teams seeded with canonical names.
2. **AFL historical results loader** — aussportsbetting AFL xlsx → DB (seeds ELO)
3. **AFL ELO calibration** — run against historical results, verify sensible ratings
4. **AFL Tier 1** — scoring model with AFL constants (goals/behinds system, correct avg total/margin)
5. **`prepare_round.py --sport AFL`** — extend main pricing script to accept sport flag
6. **AFL fixture scraper** — inserts upcoming round matches from AFL.com.au API
7. **AFL style stats ingestion** — `step0b` equivalent for AFL team stats
8. **`fetch_afl_results.py`** — automated Monday results scraper
9. **BetMate `afl_injuries.py`** — Tuesday injury scraper targeting AFL.com.au
10. **Task Scheduler installers** — AFL Tuesday pipeline automation
11. **AFL Tier 2** — matchup families (clearances, inside 50s, contested possessions, marks, rebound 50s, scoring shots, tackles, disposals)
12. **Validation pass** — 3 rounds of pricing, check warnings, calibrate

---

## Key Architectural Decisions (already made)

| Decision | Choice | Reason |
|---|---|---|
| Umpires (T6) | Skip V1 | 3 umpires dilutes signal; data availability lower than NRL |
| Pre-season games | R0 | Same as NRL — keeps round numbers aligned with API |
| Pipeline day | Tuesday | Injury list updates Tuesday; one day later than NRL Monday pipeline |
| Results source | AFL.com.au API | Same pattern as NRL — proven approach |
| Injury source | AFL.com.au `/matches/injury-list` | Server HTML, Tuesday update, all clubs, structured |
| Style stats | Footywire + AFL.com.au | Footywire is reliable (used by fitzRoy); AFL.com.au as primary |

---

## MCP Note

When building the MCP server (after AFL automation is complete), design all tool signatures
with a `sport` parameter from day 1. Do NOT build NRL-only then bolt on AFL.

```python
get_current_round(sport="NRL")   # → {round: 10, dates: "May 7-11", results: "pending"}
get_current_round(sport="AFL")   # → {round: 9, dates: "May 9-11", results: "pending"}
get_pipeline_status(sport="NRL") # → {last_run: "Mon 09:00", status: "ok"}
get_pipeline_status(sport="AFL") # → {last_run: "Tue 09:00", status: "ok"}
get_pending_tasks()              # → cross-sport list
```

---

## What NOT to Carry Over from NRL

- NRL-specific Tier 2 features (run metres, completion rate, ruck speed, kick metres, missed tackles, errors, penalties, FDO, KRM) — AFL needs completely different features
- NRL avg total / margin / home advantage constants — AFL values are ~4× larger
- NRL Tier 6 referee logic — skip entirely for AFL V1
- Any hardcoded "17 teams" references — AFL has 18
