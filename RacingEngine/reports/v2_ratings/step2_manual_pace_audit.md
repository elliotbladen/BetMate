# Step 2 manual pace audit

Date: 2026-08-23
Candidate: `pace-shape-v2.1-pit-shadow`

## Audit method

The audit checked official runner identity, complete phase coverage, prior-only par sample, phase-score direction, runner positions and adjustment sign. It did not substitute visual opinion for missing data. Extreme examples remain research flags until replay review is recorded runner by runner.

## Representative shapes

- Sprint home: Flemington R1, 18 January 2025 (`early -3.42`, `middle -4.00`, `late +4.00`, confidence `0.95`). The direction is internally coherent: a crawl followed by an extreme finish.
- Sprint home: Flemington R4, 19 July 2025 (`-4.00`, `-0.37`, `+3.08`, `0.95`). Passed the numeric shape check.
- Pace collapse: Randwick R3, 11 April 2026 (`+2.08`, `-4.00`, `-3.22`, `0.95`). The discontinuous middle score makes this a replay/manual-review flag, not automatic promotion evidence.
- Pace collapse: Flemington R1, 1 November 2025 (`+2.31`, `+1.04`, `-2.93`, `0.95`). Passed the numeric shape check.
- Slow/crawl warning: several 4 April 2026 Randwick races were extremely slow in every phase against the soft-track bucket. That clustering is evidence the going/meeting-speed control is too coarse; these are not safe standalone pace interpretations.

## Cox Plate 2024

The corrected point-in-time treatment calls the Cox Plate `very_fast_early`: early `+1.49`, middle `+1.69`, late `-0.64`, confidence `0.94`, based on 18 strictly earlier comparable races. Pride Of Jenni absorbed the largest pressure and receives `+1.97`; Via Sistina receives `-0.38`, because she was helped by position relative to the shape while still producing the best late relative split. This is directionally credible, but the winner must not be downgraded as an achievement rating merely because the race shape helped her. The pace number is therefore a run-context annotation, not an accepted performance penalty.

## Named missing races

- 2025 Everest: zero matched official sectional rows. Status: permanent source gap in the present snapshot; no imputation.
- 2026 Doncaster winner Sheza Alibi: official result identity is runner 15, but runner 15 is absent from the stored official sectional PDF. Status: permanent runner gap in the present snapshot; no imputation.

## Decision

Do not promote. The next-start response is encouraging, but the chronological prediction improvement is negligible and reverses sign by jurisdiction. Meeting-speed/going controls and adjustment semantics require another frozen experiment.
