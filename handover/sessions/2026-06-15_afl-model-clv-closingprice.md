# Session: AFL Model CLV — closingPrice backfill
**Date:** 2026-06-15  
**Commit:** `626888f`

---

## What was done

Filled `closingPrice` for **37 out of 56** `AFL_MODEL_BETS` in `lib/researchData.ts`.  
CLV column and Beat CLV stat are now live on the Research page AFL Model tab.

### Data sources used

| Source | Rounds covered |
|--------|----------------|
| `BettingEngine/outputs/afl_weekly_review/historical/latest.xlsx` | R5-R13 (games through Jun 8) |
| `BettingEngine/data/clv/afl/AFL_CLV_R08_2026-05-05.csv` | R8 verification |
| `BettingEngine/data/clv/afl/AFL_CLV_R09_2026-05-12.csv` | R9 verification |
| `BettingEngine/data/clv/afl/AFL_CLV_R12_2026-06-03_ml_comparison.csv` | R12 (confirmed closes) |

### xlsx column structure (confirmed)
- Col 18: Home H2H Close, Col 22: Away H2H Close
- Col 26: Home Line Close, Col 30: Away Line Close
- Col 34: Home Line Odds Close, Col 38: Away Line Odds Close
- Col 42: Total Close, Col 46: Over Odds Close, Col 50: Under Odds Close

### Closing price assignment rules applied

- **H2H bets:** used H2H close directly (home or away as applicable)
- **Handicap/total bets where line matches:** used closing odds directly
- **Handicap/total bets where line moved ≤4pts:** used closing odds as approximation
- **Bets where line moved ≥5pts:** `null` (misleading CLV, not comparable)
- **Alt lines far from standard (8-11pts):** `null`
- **Live bets / 2nd half markets:** `null`

### Bets left as null (19 total)

| ids | Reason |
|-----|--------|
| 6, 7 | Alt line (168.5 vs standard 189.5) / live bet |
| 8, 9, 10, 12 | Alt lines (150-160 vs standard 173-191) / unknown market |
| 26 | Line gap 6pts (Adelaide -18.5 vs close -12.5) |
| 29 | Line gap 5pts (Hawthorn -15.5 vs close -10.5) |
| 30 | Line gap 9pts (Adelaide +19.5 vs close +10.5) |
| 31 | Line gap 11pts (Under 176.5 vs close 165.5) |
| 40, 41 | Line gap 8pts (Hawthorn -20.5 vs close -12.5) |
| 47 | Line gap 5pts (Under 173.5 vs close 168.5) |
| 50-56 | R14 — xlsx not yet updated (next download Tue Jun 17) |

---

## Notable CLV findings (quick scan)

- **id:5** (Port Adelaide Win @ 3.00 → close 7.00): -57% CLV but WON. Port was early market 3.00, drifted to 7.00 by game time.
- **id:1** (Collingwood @ 2.12 → close 1.60): +32.5% CLV but LOST. Got great price on early Collingwood, market tightened, Carlton won.
- **id:37** (Essendon cash-out @ 2.31 → close 2.80): -17.5% CLV but WIN. Smart exit — paid up for Essendon early, market drifted further out.
- **id:21** (Under 181.5 @ 1.86 → close 2.00): -7% CLV, WON. Took under at tight price, market pushed it higher.
- **id:28** (Adelaide @ 2.88 → close 2.45): +17.4% CLV but LOST.

---

## R14 closing prices (TODO — Tuesday 17 Jun)

After Tuesday's AFL history xlsx download (`BetMate AFL History Push` task runs at 12:00), run this to get R14 closes:

```python
# In Python, read latest.xlsx, filter for 2026-06-11/13/14 games:
# Western Bulldogs vs Adelaide Crows (Jun 11): Adelaide H2H close
# Melbourne Demons vs Essendon (Jun 13): Under 162.5 close
# St Kilda vs GWS Giants (Jun 14): GWS H2H close + Under 185.5 close
```

Then update ids 50-56 in `AFL_MODEL_BETS`.

---

## Previous session context (also in this conversation)

- Added missing Essendon cash-out bet (id:37, May 31, +0.40u) that existed in `actual_bets_2026.csv` but was missing from AFL_MODEL_BETS
- Re-numbered ids 37-56, corrected all running totals (+0.40u delta)
- Final confirmed running total: +0.98u (56 bets, 26W/30L, 46.4%)

---

## Files changed

- `lib/researchData.ts` — AFL_MODEL_BETS closingPrice filled (37 bets), R14 comments added
- `CLAUDE.md` — Current State updated
