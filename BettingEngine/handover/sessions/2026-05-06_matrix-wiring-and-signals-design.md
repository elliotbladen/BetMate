# Session: Matrix Wiring + Signals Architecture Design
**Date:** 2026-05-06

---

## Matrix Scripts — Path Fix + Wired into prepare_round.py

### Problem
All three NRL matrix scripts had hardcoded Mac paths:
- SOURCE_PATH: `/Users/elliotbladen/Downloads/nrl (5).xlsx`
- OUTPUT_PATH: `/Users/elliotbladen/Betting_model/outputs/...`

Scripts were broken on Windows and couldn't run automatically.

### Fix — All Three Scripts
Updated `nrl_h2h_matrix.py`, `nrl_handicap_matrix.py`, `nrl_team_totals_matrix.py`:

- SOURCE_PATH now resolves to `BetMate/data/nrl/historical/latest.xlsx`
  (same file downloaded by `fetch_aussportsbetting_nrl.py` each Tuesday)
- OUTPUT_PATH now resolves relative to BettingEngine root: `outputs/nrl_*.xlsx`
- Both paths respect env vars: `BETMATE_ROOT` and `NRL_HISTORICAL_XLSX`
- Pattern is identical across all three scripts for consistency

### Step 8 Added to prepare_round.py
Added `step8_regenerate_matrices()` and `--skip-matrices` flag.

Behaviour:
- Runs all three matrix scripts as subprocesses after step 7 (pricing)
- Subprocess failures are WARNINGS not fatal — stale matrices beat a blocked pipeline
- Skipped automatically on `--dry-run`
- Skipped with `--skip-matrices` flag (use when historical xlsx not yet updated)
- Each script still independently runnable as before

Pipeline is now:
```
step 0   load fixture
step 0b  import style stats
step 1   verify previous results
step 2   rebuild team stats
step 3   rebuild ELO
step 4   load injuries
step 5   load referees
step 6   validate
step 6a  fetch weather
step 7   price (T1-T8)
step 8   regenerate matrices  ← NEW
```

---

## Signals Architecture (designed, not built yet — build next week)

### Triple Confluence Rule (Option A — confirmed by user)
All 3 matrices must agree at the same threshold tier:

| Tier | Criteria | Action |
|------|----------|--------|
| Gold | All 3 matrices ≥20% edge, same direction | Bet — full quarter-Kelly |
| Silver | All 3 matrices 10-20% edge, same direction | Bet — half stake |
| Partial | 2 of 3 ≥20% | Log only, no recommendation |
| Single | 1 market only | Research, not a signal |

"Same direction" is enforced — H2H/handicap/totals must all point the same team.

### ML Role
- ML shadow predictions used as confidence modifier, not primary signal
- Directional agreement → `ml_confirmed` ✅
- Directional disagreement → `ml_flag` ⚠️ (review before placing — yellow flag, not veto)

### Bookmaker for EV
- Pinnacle for EV calculation (sharpest line = true probability)
- Best available AU bookie (Sportsbet/TAB/Neds) for actual stake price

### Codex Notes (from handover review)
- `market_intel_profiles` has 81 AFL line movement profiles — useful for signals context
- `market_intel_signals` table exists but empty — live signal generation not built yet
- Betmate import layer (`betmate_ingest/`) exists — reads already-collected files, not a scraper
- Migration 009 broken — fix before running new migrations next week
- AFL source paths in Codex sessions used Mac paths — updated to Windows in today's session

---

## Pending
- Thursday: R10 injuries re-scrape + referee load + re-run prepare_round.py
- Monday: AFL automation build (open AFL_PREP.md first)
- Next week: wire signals pipeline (triple-confluence + ML + DB writes)
- Before signals: fix migration 009
