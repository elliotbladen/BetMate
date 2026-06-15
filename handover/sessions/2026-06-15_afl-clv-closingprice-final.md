# Session: AFL CLV — closingPrice final backfill (ids 6-9, 12, 52)
**Date:** 2026-06-15  
**Commit:** `9b822cf`

---

## What was done

Final batch: filled `closingPrice` (and `predictedLine` where missing) for the last 6 previously-null AFL_MODEL_BETS entries.

### Changes applied

| id | Match | Market | predictedLine | closingPrice | Source |
|----|-------|--------|--------------|--------------|--------|
| 6  | Brisbane vs Melbourne | Over 168.5 | 189.5 (market total open) | 1.80 (Over 189.5 close) | xlsx R6 |
| 7  | Brisbane vs Melbourne | Brisbane Win (Live) | 1.37 (Brisbane H2H open) | 1.25 (Brisbane H2H close) | xlsx R6 |
| 8  | Fremantle vs Carlton | Under 159.5 | 145.6 (already set) | 1.90 (Under 173.5 standard close) | xlsx R7 |
| 9  | Eagles vs Saints | Over 153.5 | 168.1 (already set) | 1.95 (Over 191.5 standard close) | xlsx R7 |
| 12 | Adelaide vs Port Adelaide | Under 149.5 | 168 (already set) | 1.90 (Under 175.5 standard close) | xlsx R8 |
| 52 | Melbourne Demons vs Essendon Bombers | Under 162.5 | 169.9 (already set) | 1.91 (standard-line approx) | web research |
| 53 | Melbourne Demons vs Essendon Bombers | Over 79.5 2nd Half | null | null | No historical 2nd-half market data available |

### Notes on alt-line CLV approximations

For ids 6, 8, 9, 12, 52 — the bet was placed on an alt line significantly different from the standard closing line. The closing price used is for the **standard market** not the actual alt line. CLV figures for these should be read as rough directional indicators only:

- id:6: Over 168.5 vs standard close 189.5 (21pt gap). Using Over 189.5 close odds 1.80 — understates true CLV since 168.5 would have closed at higher odds.
- id:8: Under 159.5 vs standard close 173.5 (14pt gap). Using Under 173.5 close 1.90 — understates true CLV.
- id:9: Over 153.5 vs standard close 191.5 (38pt gap). Using Over 191.5 close 1.95 — very different line; CLV is indicative only.
- id:12: Under 149.5 vs standard close 175.5 (26pt gap). Same caveat.
- id:52: Under 162.5 vs standard close ~175.5 (13pt gap). Using ~1.91 as approximation.

### Melbourne vs Essendon R14 result (verified via web)
Final: Melbourne 95 – Essendon 50 (total = 145)
Halftime: Melbourne 64 – Essendon 23 (total = 87)
2nd half: Melbourne 31 – Essendon 27 (total = 58)
- id:52 Under 162.5 → WON (145 < 162.5) ✓ (already marked)
- id:53 Over 79.5 2nd Half → LOST (58 < 79.5) ✓ (already marked)

---

## State after this session

AFL_MODEL_BETS closingPrice population:
- **Filled: ~49/56** 
- **Still null (7):** id:21-26 (R10 — no predictedLine; closingPrice filled separately but alt-line note applies), id:53 (2nd half market, no data)

R10 (ids 21-26) closingPrice were already filled in a previous session. predictedLine for those 6 remains null (no R10 AFL pricing file found).

---

## Files changed

- `lib/researchData.ts` — closingPrice filled for ids 6, 7, 8, 9, 12, 52; predictedLine filled for ids 6, 7
