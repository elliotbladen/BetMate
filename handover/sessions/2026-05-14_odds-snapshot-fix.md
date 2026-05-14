# Session 2026-05-14 — Odds snapshot fix (missing arrows)

## What was done

### Fixed: odds movement arrows disappearing (snapshot script crashing)

**Symptom:** Odds arrows disappeared. Cycle log showed snapshot script failing with exit code 1 at 06:40 and 09:00 on May 14. No entries in snapshot.log for May 14 — crash happened before logging was initialised.

**Root cause:** Two module-level imports crash Python immediately when their packages aren't available:
- `import requests` (line 31 of `odds_snapshot.py`)
- `from zoneinfo import ZoneInfo` → `ZoneInfo("Australia/Sydney")` needs `tzdata` on Windows

The cycle script used `--with requests python script.py` which:
1. Didn't provide `tzdata` at all
2. Was likely failing to inject `requests` in the Task Scheduler context due to `$ErrorActionPreference = "Stop"` treating uv's install stderr messages as fatal errors

**Fix — three changes:**

1. **`lib/scraper/odds_snapshot.py`** — added PEP 723 inline script metadata:
   ```python
   # /// script
   # dependencies = ["requests", "tzdata"]
   # ///
   ```

2. **`lib/scraper/odds_movement_tracker.py`** — same fix (also uses `ZoneInfo`):
   ```python
   # /// script
   # dependencies = ["tzdata"]
   # ///
   ```

3. **`scripts/run_odds_snapshot_cycle.ps1`** — three changes:
   - `$ErrorActionPreference = "Continue"` (was `"Stop"` — uv writes install progress to stderr which PowerShell 5.1 treats as an error)
   - `uv run $snapshotScript` (was `uv run --with requests python $snapshotScript`)
   - `uv run $trackerScript` (was `uv run python $trackerScript`)
   - Running scripts directly (not `python script.py`) causes uv to read the inline PEP 723 metadata

**Verified:** Ran cycle manually at 09:59 — snapshot appended 916 rows for 2026-05-14, tracker detected 13 movements. Cycle log shows `Tracker script finished with exit code 0`.

## State at end of session

- Dev server: running on port 3000
- Odds arrows: restored (13 movements detected for today)
- 18:00 Task Scheduler run: ready, will use fixed scripts
- Both Python scrapers: self-contained via PEP 723 inline deps — no more reliance on `--with` flags

## Pending

- BVI weekly Task Scheduler task: install entry to run `afl_bvi.py` Monday 08:00
- Odds movement alert threshold: only alert if `change_pct >= 10%`
- `public/mockup.html` can be deleted (was just for design review)
- Emotional task install script (`scripts/install_nrl_emotional_task.ps1`) has stale BetMate/ paths
