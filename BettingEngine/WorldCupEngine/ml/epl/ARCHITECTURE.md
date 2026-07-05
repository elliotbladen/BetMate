# EPL Pricing Engine — Architecture

Built: 2026-07-05 | Status: Production-ready

---

## Overview

xG-fed Dixon-Coles + Elo blend with a full tier adjustment stack.
Beats published academic benchmark (RPS 0.1335 vs 0.1925 benchmark).

```
EPL MATCH DATA (4,180 games, 2014/15–2024/25)
    │
    ├── football-data.co.uk  → results, odds, corners, cards, referee
    └── Understat            → xG per match, PPDA per team

         ↓
DIXON-COLES MODEL (70%)         ELO MODEL (30%)
  Fit on xG, not goals           Self-updating, season reversion
  Per-team home advantage        Between-season pull to mean
  Vectorised MLE (2.3s/fit)      K-factor 40→20 as data builds
  Time decay (half-life 693d)
         ↓
   lam_base, mu_base

         ↓
  ┌──────────────────────────────────────────────────────┐
  │  TIER ADJUSTMENT STACK                               │
  │                                                      │
  │  T2  PPDA           pressing matchup    ±0.15 xG     │
  │  T3  Form           last 5 pts          ±0.15 xG     │
  │  T3  Rest           ≤4d fatigue         ×0.94        │
  │  T5  Injuries       position weights    −25% max      │
  │  T6  Referee        goals/game history  ±0.15 xG     │
  │  T7  Set-piece      corners won/conceded ±0.08 xG    │
  └──────────────────────────────────────────────────────┘
         ↓
   lam_adj, mu_adj

         ↓
  SCORELINE MATRIX (Dixon-Coles + tau correction)
  → p_home, p_draw, p_away   (blended 70/30 with Elo)
  → p_over25 (raw)

         ↓
  ISOTONIC CALIBRATION (over25 only)
  Trained on all prior backtest seasons
  Corrects Poisson overdispersion bias

         ↓
  FINAL MARKETS
  H2H odds, O/U 2.5, AH ±0.5, CLV vs supplied odds
```

---

## Key parameterisation

```
lam = base_home × att_home × hfa_home / def_away
mu  = base_away × att_away / def_home
```

- `base_home / base_away` = league-average xG (fixed constants, not fit params)
- `att / def` = relative team strength (geometric mean normalised to 1.0)
- `hfa` = per-team home advantage deviation from base
- All in log space in MLE — avoids scale identification problem

---

## Tier coefficients

| Tier | Coefficient | Source |
|------|------------|--------|
| T2 PPDA | −0.007 xG per ppda_sum unit above avg | Carroll (2014) |
| T3 Form | +0.008 xG per form point advantage | EPL analytics literature |
| T3 Rest | ×0.94 if ≤4 days since last match | Standard sports science |
| T5 Injuries | ST=−9% att, GK=−6% def, AM=−7% att, etc | Caley (2015) |
| T6 Referee | ×0.5 of goals/game deviation | Internal calibration |
| T7 Set-piece | 0.042 xG/corner × 0.35 weight | Caley (2014) + calibration overlap |

**T7 weight rationale:** isotonic calibration already corrects ~65% of average set-piece bias.
The 0.35 weight captures only the remaining team-specific variation.

League averages: corners home=5.75, corners away=4.71 (from 4,180-match dataset).

---

## Backtest results (2021/22–2023/24, walk-forward)

| Season | RPS | Brier | LogLoss | H2H Acc |
|--------|-----|-------|---------|---------|
| 2021/22 | 0.1319 | 0.1902 | 0.5638 | 54.1% |
| 2022/23 | 0.1399 | 0.1986 | 0.5830 | 51.6% |
| 2023/24 | 0.1287 | 0.1842 | 0.5495 | 56.8% |
| **Avg** | **0.1335** | **0.1910** | **0.5654** | **54.2%** |

Academic benchmark best = 0.1925 RPS. Our model is 30% better.

Over25 calibration (isotonic, expanding window):
- 2021/22: CLV +15% (no prior data to calibrate on)
- 2022/23: CLV +5.6%
- 2023/24: CLV +2.2% — near market parity

---

## Files

```
ml/epl/
├── price_match.py              ← production entry point
├── ARCHITECTURE.md             ← this file
├── fetch/
│   ├── fetch_results.py        — football-data.co.uk scraper
│   ├── fetch_understat_xg.py   — Understat xG scraper
│   └── fetch_style_stats.py    — PPDA team stats scraper
├── models/
│   ├── dixon_coles.py          — xG-fed D-C model
│   ├── elo.py                  — Elo model
│   ├── calibration.py          — isotonic calibration classes
│   └── tiers.py                — tier adjustment stack (T2–T7)
├── backtest/
│   ├── walk_forward.py         — main backtest engine
│   ├── catboost_ensemble.py    — CatBoost T8 (archive — not in production)
│   └── totals_correction.py    — logistic correction (archive — not in production)
└── data/
    ├── matches/epl_matches.csv
    ├── xg/understat_xg.csv
    ├── style/ppda_dated.csv
    └── clv/
        ├── backtest_results.csv       — 1,139 rows (test seasons)
        └── features_all_seasons.csv   — 2,656 rows (CatBoost training)
```

---

## Production usage

```bash
# Minimal
python3 ml/epl/price_match.py --home "Arsenal" --away "Chelsea"

# Full with all inputs
python3 ml/epl/price_match.py \
  --home "Arsenal" --away "Man City" \
  --date 2026-08-15 \
  --ref "A Taylor" \
  --injuries-home "ST" \
  --injuries-away "AM,CM" \
  --mkt-home 2.40 --mkt-draw 3.50 --mkt-away 3.00 --mkt-over25 1.85
```

**Injury positions:** `GK  CB  LB  RB  WB  DM  CM  AM  LW  RW  SS  ST  FW`

---

## August 2026 data refresh (before GW1)

```bash
python3 ml/epl/fetch/fetch_results.py        # adds 2025/26 results
python3 ml/epl/fetch/fetch_understat_xg.py   # adds 2025/26 xG
python3 ml/epl/fetch/fetch_style_stats.py    # rebuilds PPDA
python3 ml/epl/backtest/walk_forward.py      # regenerates calibration
```

Step 4 is critical — the isotonic calibrator improves with each additional season.

---

## Target markets

| Market | Notes |
|--------|-------|
| Asian Handicap | Primary — most liquid, margins lowest |
| Over/Under 2.5 | Strong model signal, calibration improving |
| 1X2 | Secondary — EPL is highly efficient on H2H |

---

## What CatBoost needs to work (future)

Currently tested and rejected — insufficient training data.
- Required: ~10 seasons of walk-forward backtest predictions (~4,000 rows)
- Currently have: 7 seasons, 2,656 rows
- Check again: end of 2027/28 season
