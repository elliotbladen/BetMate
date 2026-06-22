# Session: AFL Model — predictedLine backfill
**Date:** 2026-06-15  
**Commit:** `20b755e`

---

## What was done

Filled `predictedLine` for **41 out of 56** `AFL_MODEL_BETS` in `lib/researchData.ts`.

The `predictedLine` column shows the model's fair price/line for the market bet:
- **H2H bets** → model's fair H2H odds for the backed team (`rules_home_odds` or `rules_away_odds`)
- **Handicap bets** → model's predicted winning margin for the favoured team (absolute value from `rules_margin`)
- **Total bets** → model's predicted total score (`rules_total`)

---

## Sources used per round

| Round | File | Columns used |
|-------|------|--------------|
| R7 | `BettingEngine/data/pricing/afl/AFL_PRICING_R07_2026-04-28.csv` | `final_margin`, `final_total`, `home_odds`, `away_odds` |
| R8 | `BettingEngine/data/pricing/afl/AFL_PRICING_R08_2026-05-05.csv` | same |
| R9 | `BettingEngine/data/pricing/afl/AFL_PRICING_R09_2026-05-12.csv` | `fair_margin_home`, `fair_total`, `fair_home_odds`, `fair_away_odds` |
| R11 | `BettingEngine/data/pricing/afl/AFL_PRICING_R11_2026-05-25.csv` | `rules_margin`, `rules_total`, `rules_home_odds`, `rules_away_odds` |
| R12 | `BettingEngine/results/r12_afl_2026.csv` | same |
| R13 | `BettingEngine/results/r13_afl_2026.csv` | same |
| R14 | `BettingEngine/results/r14_afl_2026.csv` | same |

---

## Null entries (15 total)

| ids | Reason |
|-----|--------|
| 1-7 | R5-R6 — no AFL pricing files for these rounds |
| 10 | "Game 1.8" on Eagles vs Saints — ambiguous which team backed; model price (1.07 or 16.34) doesn't match market 1.80 |
| 21-26 | R10 — no AFL pricing file found (no `r10_afl_2026.csv` or `AFL_PRICING_R10_*.csv`) |
| 53 | "Over 79.5 2nd Half" — model has no half-time total |

---

## Key predictedLine values (notable divergences)

| id | Match | Market | predictedLine | takenPrice | Notes |
|----|-------|--------|--------------|------------|-------|
| 14 | Adelaide vs Port | Adelaide -9.5 | **55.7** | 1.89 | Model had Adelaide by 55.7, market only -9.5 |
| 17 | Port vs WB | Port Adelaide Win | **2.94** | 1.96 | Model had Port as slight dog at 2.94 — market priced them as favourite |
| 18 | Gold Coast vs StKilda | GC -17.5 | **48.9** | 1.89 | Model had GC winning by 48.9, market -17.5 |
| 32 | Geelong vs Swans | Swans +10.5 | **5.8** | 1.90 | Model had Geelong by only 5.8, Swans +10.5 was value |
| 45 | Sydney vs StKilda | Sydney -29.5 | **54.4** | 1.89 | Model had Sydney by 54.4, market -29.5 underestimated |

---

## Files changed

- `lib/researchData.ts` — `predictedLine` filled for 41 AFL_MODEL_BETS (ids 8-9, 11-20, 27-52, 54-56)
