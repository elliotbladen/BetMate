# Session: Weekend Injury Diff + Auto Team News
**Date:** 2026-06-01

## What was built

New script: `scrapers/weekend_injury_diff.py`

Runs Monday morning and surfaces **only** the injuries that are new since the last scrape — i.e., players not previously in `latest-injuries.json`. Eliminates noise from injuries we already priced in.

### How it works

1. Loads existing `data/{sport}/injuries/processed/latest-injuries.json` as the "known" baseline
2. Scrapes fresh (NRL: NRL.com casualty ward via `nrl_injuries.py`; AFL: footywire.com via `afl_injuries.py`)
3. Diffs on `(team, player)` key:
   - **NEW** — player absent from known list
   - **WORSE** — was `doubtful`, now `out`
   - **BACK** — was in known list, no longer appears (recovered/returned)
4. Writes `data/{sport}/injuries/processed/new-this-week.json` with structured diff
5. Updates `latest-injuries.json` with the full fresh list (so next Monday diffs correctly)
6. Prints formatted console summary

### Imports

The script imports `nrl_injuries` and `afl_injuries` directly (via `sys.path.insert`) and reuses their parse/fetch/write_outputs functions — no code duplication.

### Files created

| File | Purpose |
|------|---------|
| `scrapers/weekend_injury_diff.py` | Main diff script |
| `scripts/run_weekend_injuries.ps1` | PS1 wrapper (sets BETMATE_ROOT, PYTHONUTF8) |
| `scripts/install_weekend_injuries_task.ps1` | Task Scheduler installer |

### Task Scheduler

Task: **"BetMate Weekend Injuries"**
- Schedule: Monday 07:30 (StartWhenAvailable)
- Runs BEFORE BVI tasks (08:00+)
- Log: `data/injuries/logs/task_output.log`

### To install the task

```powershell
& C:\Users\ElliotBladen\Apps\scripts\install_weekend_injuries_task.ps1
```

### To test immediately

```powershell
& C:\Users\ElliotBladen\.local\bin\uv.exe run --with requests --with beautifulsoup4 python scrapers\weekend_injury_diff.py
```

First run will flag ALL current injuries as new (no prior baseline). After that, only genuine new weekend injuries appear.

## Verified live — 2026-06-01 14:05 (final correct push)

**Bug fixed mid-session:** "rested" players were appearing in team news as injuries. Added `is_resting()` filter in `compute_diff()` inside `weekend_injury_diff.py`. Keywords: `rested`, `rest`, `managed`, `load management` — these are stripped from `fresh` before any diff computation so they never reach `new-this-week.json`.

**Gotcha:** first run had already absorbed real injuries into the baseline before filter was added, so the second diff showed 0 new. Reconstructed correct diff from round-13 vs round-14 files manually and pushed.

## Verified live — 2026-06-01 13:46 (initial — had rested players, replaced)

First run output:
- NRL R14: 17 new injuries, 4 worsened, 25 cleared — `team_news_nrl` pushed to Supabase ✅
- AFL R13: 0 new injuries, 14 cleared — `team_news_afl` pushed to Supabase ✅
- NRL alert teams: Canterbury Bulldogs, Cronulla, Manly, Cowboys, Panthers, Rabbitohs, Wests Tigers

**Critical name normalisation confirmed working** — all 4 hyphenated NRL names correctly mapped to Odds API names before writing JSON keys.

## Also built: scripts/update_team_news_injuries.py

Rebuilds the injury section of team news from the full fresh `latest-injuries.json`.

### Why full rebuild, not just the diff?
Applying only the diff incrementally would miss return-date updates (player was already known but their TBC became Round 16). Full rebuild is cleaner and idempotent.

### Key rules
- Replaces ALL `type: "injury"` items per team with fresh data
- Preserves ALL `type: "suspension"` items unchanged (manual-only)
- Drops teams that have zero injuries AND zero suspensions
- Adds teams not previously in team news if they now have injuries
- Recomputes `status: "alert" | "monitor"` based on severity of all items
- Severity: NRL uses `importance_tier` from scraper (elite→high, key→medium, rotation→low); AFL defaults to low
- Pushes `team_news_nrl` and `team_news_afl` keys to Supabase

### To manually push a suspension change
1. Edit `data/{sport}/team-news/latest.json` — add/remove the suspension item
2. Run: `uv run --with requests python scripts/update_team_news_injuries.py --sport NRL`
   (This will also rebuild injuries from the current `latest-injuries.json` — that's correct behaviour)

## Notes

- `latest-injuries.json` is the diff baseline — don't delete it between rounds
- The Tuesday injury fetch (existing "BetMate AFL Injuries Fetch" / nrl_injuries.py tasks) still runs as before and updates `latest-injuries.json` mid-week. This means Monday's diff is comparing against the PREVIOUS TUESDAY's state, which is exactly right: it catches anything that happened in the games and wasn't in last week's casualty ward.
- `new-this-week.json` is for human review only (console summary) — team news is populated from the full `latest-injuries.json`
- AFL severity is all `low` for now — no `importance_tier` in `afl_injuries.py`. Future improvement: add AFL elite players set.
