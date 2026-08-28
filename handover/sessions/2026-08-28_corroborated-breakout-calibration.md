# Handover — corroborated breakout calibration

Two further shadow families were completed after commit `b11d871`.

- V2.2 requires predeclared independent clock or energy corroboration.
- V2.3 fits a bounded partial fallback on 1,022 pre-2025 90-day examples.
- Natural Fling, Gringotts and Sheza Alibi are excluded from every fit.

V2.2 restores elite/cohort validity but leaves Natural Fling at 83.53 because
her stored clock and energy evidence do not cross the training thresholds.
V2.3 selects coefficient 0.35 and lifts her to 91.73 while improving the broad
90- and 365-day cohorts. It still fails Natural Fling, narrowly misses elite
Spearman (0.498 versus 0.50) and narrowly misses class-only at 180 days.

Do not tune the coefficient upward: Natural requires about 70% relief, while
the pre-2025 optimum is 35%. Do not rerun/promote Horse Ability on these figures.
Next work must improve independent achieved-run evidence rather than target the
named horse.

Canonical reports:

- `reports/v2_ratings/achieved_run_v2_2_corroborated.json`
- `reports/v2_ratings/achieved_run_v2_3_calibrated.json`
- `reports/v2_ratings/achieved_run_v2_2_v2_3_findings.md`
