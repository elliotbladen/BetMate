# Handover: controlled V2 ratings rebuild

Date: 23 August 2026

## Outcome

Steps 1–8 are complete and the racing sanity gate passes. Step 9 was then run.
The elite run-rating foundation is credible, but the naive V2 current-state
predictor failed and is frozen. Do not promote V2 to pricing yet.

## Implemented

- `racing_engine/rnsw.py`: structured Racing.com card owns NSW results;
  `--results-only` backfill; PDFs may only enrich matching official numbers.
- `racing_engine/racing_com.py`: added `the valley` to metro discovery.
- `racing_engine/v2_ratings.py`: versioned clean tables, clock quarantine,
  official audit loader, IFHA distance margin scale, form-first Race Strength,
  elite leaderboard, same-season audit gate, chronological prediction test.
- `data/reference/australian_classifications_2024_25_elite.csv`: 25 official
  Racing Australia audit records.
- `tests/test_v2_ratings.py`: source ownership, clock, IFHA scale and form/margin
  tests.

## Reproducible command

`.venv/bin/python -m racing_engine.v2_ratings --as-of 2026-08-16`

Report: `reports/v2_ratings/v2_rebuild_report.json`.

## Key evidence

- Clean: 2,720 races; 36,712 runners; 28,939 rated performances.
- Quarantine: 1,394 records; impossible clocks never set a V2 race level.
- Official 2024/25 audit: 24 matches; Spearman 0.6858.
- Top performance: Via Sistina, Cox Plate, 127.43 (official 127).
- Expected checks: Sir Delius 122.27, Mr Brightside 119.48, Autumn Glow 118.45.
- Prediction test (577 common 2025/26 races): uniform 2.3210 log loss, V1
  2.3356, V2 2.4537. V2 median-last-three state is rejected/frozen.

## Next experiment

Build `horse-ability-v2.1` without changing the accepted V2 run ratings. Test
robust best-sustainable form versus median/recency alternatives; add layoff and
campaign state, distance/going suitability and explicit uncertainty one family
at a time. Fit/calibrate on training only. Compare on identical races to V1,
uniform, and this failed V2 state. Market tests wait for timestamped 2025/26
opening and closing prices.
