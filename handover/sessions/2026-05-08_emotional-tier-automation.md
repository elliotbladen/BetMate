# Session 2026-05-08 — T7 Emotional Tier Automation

## What was done

### Context
T7 emotional tier was fully wired in the pricing engine (tier7_emotional.py, load_emotional_round.py, prepare_round.py all calling it) but `emotional_flags` table had 0 rows — it was never fed any data. User wanted BetMate to be the information hub that generates and holds emotional flag data, with BettingEngine pulling from it exactly like it already pulls injuries and referees.

### Files created

**`BetMate/lib/scraper/nrl_emotional.py`**
- Runs every Tuesday at 11:00 (before BettingEngine's 19:00 prepare_round run)
- Reads BetMate's `data/nrl/news_flags/processed/latest.json` and `data/nrl/injuries/processed/latest-injuries.json`
- Auto-detects deterministically:
  - `shame_blowout`: queries BettingEngine DB for 30+ point losses last round
  - `rivalry_derby`: checks fixture against hardcoded NRL rivalry pairs list
  - `origin_boost`: checks if round falls in post-Origin camp window (2026 dates hardcoded)
- Calls Claude (claude-opus-4-7) with all data to identify: milestone, new_coach, star_return, farewell, personal_tragedy, must_win
- Auto-finds BettingEngine DB at `../BettingEngine/data/model.db` (sibling directory)
- Outputs `data/nrl/emotional/processed/latest-emotional.json`
- Usage: `uv run --with anthropic --with requests python lib/scraper/nrl_emotional.py --round 11`
- Requires: `ANTHROPIC_API_KEY` env var (Claude calls silently skipped if missing)

**`BetMate/scripts/install_nrl_emotional_task.ps1`**
- Installs Task Scheduler task "BetMate NRL Emotional Flags" — Tuesday 11:00

**`BetMate/data/nrl/emotional/`** (new directory tree)
- `raw/YYYY/round-N.json` — raw API payload
- `processed/YYYY/round-N.json` — validated flags
- `processed/latest-emotional.json` — consumed by BettingEngine

### Files modified

**`BettingEngine/scripts/prepare_round.py`**
- Added `betmate_latest_emotional()` path resolver (mirrors betmate_latest_injuries/referees pattern)
- Added `step5b_load_emotional()` — reads BetMate's latest-emotional.json, upserts into emotional_flags table
- Wired into main pipeline between step 5 (referees) and step 6 (validate)
- Respects `--skip-load` flag (same as injuries/referees)
- If file missing or wrong round: warns + tells user how to regenerate, does not fail

## Architecture

```
Tuesday 11:00  nrl_emotional.py  →  data/nrl/emotional/processed/latest-emotional.json
Tuesday 19:00  prepare_round.py  →  reads latest-emotional.json  →  emotional_flags table
                                 →  T7 fires during pricing (already wired)
```

Same pattern as:
```
Monday  10:00  nrl_injuries.py   →  data/nrl/injuries/processed/latest-injuries.json
Monday  19:03  prepare_round.py  →  reads latest-injuries.json  →  injury_reports table
```

## To activate

1. Set `ANTHROPIC_API_KEY` in environment (or `.env.local`)
2. Install task: `powershell -ExecutionPolicy Bypass -File scripts\install_nrl_emotional_task.ps1`
3. Test dry run: `uv run --with anthropic --with requests python lib\scraper\nrl_emotional.py --round 11 --dry-run`

## Pending

- Update CLAUDE.md with new task and file locations
- Add ANTHROPIC_API_KEY to .env.local.example
- Tune Claude system prompt after first few rounds (adjust confidence thresholds)
- Consider AFL equivalent: `afl_emotional.py` after AFL pipeline is built
