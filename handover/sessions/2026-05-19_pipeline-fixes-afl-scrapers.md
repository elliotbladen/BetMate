# Session 2026-05-19 — Pipeline Fixes, AFL Scrapers, NRL Pricing Fixed

## What happened

Tuesday pipeline day. Everything was broken. Diagnosed and fixed every failing task.

---

## Root Causes Fixed

### 1. Stale paths from monorepo split
After the BetMate/BettingEngine split, several Task Scheduler tasks still had `Apps\BetMate\` in their WorkingDirectory or script paths. Fixed by updating each action to use `Apps\` directly.

**Tasks with path fix:**
- "BettingEngine NRL Injuries Fetch" — WorkingDirectory `Apps\BetMate` → `Apps`
- "BetMate NRL Style Stats Scrape" — script path fixed
- "BetMate NRL Round Prep" — script path fixed

### 2. BettingEngine NRL Pricing — BETMATE_ROOT resolution bug (CRITICAL)
`_find_betmate_root()` in `prepare_round.py` searches for a sibling `BetMate` directory.
After the monorepo split, `C:\Users\ElliotBladen\Apps\BetMate` still exists (old repo, no data).
BettingEngine found this and tried to load fixture/injuries from `Apps\BetMate\data\...` → FATAL.
Actual data lives at `Apps\data\...`.

**Fix:** Created wrapper `BettingEngine/scripts/run_nrl_pricing.ps1` that:
1. Sets `$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"`
2. Sets `$env:PYTHONUTF8 = "1"` (fixes UnicodeEncodeError on box-drawing chars in non-UTF console)
3. Runs `prepare_round.py --season 2026 --round 0`
4. If exit 0, auto-detects round from fixture JSON and runs `export_round_csv.py`

Updated Task Scheduler task to call `powershell.exe -File run_nrl_pricing.ps1`.

### 3. NRL Historical Results — wrong script name + playwright not installed
Script was called `nrl_historical.py`, actual file is `nrl_historical_results.py`. Fixed.
Also ran `uv run --with playwright python -m playwright install chromium` (was missing on this setup).

### 4. ephem module missing
Step 8 (matrix regeneration) crashed with `ModuleNotFoundError: No module named 'ephem'`.
Fix: `& .venv\Scripts\python.exe -m pip install ephem`
All 3 matrices now run clean.

### 5. NRL Referees task — moved to Wednesday
Refs aren't announced until Wednesday. Moving Tuesday 2 PM + 5 PM → Wednesday 2 PM only.
R12 pricing ran with T6=0.0 (no refs yet) — expected. Will reprice Wednesday after refs come in.

---

## New AFL Scrapers Built

### `lib/scraper/afl_injuries.py`
Source: footywire.com/afl/footy/injury_list
Tables come in pairs: (team header, player data). Parses Player/Injury/Returning columns.
parse_return_status(): "Test"/"Concussion" → doubtful; int ≤1 week → doubtful; else → out
Output: `data/afl/injuries/processed/latest-injuries.json`
Run: `uv run --with requests --with beautifulsoup4 python lib/scraper/afl_injuries.py --season 2026`
Tested: 124 records, 18 teams ✅

### `lib/scraper/afl_style_stats.py`
Source: afltables.com/afl/stats/{season}t.html
Stats in "for-against" format (e.g. "139-115") — takes first number as team stat.
Columns: FF, FA, CP, UP, CM, MI, 1%, GA → per-game averages
Skips W-D-L summary rows, uses seen_teams set to avoid duplicates.
Output: `data/afl/style-stats/processed/latest-style-stats.csv`
Tested: 18 teams, round 11 ✅

### `lib/scraper/afl_round_prep.py`
Orchestrates AFL round prep: runs afl_injuries.py only (no umpires).
Output: logs to `data/afl/logs/round_prep.log`
Tested: exit 0 ✅

---

## Task Scheduler — New Tasks
| Task | Schedule | Script |
|------|----------|--------|
| BetMate AFL Injuries Fetch | Tuesday 11:30 | lib/scraper/afl_injuries.py |
| BetMate AFL Style Stats Scrape | Tuesday 16:15 | lib/scraper/afl_style_stats.py |
| BetMate AFL Round Prep | Tuesday 16:20 | lib/scraper/afl_round_prep.py |

---

## NRL R12 Pricing — Done

Auto-detected round 12 (5 games: Thu May 21 – Sun May 24).
All tiers fired except T6 (referees not yet announced — T6=0.0 is expected).
Results: `BettingEngine/results/r12_pricing_2026.csv` ✅

T2 fired for NQ Cowboys vs Rabbitohs (family C, +2.0pt hcap / -1.5pt totals).
T5 fired for all 5 games with real injury data.
T7 all clear weather.

---

## What to do next Tuesday

Full pipeline will auto-fire. Should get:
- 10:00 NRL injuries
- 11:30 AFL injuries
- 16:00 NRL + AFL historical results
- 16:15 NRL style stats + AFL style stats
- 16:20 NRL round prep + AFL round prep
- 16:40 NRL pricing (wrapper handles export)

Wednesday 14:00 referees task will fetch refs → re-run pricing manually:
```powershell
& "C:\Users\ElliotBladen\Apps\BettingEngine\scripts\run_nrl_pricing.ps1"
```

---

## Outstanding

- AFL equivalent of NRL pricing pipeline (prepare_round.py doesn't do AFL yet)
- BVI weekly Task Scheduler task not yet installed
- `nrl_team_news.py` auto-generator (injuries section from latest-injuries.json)
- Migration 009 fix still needed before next migration run
