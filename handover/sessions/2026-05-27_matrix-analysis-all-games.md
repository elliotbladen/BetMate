# Session Diary — 2026-05-27 — Matrix Analysis: NRL R13 + AFL R12

## What was done

Three matrix scripts built and run. Results summary:

---

### 1. Cronulla Sharks vs Manly Sea Eagles — NRL R13, Fri 29 May (H2H matrix)

**7-way confluence — all backing Cronulla / opposing Manly. #1 signal of the round.**

| Condition | Manly actual | Implied | Edge |
|-----------|-------------|---------|------|
| As away team | 32.0% | 48.2% | 34% OPPOSING |
| Night games (≥18:00) | 38.9% | 50.7% | 23% OPPOSING |
| Thu/Fri games | 31.6% | 51.4% | 39% OPPOSING |
| After a win | 44.4% | 57.2% | 22% OPPOSING |
| Short rest (≤6 days) | 29.4% | 53.2% | 45% OPPOSING |
| vs Cronulla H2H | 14.3% | 39.4% | 64% OPPOSING |
| May games | 31.2% | 49.4% | 37% OPPOSING |

**Signal: Cronulla -2.5 — HIGH.** Model -4.2 vs market -2.5. Update after T5/T6 load.
Script: `scripts/_cronulla_manly_matrix.py`

---

### 2. Melbourne Storm vs Sydney Roosters — NRL R13, Sat 30 May (H2H matrix)

**No signal. Conflicting 2-vs-2.**

| Signal | Direction | n |
|--------|-----------|---|
| Storm H2H vs Roosters | 25% BACKING Storm | 10 |
| Storm May games | 21% OPPOSING Storm | 16 |
| Roosters H2H vs Storm | 51% OPPOSING Roosters | 10 |
| Roosters full moon (near-full, May 31) | 24% BACKING Roosters | 13 |

H2H edges from both sides align on Storm, but May + full moon push back equally. Model = market at Roosters -1.5. Coin flip confirmed. **Skip handicap. Lean UNDER 49.5.**
Script: `scripts/_storm_roosters_matrix.py`

---

### 3. Sydney Swans vs Richmond Tigers — AFL R12, Sat 30 May (TOTALS matrix)

**No signal. Conflicting 1-vs-1.**

| Signal | Direction | n |
|--------|-----------|---|
| Sydney full moon (±1 day, nearest full May 31) | 36% OVER | 7 |
| Richmond May games | 27% UNDER | 21 |

Full moon pushes OVER (Sydney avg 179 vs line 170 near full moons, n=7 — thin). May games push UNDER (Richmond avg 166 vs line 170 in May, n=21). These conflict. Rules model 195.6 vs ML 178.0 vs market 178.5 — ML is at market. Sydney injuries (Gulden, Adams, Campbell, King) suppress offensive upside. **SKIP totals confirmed.**
Script: `scripts/_afl_totals_matrix.py`

---

## Scripts created

| Script | Game | Type | Result |
|--------|------|------|--------|
| `scripts/_cronulla_manly_matrix.py` | Cronulla vs Manly NRL R13 | H2H win% | 7-way confluence BACK CRONULLA |
| `scripts/_storm_roosters_matrix.py` | Storm vs Roosters NRL R13 | H2H win% | No signal |
| `scripts/_afl_totals_matrix.py` | Sydney vs Richmond AFL R12 | Totals over/under% | No signal |

## Files updated

- `outputs/results/r13_nrl_pricing_2026.md` — Cronulla/Manly section upgraded + added to signal table; Storm/Roosters section updated
- `outputs/results/r12_afl_pricing_2026.md` — Sydney/Richmond totals section updated with matrix result
- `BettingEngine/CLAUDE.md` — R13 top signals updated (Cronulla -2.5 now #1)

## Fixture note

AFL R12 runs simultaneously with NRL R13 — Sydney vs Richmond is Sat 30 May, same day as Storm vs Roosters. 

## What still needs doing before game time

### NRL R13 (Cronulla game kicks off Fri 20:00)
1. **Run injuries scraper NOW**: `uv run python scrapers/nrl_injuries.py` (T5 stale)
2. **Wait for refs Wed 14:00**, or run manually: `uv run python scrapers/nrl_referees.py`
3. **Re-run pricing**: `& C:\Users\ElliotBladen\Apps\BettingEngine\scripts\run_nrl_pricing.ps1`
4. **Check Manly injury list** — any outs strengthen Cronulla case
5. **Check Cronulla market H2H** — model 1.57, expect market ~1.50-1.55. Assess EV.

### AFL R12 (games Sat/Sun)
- Monitor Sean Darcy (Fremantle, doubtful for Brisbane game)
- No matrix action needed for Sydney/Richmond

## Key insight: full moon OVER for Sydney

Sydney near full moons go OVER the totals line 71.4% of the time (n=7, avg actual 179 vs avg line 170, +9pt). This is a notable pattern even at small sample. Worth tracking for future Sydney games around full moons — if the sample grows to 15+ with same direction, this becomes a usable signal.

The mechanism might be: full moon games often coincide with marquee round fixtures where Sydney plays up, and the market sets conservative lines for rivalry games.
