# Session Diary — 2026-05-27 — AFL R12 + NRL R13 Pricing

## What was done

### AFL R12 Pricing — COMPLETE
- ELO rebuilt from `outputs/afl_weekly_review/historical/latest.xlsx`
- Added AFL R12 fixture, injuries, emotional flags, and weather to `BettingEngine/scripts/prepare_afl_round.py`
- R12 fixture (7 games — 4 byes: Adelaide, Gold Coast, North Melbourne, Port Adelaide):
  - St Kilda vs Hawthorn (Thu, Marvel)
  - Carlton vs Geelong (Fri, Marvel)
  - Sydney vs Richmond (Sat, SCG)
  - Brisbane vs Fremantle (Sat, Gabba)
  - Western Bulldogs vs Collingwood (Sat, Marvel)
  - Melbourne vs GWS (Sun, MCG)
  - West Coast vs Essendon (Sun, Optus)
- Updated `_export_afl_prices.py` to query R12 (was hardcoded to R11)
- Output: `BettingEngine/results/r12_afl_2026.csv` (7 rows)
- Analysis: `BettingEngine/outputs/results/r12_afl_pricing_2026.md`

**AFL R12 top signals:**
1. Collingwood +7.5 — Bulldogs have both rucks out (Darcy season + English head). Model coin flip, ML goes Magpies. Market overrating Bulldogs.
2. Bulldogs/Magpies UNDER 180.5 — model 161.3 (19pt gap). Strongest totals signal of the round.
3. Eagles +10.5 — rules says Eagles win, ML says Bombers by only 6.8. Market -10.5 is too aggressive for Essendon.
4. Eagles/Bombers UNDER 165.5 — model 152.8 (12.7pt gap, bias-adjusted even lower).
5. Hawks -12.5 — both models (rules -30.4, ML -16.3) well above market line.
6. Carlton +23.5 — ML divergence play (rules -44.1 vs ML -9.8 = 34.3pt gap, biggest of round).

### NRL R13 Pricing — PRELIMINARY
- NRL R13 pricing auto-ran at 06:30 this morning via Task Scheduler
- Analysis written to `BettingEngine/outputs/results/r13_nrl_pricing_2026.md`
- **Critical: T5 and T6 both empty** — injuries stale (R12 from May 19), refs not announced until 14:00 today

**NRL R13 pre-update signals:**
1. Parramatta +14.5 — model Knights by 9.65 vs market 14.5 (4.85pt gap). Standout signal even before injuries load.
2. Panthers -7.5 — model 10.47 vs market 7.5 (3pt gap).
3. Broncos/Dragons UNDER 54.5 — model 47.6.
4. Panthers/Warriors UNDER 48.5 — model 44.5.

## What still needs doing

### TODAY (before R13 bets)
1. **Run NRL injuries scraper** — `uv run python scrapers/nrl_injuries.py`
2. **Wait for refs** — Task Scheduler fires at 14:00. If it doesn't run: `uv run python scrapers/nrl_referees.py`
3. **Re-run NRL R13 pricing** — `& C:\Users\ElliotBladen\Apps\BettingEngine\scripts\run_nrl_pricing.ps1`
4. **Monitor Sean Darcy (Fremantle)** — listed doubtful. Update AFL R12 Brisbane/Fremantle bet if he's out.

### THIS WEEK
- R12 CLV: opening/closing lines not yet filed — run after Sportsbet settles R12 games
- R12 NRL results: load to DB once results published Tuesday

## File changes
- `BettingEngine/scripts/prepare_afl_round.py` — added R12 to FIXTURE, INJURIES, EMOTIONAL_FLAGS, WEATHER
- `BettingEngine/scripts/_export_afl_prices.py` — updated to R12
- `BettingEngine/results/r12_afl_2026.csv` — NEW
- `BettingEngine/outputs/results/r12_afl_pricing_2026.md` — NEW
- `BettingEngine/outputs/results/r13_nrl_pricing_2026.md` — NEW
- `CLAUDE.md` — updated Current State with R12/R13 notes
