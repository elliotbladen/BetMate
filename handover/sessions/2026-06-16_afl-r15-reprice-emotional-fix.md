# Session: AFL R15 Full Reprice + Emotional Scraper Fix
**Date:** 2026-06-16  
**Duration:** ~2 hours across two context windows

---

## What Was Done

### 1. AFL R15 Injuries — Researched + Entered
Searched internet for all 14 playing teams (byes: Brisbane, Sydney, Essendon, West Coast).
Added `INJURIES[15]` block to `BettingEngine/scripts/prepare_afl_round.py`.

Key players out:
- **GWS**: Tom Green (ACL season), Josh Kelly (hip TBC), Sam Taylor (hamstring TBC) → compound penalty
- **Port Adelaide**: Connor Rozee (season), Sam Powell-Pepper (TBC), Jack Lukosius (TBC) → compound penalty
- **Western Bulldogs**: Sam Darcy (ACL season), Bailey Williams (hamstring)
- **Collingwood**: Brayden Maynard (shoulder likely miss), Jamie Elliott (season)
- **Richmond**: 4 outs — Gibcus, Lalor, Rioli, Nankervis
- **North Melbourne**: Coleman-Jones (head TBC), Archer (season)

### 2. Emotional Scraper Fixes (`scrapers/afl_emotional.py`)
Three bugs fixed:

**a. Missing flag types** — `VALID_FLAG_TYPES` was missing `shame_blowout` and `losing_streak`.

**b. System prompt too conservative** — Changed "0–2 per round" to "2–5 per round", added descriptions for shame_blowout/losing_streak with flag strength guide (major=60+pts, normal=40-59pts).

**c. No form data** — Added `load_recent_form()` function that reads `BettingEngine/outputs/afl_weekly_review/historical/latest.xlsx` via openpyxl. Returns last 2 results per team (margin from team's perspective). Added `RECENT FORM` section to the Claude prompt so it can detect shame blowouts and losing streaks.

Added `--with openpyxl` to the Thursday reprice script's uv run command.

**Result after fixes:** Claude returned 6 flags (was 1 before):
- Adelaide Crows — personal_tragedy/major (Jordan Dawson brother died)
- Richmond Tigers — losing_streak/normal (3+ losses including 114pt thrashing)
- Richmond Tigers — shame_blowout/major (114pt loss to Sydney)
- Western Bulldogs — shame_blowout/normal (57pt loss to Adelaide)
- Gold Coast Suns — losing_streak/normal (2 losses including 45pt margin)
- Hawthorn Hawks — shame_blowout/normal (**ERROR** — Claude assigned wrong team. Notes say "St Kilda was smashed by Hawthorn" — the flag should be St Kilda, not Hawthorn. St Kilda has since rebounded anyway. Net effect: Hawthorn gets ~+1.5 T6 bonus it doesn't deserve. Discount 1.5pts from Hawks line in Suns vs Hawks.)

### 3. Emotional Loading Bug Fixed (`BettingEngine/scripts/prepare_afl_round.py`)
`load_external_round_prep()` had a strict `round == round_num` guard. When `latest-emotional.json` was from R14 (before Tuesday's scrape updated it), R15 flags were silently blocked.

Fix: changed to `file_round <= round_num` so any file from the current or previous round flows through.

### 4. Full Reprice Run
Pipeline: game_log.py → prepare_afl_round.py → _export_afl_prices.py → afl_matrix_confluence.py  
Output: `BettingEngine/results/r15_afl_2026.csv`

All 7 tiers confirmed firing including T6 emotional and T7 weather (all venues).

### 5. Thursday Reprice Scripts Created
- `BettingEngine/scripts/run_afl_r15_thursday_reprice.ps1` — runs emotional scraper + full price + export + matrix at 14:10
- `BettingEngine/scripts/install_afl_r15_thursday_task.ps1` — Task Scheduler installer (requires admin)
- User must run installer script as admin: `! & "...\install_afl_r15_thursday_task.ps1"`

---

## R15 Final Prices

| Game | Rules Margin | ML Margin | Matrix |
|------|-------------|-----------|--------|
| Freo vs Cats | Freo −11.9 / 196pts | Freo −16.5 / 151pts | 3-way FREO COVERS |
| Suns vs Hawks | Hawks −10.4 / 168pts | Hawks −14.4 / 132pts | 5-way SUNS COVER |
| Crows vs Demons | Adel −34.0 / 190pts | Adel −32.0 / 164pts | 3-way BACK MELB |
| GWS vs Carlton | GWS −28.1 / 177pts | **Carlton −4.7 / 152pts** | Totals OVERS only |
| Pies vs Power | Pies −29.3 / 165pts | Pies −8.0 / 163pts | **100% both H2H+hcp** |
| **Tigers vs NM** | **NM −14.6 / 158pts** | **NM −33.3 / 148pts** | **5-way BACK NM + 5-way NM COVERS** |
| Saints vs Dogs | Dogs −5.4 / 174pts | 50/50 / 173pts | 4-way DOGS COVER + 3-way BACK DOGS |

---

## Top Signals

**1. Tigers vs NM — NM (strongest):** Both models + 5-way matrix (H2H + handicap). Richmond 3+ loss streak, 114pt shame blowout. Clearest triple-confirmation of the round.

**2. GWS vs Carlton — Carlton value (ML only):** ML says Carlton by 4.7 vs rules GWS by 28.1. If market has GWS ~1.25–1.30, Carlton at $3.50+ is massive ML value. Manual review required — ELO gap is real.

**3. Pies vs Power — Back Pies:** 100% matrix confidence at MCG. Rules −29.3. ML −8.0 more cautious. Injuries roughly neutral.

**4. Saints vs Bulldogs — Bulldogs:** 4-way matrix + 3-way H2H. Rules −5.4. T3 bounce-back (−2.5) and T6 (+1.5) both favour Dogs.

**Totals:** All model totals running below market — especially ML totals (131–165 vs rules 157–196). Any market line at or above rules total = UNDER value.

---

## Odds Movement Snapshot (from earlier in session)

From `data/odds_movements/latest.csv`:
- **Collingwood**: 5 books shortening H2H
- **Carlton**: 5 books, 2.7% shortening
- **NM**: Betfair exchange moving (smart money)
- **Adelaide**: 7 books shortening (but personal tragedy flag — public front-running)
- **Hawthorn**: 7 books shortening (public trap — Suns at home with 5-way matrix)
- **Only UNDER shortening**: Freo/Geelong (−1.6% Sportsbet)
- All other totals: OVER shortening (public money)

---

## Pending

- [ ] Install Thursday task as admin: `! & "...\install_afl_r15_thursday_task.ps1"`
- [ ] Watch 2pm Thursday squad drop — update INJURIES[15] if new outs appear, re-run prepare_afl_round.py manually
- [ ] File bets to `BettingEngine/data/bets/actual_bets_2026.csv` after placing
- [ ] After closing lines available: run CLV scripts
- [ ] Fix emotional scraper Hawthorn/St Kilda attribution bug — add validation: if flag_type is shame_blowout/losing_streak, verify team is actually in the fixture (already is), and cross-check that team lost the blowout (not won it)
