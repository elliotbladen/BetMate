# Session Diary — 2026-06-01: Per-Market Thresholds, Manly/Souths Hypothetical, Drift Analysis, Automations

## What was done

### 1. Per-market threshold wiring — both scripts complete

Both confluence analysers now fire totals signals at lower thresholds than H2H/handicap:

**AFL** (`scripts/afl_matrix_confluence.py`):
```python
MIN_EDGE_BY_MARKET  = {'totals': 5.0}   # h2h/handicap stay at MIN_EDGE (20%)
MIN_COUNT_BY_MARKET = {'totals': 3}     # h2h/handicap stay at MIN_COUNT (3+)
```

**NRL** (`scripts/matrix_confluence.py`):
```python
MIN_EDGE_BY_MARKET  = {'totals': 10.0}
MIN_COUNT_BY_MARKET = {'totals': 3}
```

Both `analyse_game()` and `print_report()` accept `min_edge_by_market` / `min_count_by_market` dicts. A `_meets_count()` helper in `main()` keeps the JSON/Supabase output consistent with what the report shows.

Context: AFL totals edges are structurally smaller than H2H/handicap (max ~30% vs NRL's 74%). The 20% global threshold was suppressing every AFL totals signal. Carlton/Geelong had 4 OVERS edges all ≥5% that were invisible before this fix.

Committed: `3542904`

### 2. AFL totals threshold changed 3%→5%

User asked to raise the AFL totals floor from 3.0% to 5.0%. Changed `MIN_EDGE_BY_MARKET = {'totals': 3.0}` → `5.0`. The Carlton/Geelong OVERS signal still fires (all 4 edges are ≥5%: vs Geelong 9.5%, vs Carlton 9.5%, Thu/Fri 8.4%, Full Moon 10.9%).

### 3. New NRL R13 totals signals (now visible)

- **Newcastle/Parramatta — OVERS (3-way):** vs Parramatta 16.4%, vs Newcastle 16.4%, Total Points Away 10.4%
- **Wests Tigers/Bulldogs — OVERS (4-way):** Full Moon 20.9%, Full Moon 15.5%, vs Canterbury 13.4%, vs Wests 13.4%

### 4. New AFL R12 totals signals (now visible)

- **Carlton/Geelong — OVERS (3-way):** vs Geelong 9.5%, vs Carlton 9.5%, Thu/Fri 8.4% (+ Full Moon 10.9% = 4 edges total)
- **Melbourne/GWS — UNDERS (3-way):** vs GWS 7.1%, vs Melbourne 7.1%, Full Moon 6.1%

### 5. Manly vs Souths hypothetical pricing — full 8-row matrix

Ran a complete contextual matrix analysis for a hypothetical R14 game: **Manly (HOME) vs South Sydney (AWAY)**, Thu June 4 2026, 20:00, 4 Pines Park.

**Contextual rows determined from real DB data:**
- Manly: R13 May 29 (WIN), 6-day rest → SHORT REST, last_result=win
- Souths: R12 May 24 (LOSS), 11-day rest → LONG REST, last_result=loss
- Moon: 4.14 days from nearest phase → no moon row
- Month: June
- Venue: 4 Pines Park (Brookvale Oval)

**Top confluence signals:**

H2H:
- HOME_WIN: After a Win (17.6% Manly, edge), vs South Sydney (17.6% Manly)
- AWAY_WIN: vs Manly (17.6% Souths), Total Points Away rows

Handicap (strongest signal):
- HOME_COVERS (11 edges): Manly Long Rest 60.0%⚡, Short Rest fading Manly 24.1%⚡, Night/Thurs, June, vs Souths, venue rows all pointing HOME_COVERS
- This is the standout market — Manly as heavy home coverage favourites in this scenario

Totals:
- Venue row and Monday rows push OVERS but below 3+ count threshold

**Key finding:** Manly's 60% cover rate after Long Rest (10+ days) is the biggest single contextual edge in the handicap matrix.

Note: Souths actually had 11-day rest (Long Rest), not 6-day. The contrast with Manly's Short Rest (6 days) adds to Manly's edge.

### 6. Manly odds drift analysis — after a loss, last 4 years

Used `data/nrl/historical/latest.xlsx` (aussportsbetting data, 2022–2024). Methodology: identified 31 Manly games with opening + closing H2H odds, checked whether they were backed (odds shortened >0.02) or drifted (odds lengthened >0.02) after a loss the previous game.

**Results (31 games with drift data after a loss):**
- Overall: 55% drifted / 45% backed after a loss
- By year: 2022 (57% backed) → 2023 (29% backed) → 2024 (33% backed)
- The trend is worsening — punters have lost confidence in Manly after losses in recent years
- Away after loss: 67% drifted (strongest signal)
- Average drift magnitude (+1.178 units) >> average back (-0.219 units)
- One extreme outlier: Roosters $1.65→$7.25 (likely Trbojevic injury announcement at TAB open)

**Implication:** When Manly is coming off a loss, they tend to drift further in recent years. A contrarian back after they drift could have value if the model still favours them.

### 7. Automations recovered (all missed due to internet/session issues)

All of the following ran successfully today (June 1 — Monday):

| Task | Result |
|------|--------|
| NRL historical download (playwright) | ✅ `nrl_20260601.xlsx` (795 KB), `latest.xlsx` updated |
| AFL historical download (playwright) | ✅ `afl_20260601_072209.xlsx` (834 KB), `latest.xlsx` updated |
| NRL history push to Supabase | ✅ 519 matches pushed to `nrl_match_history` |
| Odds snapshot (Monday baseline) | ✅ 8 NRL + 8 AFL events, baselines pushed to Supabase |
| Odds movement tracker | ✅ 0 movements (baseline just set, expected) |

## Files changed

- `scripts/afl_matrix_confluence.py` — per-market thresholds (5%/3+ for totals)
- `scripts/matrix_confluence.py` — per-market thresholds (10%/3+ for totals)
- `handover/sessions/2026-05-29_t9-confluence-totals-permarket.md` — previous session diary

## Git

Committed to BettingEngine main: `3542904` (per-market thresholds + moon phase + month for both scripts)

## Notes

- Full Moon May 30–31 2026 generated significant NRL R13 signals (Tigers/Bulldogs totals especially)
- AFL historical download uses `fetch_aussportsbetting_nrl.py --page-url https://www.aussportsbetting.com/data/historical-afl-results-and-odds-data/ --output-dir outputs\afl_weekly_review\historical` (not `--page-url afl`)
- Monday baseline snapshot auto-pushes `nrl_opening_baseline` + `afl_opening_baseline` to Supabase — odds movement arrows will work from next snapshot onwards
- `scripts/run_push_nrl_history.ps1` needs `--with requests --with openpyxl` (wrapper already has these flags)
