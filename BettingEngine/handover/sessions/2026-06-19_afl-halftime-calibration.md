# Session 2026-06-19: AFL Halftime Model Calibration

## What Was Completed

### AFL Halftime Pipeline — Extended from Prior Session (2026-06-14)

This session continued work from the 2026-06-14 build. All 5 scripts from that session are live.
This session focused on calibrating the AFL halftime model constants against the 875-game dataset.

### Model Calibration — `scripts/halfTime_price_afl.py`

**Run against `data/inplay/afl/halftime/processed/halftime_dataset.csv` (875 valid games)**

#### BASELINE_ACCURACY
- Updated: `0.52` → **`0.529`**
- Per-year breakdown:
  - 2022: 0.534 (n=190)
  - 2023: 0.523 (n=193)
  - 2024: 0.532 (n=203)
  - 2025: 0.528 (n=193)
  - 2026: 0.531 (n=96, mid-season)
- Method: goals / (goals + behinds) across all H1 shots in dataset

#### H2 Total Lookup Table (SECOND_HALF_BY_FIRST)
Table was already well-calibrated. Actual data confirmed:

| H1 Band  | n   | Actual avg H2 | Table value | Delta |
|----------|-----|---------------|-------------|-------|
| <60      | 104 | 82.1          | 82.0        | +0.1  |
| 61-75    | 206 | 83.3          | 83.0        | +0.3  |
| 76-88    | 244 | 84.6          | 85.0        | -0.4  |
| 89-100   | 173 | 86.0          | 86.0        | 0.0   |
| 101+     | 148 | 88.5          | 89.0        | -0.5  |

No changes made — all values within 0.5 pts of actual.

#### Accuracy Trend Weight
- ACCURACY_TREND_WEIGHT=1.0 **retained** per user preference
- Calibration finding: accuracy trend (H1 acc diff) has **near-zero predictive power** for H2 margin
  - Regression coefficient on acc_diff: -11.2 (implies slight regression to mean)
  - Correlation(acc_adj, h2_margin) = -0.04 across all weight values
- Interpretation: historically, H1 kicking accuracy doesn't carry well into H2 at the population level
- User stance: "if they are kicking bad or good, i actually want that trend to continue"
- Resolution: retained at 1.0; noted in comments as a situational/qualitative lens rather than a strong edge

#### Live Stats Weights (I50, Clearances, Clangers)
- **Cannot calibrate from historical dataset** — the 875-game dataset does not contain per-quarter team stats (inside 50s, clearances, clangers)
- Weights remain research-estimated: PTS_PER_I50_DIFF=0.4, PTS_PER_CLEARANCE_DIFF=0.3, PTS_PER_CLANGER_DIFF=0.5, STATS_ADJ_CAP=6.0
- These come from FootyWire live scraping (afl_ht_live.py → enrich_with_live_stats) and are only available during live games
- **To do:** re-calibrate once 50+ live-scraped halftime observations are accumulated (start of 2027 season at earliest)

### Prior Session Work (2026-06-14) — Confirmed Stable

All code changes from 2026-06-14 session are working:
- NRL restart calc: `(home-away) * 0.72 * 0.36` (0.26 pts per restart diff — conservative, research-backed)
- NRL conversion cap: `max(-2.0, min(2.0, conversion_adj))`
- NRL error regression: `error_diff * 1.4 * 0.45 = 0.63 pts/error`
- AFL live scraper (afl_ht_live.py): Squiggle API + FootyWire enrichment
- AFL pregame source: betmate.au/api/afl-predictions (primary) → local CSV (fallback)
- AFL accuracy adjustment: trend continuation (not regression to mean) — user preference

## Files Changed This Session
- `scripts/halfTime_price_afl.py` — BASELINE_ACCURACY 0.52→0.529, calibration comments added to all constant blocks

## Calibration Data Reference
```
Accuracy regression (875 games):
  ht_score_diff coefficient: 0.187 (H1 margin explains ~19% of H2 margin)
  acc_diff coefficient:      -11.2  (near-zero, slightly negative)
  corr(acc_adj, h2_margin):  -0.04  (all weights)

H2 total regression:
  All bands calibrated within 0.5 pts of actual averages
  Avg H1 shots per team: 11.7 (not 25 — confirmed model uses actual shot counts)
```

## Next Session
- NRL R15 results — load when available; re-run CLV if R14 historical data is on aussportsbetting
- AFL R14 CLV — check if historical data available yet (usually 3-7 day lag)
- AFL R15 pricing — run prepare_round.py after Tuesday pipeline completes
- Accumulate live halftime stat observations (I50/clearances/clangers) from live games — target 50 to calibrate weights
- Consider building a simple log of live-scraped halftime stats to enable future calibration
