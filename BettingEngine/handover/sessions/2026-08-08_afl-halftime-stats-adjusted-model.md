# 2026-08-08 — AFL Halftime Stats-Adjusted Model (v2)

## What Happened

Built a research-backed stats-adjusted regression model into `scripts/halfTime_price_afl.py` during a live Fremantle vs Melbourne R22 halftime pricing session.

### The Problem (v1)

The v1 halftime model used a fixed Bayesian regression factor (0.45) that blended the HT margin with the pre-game prior. Live stats (I50s, clearances, clangers) were bolted on as a small additive adjustment capped at ±6 points. This meant a team could dominate every stat and the model would barely notice — the pre-game prior dominated everything.

### The Fix (v2) — Stats-Adjusted Dynamic Regression

Added a "process stats vs outcome stats" framework backed by academic research:

**Research basis:**
- AFL: I50 differential R=0.71 with winning margin (strongest non-scoring stat). Turnovers "count for double" (Wheatley 2018). Clearances weakest big stat (~50% stoppage base rate). I50 + contested poss combined R²=0.552.
- NBA: Halftime stats predict winners at 84.1% accuracy (Adam et al, Springer 2024). Shooting accuracy H1→H2 correlation = -0.007 (zero persistence across 12,486 shots).
- AFL conversion: avg 51.4%, volume > accuracy for predicting wins (Wong, Medium).

**What persists (process stats → structural, skill-based):**
- Inside 50 differential
- Clanger/turnover differential
- Clearance differential

**What regresses (outcome stats → luck/variance):**
- Goal accuracy (near-zero correlation between halves)
- I50 conversion rate
- Scoring efficiency per entry

**How it works:**

1. Calculate `stats_implied_margin` from process stats:
   ```
   stats_margin = (I50_diff × 1.4) + (clanger_diff × -1.0) + (clearance_diff × 0.5)
   ```

2. Compare stats direction vs pre-game prior direction:
   - Stats back the prior → RAISE regression factor (trust pre-game more)
   - Stats oppose the prior → LOWER regression factor (trust live evidence more)

3. Scale adjustment by signal strength (capped at ±0.10):
   ```
   signal_strength = min(|stats_implied_margin| / 15.0, 1.0)
   adj = ±0.10 × signal_strength
   regression = clamp(0.45 + adj, 0.20, 0.65)
   ```

### Weight Derivations

| Weight | Value | Source |
|--------|-------|--------|
| `STATS_IMPLIED_I50_WEIGHT` | 1.4 | AFL I50 R=0.71 — highest non-scoring correlation |
| `STATS_IMPLIED_CLANGER_WEIGHT` | -1.0 | Turnovers "count for double" (lost + gained possession) |
| `STATS_IMPLIED_CLEARANCE_WEIGHT` | 0.5 | Weakest big stat — ~50% base rate from stoppages |
| `REGRESSION_ADJUSTMENT_MAX` | 0.07 | Research-calibrated 7% — xG convergence maps to ~8%, MoS natural drift = 29% of quarter variation, NBA close-game evidence supports upper half. Upgrade to 0.08-0.10 after 50+ live observations validate weights. |

### Live Test — Fremantle vs Melbourne R22

**Actual HT: Melbourne 10.5 (65) – Fremantle 11.2 (68)**

| Metric | v1 (fixed regression) | v2 (stats-adjusted) |
|--------|:---------------------:|:-------------------:|
| Regression factor | 0.45 | 0.36 |
| Stats-implied margin | n/a | Melbourne +14.0 |
| Expected final margin | ~-14.0 | -13.5 |
| Melbourne win prob | ~17% | 17.7% |
| Fremantle win prob | ~80% | 79.8% |
| Fremantle fair odds | ~$1.25 | $1.25 |

In this game the adjustment was modest because Melbourne's I50 dominance (35-25) was partially offset by Fremantle winning clearances (24-22) and clangers nearly equal (29-28). The stats oppose the pre-game prior (Freo -14.5) so regression dropped from 0.45 to 0.36 — trusting the live evidence more. But since Freo is also leading the actual score AND matches the prior, the final price barely moved.

The model would show bigger shifts in games where stats and score are heavily misaligned (e.g., a team dominates stats but trails by 4+ goals due to accuracy luck).

### Files Changed
- `scripts/halfTime_price_afl.py` — added stats-implied margin calculation, dynamic regression factor, new dataclass fields, updated print output

### Halftime Matrix Analysis (also this session)
Read the AFL HT H2H matrix (`outputs/afl_ht_h2h_matrix.xlsx`) for Melbourne and Fremantle. Key signals:
- Melbourne vs Fremantle H2H: 16.7% win rate (1/6), -66.5% opposing
- Fremantle vs Melbourne H2H: 83.3% (5/6), +33.3% backing
- Melbourne in August: 33.3% win rate, -29% opposing
- Fremantle away & trailing at HT: 39.1% actual vs 32.1% implied, +21.8% backing

### Future Calibration
- These weights are research-derived, not regression-fitted to our dataset
- Once 50+ live halftime observations are accumulated, run a proper regression on {I50_diff, clanger_diff, clearance_diff} vs H2 margin to calibrate the weights
- The ±0.10 regression adjustment cap is conservative by design — can expand to ±0.15 if evidence supports it
- Consider adding contested possessions as a 4th process stat (R=0.58 with margin, currently not scraped at halftime)

### Sources
- [AFL Stats vs Winning Margin](https://perkot.github.io/afl-stats/) — I50 R=0.71, contested poss R=0.58
- [Which AFL Stats Matter Most (Wheatley 2018)](http://troywheatley.blogspot.com/2018/10/afl-statistics-series-1-which.html) — turnovers count double, clearances weakest
- [AFL Conversion Rates (Wong)](https://denisewong1.medium.com/a-closer-look-at-afl-stats-conversion-rates-d2b393eb3b0c) — 51.4% avg, volume > accuracy
- [NBA HT Prediction (Adam et al, Springer 2024)](https://link.springer.com/article/10.1007/s44163-024-00201-9) — 84.1% accuracy from HT stats
- [AFL Performance Indicators (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S1440244018303141) — 95.1% win/loss accuracy, RMSE 6.8 pts
- [AFL Inside 50 Causal Effect (ResearchGate)](https://www.researchgate.net/publication/380734913_ESTIMATING_THE_CAUSAL_EFFECT_OF_DIFFERENT_INSIDE_50_DECISIONS_ON_SCORING_IN_AUSTRALIAN_FOOTBALL)
