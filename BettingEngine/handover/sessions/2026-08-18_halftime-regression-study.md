# 2026-08-18 — Halftime Regression to Market Study

## Question
"The market is the smartest bettor in the world. At halftime, how often does the final score get back to the market line? And when it doesn't, why?"

## Dataset
- NRL: 746 games (2022-2026) with HT scores, FT scores, Betfair pre-game + HT odds
- AFL: 875 games (2022-2026) same structure
- Source: `data/inplay/{sport}/halftime/processed/halftime_dataset.csv`

## Key Findings

### 1. H2 regresses toward the market ~60% of the time
- NRL: 61.3% | AFL: 59.5%
- Not enough edge to bet blindly — need second-level signals

### 2. Regression depends on HOW FAR off the market HT is
- NRL: HT 19+ pts off market → 76.3% regression (156 games)
- AFL: HT 37+ pts off market → 67.1% regression (368 games)
- When HT is close to market → coin flip (47-48%)

### 3. H2 scoring is roughly constant regardless of H1
- NRL: H2 averages ~23pts whether H1 was 10 or 36
- AFL: H2 averages ~83pts whether H1 was 50 or 120
- Small regression exists (~8pts NRL) but nowhere near enough to save the market line
- H1-H2 correlation: NRL -0.244 (moderate regression), AFL +0.111 (near zero)

### 4. Pre-game fav trailing at HT — comeback rates
- NRL trailing 1-6: 50% comeback | 7-12: 52.8% | 13+: 36.9%
- AFL trailing 1-12: 52.8% | 13-24: 36% | 25+: 17%

### 5. When market gets it wrong, it's visible at HT
- NRL: 64.6% of blowout-wrong games already visible at HT
- AFL: 85.6% already visible at HT
- Market mostly gets blindsided in H1, not H2

## The Edge Framework

The HT bookmaker adjusts the line (e.g. pre-game 46, HT line drops to ~36 when H1 is 10). No edge in just knowing H2 averages 27. Need SECOND-LEVEL signals.

### Expected vs Surprise H1 (from Betfair odds shift)
- **Expected low H1** (small Betfair shift): avg H2 = 25.2pts — cause persists
- **Surprise low H1** (big Betfair shift): avg H2 = 27.1pts — partial reversion
- Gap: ~2pts. Real but small.

### Best unders combo: Even match + expected low H1
- 32 games, avg H2 = 23.9, avg FT = 36.9, H2 ≤ 20 in 43.8%

### The real second-level factors (what the HT bookie can't fully price):
1. **Ref tendency** — whistle-heavy ref in H1 doesn't change at the break
2. **Weather at HT** — rain/wind is structural, not random
3. **In-game injuries** — spine player down = attack cooked for H2
4. **HT stats** — errors, completion rate, metres = process indicators

## Gap: Historical Combined Dataset
All four signals are scraped LIVE on gameday (`scripts/nrl_ht_live.py`, `scripts/afl_ht_live.py`). Missing: historical dataset linking ref + weather + HT stats to H2 outcomes for backtesting the combined trigger. Build when ready.

## Betting Rules (from this study)
1. Only bet HT totals when H1 is EXTREME (NRL ≤16 or ≥30)
2. Check Betfair odds shift: expected H1 = bet, surprise H1 = stay away
3. Stack with ref + weather + HT stats for edge over the HT bookmaker
4. AFL low-scoring H1 (≤55): UNDER hits 95.4% — near certainty (already in memory)
