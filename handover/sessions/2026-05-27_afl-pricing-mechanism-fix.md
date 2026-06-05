# Session Diary — 2026-05-27 — AFL Pricing Mechanism Fix

## What was done

### Root cause investigation — AFL totals underpricing

Investigated the planned AFL T1 pricing mechanism fix. The problem:
- Model accuracy data (R8–R9) showed AFL totals were running **~8–13pts below market open**
- CLAUDE.md (and the R12 analysis) had the direction **backwards** — stating model runs "10–25pts above market"
- This caused wrong-direction totals signals in the R12 analysis file

**Root cause identified:**
- `LEAGUE_AVG_PER_TEAM = 83.5` was stale (from 2022–2025 data, avg 83.6)
- 2026 actual average: **90.22 pts/team** (calculated from features_afl.csv, n=99 R1–R11 games)
- The gap is ~6.7pts/team. With 25% T1_REGRESSION anchor, this costs ~1.7pts/team = ~3.4pts/game on totals
- `compute_season_calibration()` was compensating with `total_correction = +3.0` — but the constant itself was wrong

**Key insight from model accuracy data:**
- R8: rules_total_vs_actual_bias = -20.44 (model badly below actual — early season artifact)
- R9: rules_total_vs_actual_bias = +4.00 (model approximately right on actual)
- BUT market prices AFL totals ~8-12pts ABOVE actual scoring (systematic market premium)
- Therefore: UNDER bets have value through **market overpricing**, not because model > market

**Pattern in R12 game-by-game model vs market totals:**
- Games where model is ABOVE market: Sydney/Richmond (+17), Melbourne/GWS (+15), Carlton/Geelong (+8), Brisbane/Fremantle (+3)
- Games where model is BELOW market: Bulldogs/Magpies (-20), Eagles/Bombers (-14), Saints/Hawks (-5)
- High-ELO dominant games → model overproduces totals (strong teams' scoring rates inflate predictions)
- Low-ELO/injury-heavy games → model underproduces (weak teams' low rates carry through)

### Fix applied

**`BettingEngine/scripts/prepare_afl_round.py`**
- Updated `LEAGUE_AVG_PER_TEAM` from `83.5` → `90.2`
- Comment updated: "2026 actual avg: 90.22 per team (R1-R11, n=99; was 83.5 from 2022-2025)"

**Effect on R12 calibration after the fix:**
- total_correction changed from +3.0 → **-1.2** (model now slightly above actual on average = well calibrated)
- All model totals shifted ~1pt lower (net of anchor increase vs calibration reduction)
- Handicap margins unchanged (ELO-based, not affected by scoring anchor)

**`outputs/results/r12_afl_pricing_2026.md` — signal corrections:**
- Carlton/Geelong totals: corrected from UNDER → **OVER 179.5** (model 186.9, +7.4pts above market)
- Sydney/Richmond totals: corrected from UNDER → **Skip** (model above market but conflicting signals)
- Melbourne/GWS totals: corrected from UNDER → **Lean OVER 176.5** (model 190.9, +14.4pts above market, weak)
- Eagles/Bombers totals: corrected from UNDER (strong) → **Skip** (rules 151.8 vs ML 167.1 — 15.3pt divergence, no consensus)
- Bulldogs/Magpies UNDER 180.5: **unchanged** — model 160.3, -20pts below market, correct direction
- Eagles/Bombers UNDER 165.5: changed to skip due to ML divergence

**Corrected signal summary for AFL R12:**

| Game | Signal | Side | Confidence |
|------|--------|------|------------|
| Bulldogs vs Magpies | Handicap | Collingwood +7.5 | **High** |
| Bulldogs vs Magpies | Totals | UNDER 180.5 (model 160.3) | **High** |
| Eagles vs Bombers | Handicap | Eagles +10.5 | **High** |
| Eagles vs Bombers | Totals | SKIP (rules/ML 15.3pt divergence) | — |
| Saints vs Hawks | Handicap | Hawks -12.5 (model -30.4) | **Medium** |
| Saints vs Hawks | Totals | UNDER 182.5 (model 177.1, -5.4pts) | **Low-Med** |
| Blues vs Cats | Handicap | Carlton +23.5 (ML divergence play) | **Medium** |
| Carlton vs Geelong | Totals | OVER 179.5 (model 186.9, +7.4pts) | **Low-Med** |
| Melbourne vs GWS | Handicap | Melbourne -5.5 | **Low** |

**CLAUDE.md (Apps)** — two wrong notes fixed:
- AFL R12 pricing notes: "model runs 10–25pts high" → "model runs ~8pts BELOW market on average. Per-game direction varies."
- AFL R11 pricing notes: same wrong direction → corrected
- Pending work entry updated to note fix applied

**BettingEngine/CLAUDE.md** — updated current state with AFL R12 and NRL R13 notes.

### Files changed
- `BettingEngine/scripts/prepare_afl_round.py` — LEAGUE_AVG_PER_TEAM 83.5→90.2
- `BettingEngine/outputs/results/r12_afl_pricing_2026.md` — signals corrected, bias note corrected
- `CLAUDE.md` (Apps root) — AFL totals bias direction corrected in 2 places + pending work updated
- `BettingEngine/CLAUDE.md` — current state updated with R12 AFL + R13 NRL
- `handover/sessions/2026-05-27_r12-afl-r13-nrl-pricing.md` — already existed from earlier session

## What still needs doing

### TODAY (before R13 bets)
1. Close r12_afl_2026.csv in Excel, then re-export: `& ".\.venv\Scripts\python.exe" scripts\_export_afl_prices.py`
2. Run NRL injuries scraper: `uv run python scrapers/nrl_injuries.py`
3. Wait for refs (Task Scheduler fires Wed 14:00), or run manually: `uv run python scrapers/nrl_referees.py`
4. Re-run NRL R13 pricing: `& C:\Users\ElliotBladen\Apps\BettingEngine\scripts\run_nrl_pricing.ps1`
5. Monitor Sean Darcy (Fremantle, doubtful) — AFL R12 Brisbane/Fremantle

### THIS WEEK
- NRL H2H home bias: rules overrates home teams +9-11% consistently. T4 venue calibration review (NRL-side) is the remaining pricing mechanism fix.
- Add AFL R10/R11 to MODEL_ACCURACY_RUNNING_2026.csv (need to generate CLV comparison files first)
- R12 CLV: file after closing lines available

## Technical notes

### Why LEAGUE_AVG_PER_TEAM was wrong but total_correction compensated
`compute_season_calibration()` computes `total_correction = mean(actual - predicted)` across all 2026 games. With the stale 83.5 anchor, it computed +3.0 to bridge the gap. After updating to 90.2, it computes -1.2 (model now ~1.2pts above actual on average). The net prediction change is only ~1pt/game — cosmetically the same numbers.

The value of the fix is semantic: the calibration offset now means what it should (model overestimates slightly vs recent data), rather than compensating for a stale constant.

### AFL totals vs market: market premium
The AFL totals market sets lines ~8-12pts above actual scoring. This is a consistent pattern in R8-R9 data. The model tracks actuals well (R9: only +4pts vs actual). So systematic UNDER betting on AFL totals likely has edge — but through market overpricing, not model being above market.

This changes how to interpret totals signals:
- OLD logic: model > market → discount down by AFL bias → UNDER
- CORRECT logic: compare model vs market directly. Market premium means UNDER is generally reasonable. But if model is ALREADY above market, that's an OVER signal (no additional discount).
