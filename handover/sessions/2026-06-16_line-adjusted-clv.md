# Session: Line-Adjusted CLV — Mathematical Derivation + Implementation
**Date:** 2026-06-16 (afternoon session, continuation after AFL reprice)

---

## What Was Done

### Problem
User noticed R15 NRL showed only 1 positive CLV despite all 3 bets winning. Root cause: odds-only CLV is wrong for handicap/totals bets where the LINE moves. When Dolphins moved from -3.5 to -8.5 but we took -3.5, comparing our odds (1.85) to the closing standard line's odds (1.85 at -8.5) gave 0% CLV. The true CLV on our specific -3.5 line was ~+20%.

### Mathematical Solution
Used a normal distribution to compute P(cover) given where the closing line landed vs our bet line.

**Formula:**
- Handicap + under: `z = (bet_line - close_line) / σ`
- Over: `z = (close_line - bet_line) / σ`
- `P = Φ(z)`  (cumulative normal)
- `fair_close_odds = (1/P) / VIG_MULTIPLIER`  where VIG = 2/1.90 = 1.0526
- `CLV% = (taken_odds / fair_close_odds - 1) × 100`

When P=0.5 (no line movement), fair_close_odds = 1.90 (correct baseline = actual market offer).

### Sigma Values
Computed from AusSportsBetting historical xlsx data. Key fix: correct residual = `actual_margin + home_line_close` (NOT minus — home_line_close is negative for home fav, so adding it is correct).

| Sport | σ_margin | σ_total | n games | Period |
|-------|----------|---------|---------|--------|
| NRL   | 17.30    | 12.80   | 962     | 2020–2026 |
| AFL   | 32.70    | 27.49   | 976     | 2022–2026 |

Mean bias ≈ 0 for both (NRL +0.12, AFL +0.71) — closing lines are efficiently priced.

### Script Created
`BettingEngine/scripts/compute_line_adjusted_clv.py`
- Reads `BettingEngine/data/clv/running/actual_bets_clv_2026.csv`
- Updates `close_odds` and `clv_pct` for all handicap + totals bets using the line-adjusted formula
- Backs up original as `.csv.bak`
- Prints before/after comparison + summary by market type

Run: `cd BettingEngine && uv run python scripts\compute_line_adjusted_clv.py`

### Results After Running Script
Script updated 58 bets. Notable reversals:
- 0081 Dolphins -3.5: **0.0% → +19.51%** (line moved 5pts in our favour)
- 0049 Under 50.5: **-19.56% → +24.23%** (big under value vs closing 52.5)
- 0032 AFL Under 176.5: **-6.0% → +29.74%**
- 0055 Under 47.5: **-8.65% → +12.43%**
- 0082 Sharks +4.5: **-4.1% → -15.12%** (genuinely bad — line moved 3pts against us)
- 0058 Panthers -5.5: **-11.79% → -26.02%** (genuinely bad)

### Running CLV After update_clv_running.py

**NRL — 55 bets, R8–R15:**
- Avg CLV: **+5.27%**
- Positive rate: **70.9%** (39/55)
- P&L: **+$169.75**

**AFL — 43 bets, R8–R14:**
- Avg CLV: **+0.76%**
- Positive rate: **46.5%** (20/43)
- P&L: **-$4.83**

**By market type:**
- NRL totals: avg +6.77%, 9/12 positive → real edge
- AFL totals: avg +6.98%, 7/11 positive → real edge
- NRL handicap: avg -0.06%, 9/18 → neutral
- AFL handicap: avg -2.41%, 7/17 → slight leak

**Conclusion: Totals betting is the genuine edge. Handicap is neutral on NRL, dragging on AFL.**

---

## Also in This Session (Carry-over from Prior Context)

### researchData.ts Fills (partial)
Updated predictedLine / closingPrice for 4 NRL MODEL_BETS entries:
- id:28 (Dolphins Win, R11): predictedLine = 1.86 (from r11 CSV fair_away_odds)
- id:49 (Souths Win, R15): predictedLine = 1.19, closingPrice = 1.43
- id:50 (Dolphins -3.5, R15): predictedLine = 6.7 (model margin), closingPrice = 1.85 (line-adjusted)
- id:51 (Sharks +4.5, R15): predictedLine = -10.4 (model), closingPrice = 1.95 (line-adjusted)

Remaining nulls: ids 7, 22 (R8/R9, no pricing CSVs).

**Note:** Older MODEL_BETS entries in researchData.ts (pre-R15) still have odds-only closingPrice values. The research page CLV display for those bets is NOT line-adjusted. Bulk update is pending — script generates fair_close_odds for all 58 bets; could map back to MODEL_BETS IDs.

---

## BETTING RULE — Model Alignment Required
**Established:** 2026-06-17

**Rule:** Only take a handicap or H2H bet if BOTH the rules model AND the ML model agree on the direction.

- Handicap: both `rules_margin` and `ml_margin` must point to the same team winning
- H2H: both `rules_home_odds`/`rules_away_odds` and `ml_h2h` must favour the same side
- If one model has Home -28 and the other has Away +5 (GWS v Carlton R15 style) → DO NOT BET handicap/H2H on either side until alignment
- Totals: same rule — both `rules_total` and `ml_total` must be on the same side of the market line

**Why:** CLV analysis showed AFL handicap at -2.41% avg. Looking back at the misses, several involved taking lines where rules and ML disagreed (e.g. backing the rules model side when ML was pointing the other way). Agreement between both models is a minimum filter before any bet.

## Pending

- [ ] Bulk update `closingPrice` in researchData.ts MODEL_BETS + AFL_MODEL_BETS (R8–R14 entries) using line-adjusted fair_close_odds from the CSV — makes research page CLV match actual_bets_clv_2026.csv
- [ ] NRL R15 + AFL R14 weekly bets file: create in `BettingEngine/data/bets/weekly/`
- [ ] Install Thursday AFL R15 reprice task as admin: `! & "C:\Users\ElliotBladen\Apps\BettingEngine\scripts\install_afl_r15_thursday_task.ps1"`
- [ ] Fix emotional scraper Hawthorn/St Kilda attribution bug (Hawthorn shouldn't get shame_blowout when they WON by 100+)
- [ ] End-of-season: re-run compute_line_adjusted_clv.py to keep all bets updated as R15/R16 close

---

## Key Formulas for Future Reference

```
# For handicap + under bets (from home team perspective):
z = (bet_line - close_line) / σ
P = Φ(z)

# For over bets:
z = (close_line - bet_line) / σ
P = Φ(z)

# CLV:
fair_close = (1/P) / (2/1.90)   # vig-adjusted
CLV% = (taken_odds/fair_close - 1) * 100

# σ: NRL margin=17.30, total=12.80 | AFL margin=32.70, total=27.49
```

The sign convention works for both home and away handicap bets because the home_line convention
already encodes direction (home fav is negative, home dog is positive). Away bet line is
just the negation: if you bet away at +X, bet_line = X, close_line = close_away_line.
