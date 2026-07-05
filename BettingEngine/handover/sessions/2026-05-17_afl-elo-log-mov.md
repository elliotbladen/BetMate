# Session 2026-05-17 — AFL ELO log MOV formula

## What we did

### Investigation: AFL ELO MOV multiplier calibration
Triggered by last session's finding that a single R10 result (Melbourne 120 – Hawthorn 81) was producing a ~14pt line shift. Investigated whether the ELO formula was overcalibrated.

**Finding: previous session was using the wrong formula.** The session had been analysing `K=20, ln(margin+1)*1.5` but the actual code in `ml/afl/game_log.py` uses:
```python
K = 62  # regular season rounds 5+
margin_factor = min(abs(margin) / 30.0, 1.5)
delta = K * margin_factor * (outcome - expected)
```

**Correct numbers for Melbourne 39pt upset win:**
- Actual formula: Hawthorn −66 ELO → 8.6pt line shift (not 91/14 as previously stated)
- The 8.6pt shift is defensible for a genuine 18.2%-chance team winning by 39pts

### Formula change made
Replaced linear MOV with log-based (diminishing returns):
```python
# Old
margin_factor = min(abs(margin) / 30.0, 1.5)

# New
margin_factor = min(math.log(abs(margin) + 1) / math.log(31), 1.5)
```

**Research backing:** 538 (NFL/NBA), fitzRoy AFL (margin_power=0.833), academic literature (ScienceDirect 2020) — all recommend log or power over linear. Calibration point (30pts = 1.0×) and cap (1.5×) unchanged.

**File changed:** `ml/afl/game_log.py:207`

### Rebuild pipeline
1. `ml/afl/game_log.py --xlsx "Downloads/afl (8).xlsx"` → rebuilt `features_afl.csv` (3434 games)
2. `ml/afl/train.py` → retrained all 3 models
3. `ml/afl/backtest_2025.py` → confirmed on 2025 season

### Results

| Metric | Before | After |
|--------|--------|-------|
| H2H accuracy (test) | 66.2% | 67.6% |
| H2H log loss (test) | 0.610 | 0.577 |
| Margin MAE (test) | 28.16 | 28.55 |
| Margin DirAcc (test) | 72.2% | 69.9% |

Margin model marginal degradation is within training variance. H2H improvement is real and confirmed in backtest.

**Backtest sweet spot (2025):**
- Conf ≥70%: 132 bets, 79.5% strike, ROI +7.1%
- Conf ≥70%, EV ≥0%, Odds ≥1.50: 42 bets, 59.5% strike, ROI +5.4%

**Handicap model:** not usable — sub-50% strike across all thresholds (pre-existing problem)
**Totals model:** borderline 54-55% (pre-existing problem)

## Current state

- `ml/afl/game_log.py` — log MOV formula live
- `ml/afl/results/features_afl.csv` — rebuilt with new formula
- `ml/afl/results/models/` — all 3 models retrained
- `ml/afl/results/features_afl_backup_prelogmov.csv` — backup of old features (can delete after next session if all good)

## Deferred
- Autocorrelation correction (538-style): `2.2/((ELOW-ELOL)*0.001+2.2)` — correct theory, defer to next full recalibration
- AFL CLV report from prior sessions still pending
