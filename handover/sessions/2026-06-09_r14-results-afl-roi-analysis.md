# Session: NRL R14 + AFL R13 Results + AFL ROI Analysis
**Date:** 2026-06-09

## What we did

### 1. Updated research page with week's results (NRL R14 + AFL R13)

Added Section 7 to `lib/researchData.ts` — 18 bets total across the week:

| ID | Date | Match | Market | Odds | Stake | Result |
|----|------|-------|--------|------|-------|--------|
| 386 | Fri 5 Jun | Storm v Newcastle | Newcastle +4.5 | 1.85 | $25 | W |
| 387 | Fri 5 Jun | Hawthorn v Bulldogs | Hawthorn -11.5 | 1.90 | $25 | L |
| 388 | Fri 5 Jun | Hawthorn v Bulldogs | Hawthorn -20.5 | 1.91 | $20 | L |
| 389 | Fri 5 Jun | Hawthorn v Bulldogs | Hawthorn -20.5 | 1.91 | $25 | L |
| 390 | Sat 6 Jun | Gold Coast v Brisbane | Under 188.5 | 1.88 | $25 | W |
| 391 | Sat 6 Jun | Cowboys v Dolphins | Cowboys Win | 2.38 | $20 | L |
| 392 | Sat 6 Jun | WCE v Port Adelaide | Port -6.5 | 1.88 | $30 | L |
| 393 | Sat 6 Jun | WCE v Port Adelaide | Port -7.5 | 1.90 | $25 | L |
| 394 | Sat 6 Jun | Broncos v Titans | Under 50.5 | 1.90 | $25 | L |
| 395 | Sun 7 Jun | Tigers v Panthers | Under 49.5 | 1.91 | $25 | L |
| 396 | Sun 7 Jun | Sydney v St Kilda | Sydney -29.5 | 1.89 | $25 | L |
| 397 | Sun 7 Jun | Cronulla v St George | Cronulla -10.5 | 1.91 | $20 | W |
| 398 | Sun 7 Jun | Essendon v Carlton | Under 168.5 | 1.89 | $25 | W |
| 399 | Sun 7 Jun | Essendon v Carlton | Under 173.5 | 1.88 | $25 | W |
| 400 | Mon 8 Jun | Collingwood v Melbourne | Collingwood Win | 1.90 | $20 | L |
| 401 | Mon 8 Jun | Collingwood v Melbourne | Collingwood Win | 1.90 | $25 | L |
| 402 | Mon 8 Jun | Canterbury v Parramatta | Bulldogs -5.5 | 1.88 | $25 | L |
| 403 | Mon 8 Jun | Canterbury v Parramatta | Bulldogs -6.5 | 1.97 | $20 | L |

**Week net: cumPL 27.00 → 22.92 (−4.08u)**

Also added 7 NRL R14 entries to MODEL_BETS (ids 42–48):
- Newcastle +4.5 W (+0.85u) → running 4.00
- Cowboys H2H L → running 3.00
- Broncos/Titans Under L → running 2.00
- Tigers/Panthers Under L → running 1.00
- Cronulla -10.5 W (+0.91u) → running 1.91
- Canterbury -5.5 L → running 0.91
- Canterbury -6.5 L → **running −0.09** (model dipped negative this week)

### 2. AFL ROI analysis for 2026 (tracked stakes only)

**By market type:**

| Market | W | L | Win% | Staked | Net | ROI |
|--------|---|---|------|--------|-----|-----|
| Totals | 8 | 1 | 88.9% | $300 | **+$216.00** | **+72.0%** |
| Lines | 6 | 11 | 35.3% | $575 | −$148.50 | −25.8% |
| H2H | 2 | 8 | 20.0% | $323 | −$181.45 | **−56.2%** |
| **Total** | **16** | **20** | **44.4%** | **$1,198** | **−$113.95** | **−9.5%** |

**Key takeaway:** AFL totals/unders are the edge (+72% ROI, 8/9). AFL H2H is a disaster (2/10, −56%). Lines also negative (−26%). All losses driven by H2H and lines.

### 3. Closing lines — PENDING

User wants to pull closing lines tomorrow to run CLV analysis on the week's bets and determine whether results were bad luck or bad bets (i.e. did the market move against us or confirm our prices?).

Focus bets for CLV check:
- Hawthorn -11.5 / -20.5 (3 bets, all lost — did the market move toward or away from Hawthorn?)
- Port Adelaide -6.5 / -7.5 (both lost)
- Canterbury -5.5 / -6.5 (both lost)
- Sydney -29.5 (lost)
- Collingwood H2H x2 (both lost — Melbourne won by a lot or a little?)

## Files changed
- `lib/researchData.ts` — Section 7 added (ids 386–403 LEGACY_BETS), R14 added (ids 42–48 MODEL_BETS)

## Next session
1. Pull closing lines for NRL R14 + AFL R13 bets
2. Run CLV analysis — were we unlucky or backing bad prices?
3. Update `closingPrice` fields in MODEL_BETS once closing lines available
