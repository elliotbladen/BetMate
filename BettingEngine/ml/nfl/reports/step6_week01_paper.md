# NFL Step 6 — 2026 Week 1 paper launch

## Outcome

The live paper workflow is operational. Sixteen Week 1 predictions were frozen
on 31 August 2026 Brisbane time before the local market-reference capture. The
model used fixed Step 5 ridge settings refitted through completed 2025 games;
hyperparameters were not changed after viewing the vault. Staking remains off.

The 2026 preseason state was reconstructed from all completed play-by-play
through 2025, then regressed by the frozen 0.35 offseason-retention factor. The
2025/2026 kickoff, overtime and onside-kick rule flags are active. No 2026 score,
market line or result entered the prediction file.

## Market status

The nflverse schedule contains spread and total fields, but it does not identify
the bookmaker or original quote timestamp. Those values were captured only
after the prediction was sealed and are archived as a reference. They contribute
zero qualifying obtainable quotes and cannot establish opener beat rate, CLV or
ROI.

QB names are also unresolved in the current schedule feed. Under T0 data-health
rules, every Week 1 row is therefore a baseline paper prediction, not an
authorised selection.

## Largest reference disagreements

| Match | Ridge fair home spread | Schedule reference | Model direction | Difference |
|---|---:|---:|---|---:|
| Arizona at LA Chargers | LAC -3.71 | LAC -10.5 | Arizona | 6.79 |
| New Orleans at Detroit | DET -2.08 | DET -7.0 | New Orleans | 4.92 |
| Baltimore at Indianapolis | IND -1.00 | IND +3.5 | Indianapolis | 4.50 |
| Miami at Las Vegas | LV +0.92 | LV -3.5 | Miami | 4.42 |
| Denver at Kansas City | KC +1.23 | KC -3.0 | Denver | 4.23 |

These are diagnostic disagreements only. Week 1 preseason priors are heavily
regressed and presently lack confirmed starters, injuries and valid bookmaker
quotes. Large differences should trigger investigation, not confidence.

The largest totals differences were NY Jets–Tennessee over by 5.62 model points,
Atlanta–Pittsburgh over by 4.14, Tampa Bay–Cincinnati under by 3.96, and
Cleveland–Jacksonville over by 3.86. These are also non-actionable references.

## Frozen artefacts

- `data/nfl/features/2026_week1_preseason_team_state.parquet`
- `data/nfl/predictions/2026_week01_paper_frozen.csv`
- `ml/nfl/reports/step6_week01_prediction_manifest.json`
- `data/nfl/markets/2026_week01_schedule_reference.csv`
- `ml/nfl/reports/step6_week01_market_manifest.json`

## Operating rule for the next capture

A qualifying quote must record game ID, bookmaker, captured UTC timestamp,
home-team spread, total, decimal prices and source. It must be archived without
altering the frozen prediction. Later scoring uses the archived quote available
at the declared decision time and the final captured close. Retrospective line
substitution is forbidden.

Step 6 is complete as a paper launch. It is not a betting launch.

