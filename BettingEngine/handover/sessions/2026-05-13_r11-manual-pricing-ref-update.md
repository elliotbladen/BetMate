# Session 2026-05-13 - R11 Manual Pricing, Ref Update, Matrix Review

## What happened

The scheduled `BettingEngine NRL Pricing` task did not fire on Tuesday 2026-05-12 at 19:03.

Evidence:
- Task Scheduler last run remained `2026-05-05 07:43:10`
- `results/r11_pricing_2026.csv` was still timestamped `2026-05-07`
- Windows power logs showed the machine asleep across the 19:03 trigger window
- Task history is disabled, so no detailed Task Scheduler operational events were available

## Manual R11 pricing run

Ran R11 pricing manually with:
- R10 results confirmed in DB
- R11 injuries from BetMate `round-11-injuries.json`
- R11 referees from BetMate `latest-referees.csv`
- Live Open-Meteo weather enabled

Exported:
- `results/r11_pricing_2026.csv`

Latest export timestamp after this session:
- `2026-05-13 06:41:06`

## R11 referee update

Searched NRL.com match centres for the two missing R11 referees.

Confirmed:
- South Sydney Rabbitohs vs Dolphins: `Adam Gee`

Still not published on NRL.com:
- Penrith Panthers vs St. George Illawarra Dragons

NRL.com Panthers/Dragons match centre listed:
- Liam Kennedy - Touch Judge
- Belinda Sharpe - Touch Judge
- Grant Atkins - Senior Review Official

It did not list a field referee, so Panthers/Dragons remains T6 neutral.

Updated:
- `data/import/referees_r11.csv`
- BetMate local referee CSVs were also updated in the local BetMate working tree, but that repo was already heavily dirty with unrelated mass deletions, so do not commit it blindly.

## ML shadow comparison

Generated:
- `results/r11_ml_shadow_2026.txt`

Biggest ML vs rules differences:
- Roosters vs Cowboys: ML much lower on Roosters and total
- Sharks vs Bulldogs: ML less bullish Sharks
- Warriors vs Broncos: ML less bullish Warriors
- Panthers vs Dragons: same side, ML less extreme

ML totals were materially lower than rules on most games.

## Matrix review

Reviewed NRL H2H, handicap, and totals matrices against actual R11 local kickoff times.

Date/time handling:
- Pricing CSV kickoffs are UTC
- Converted to AEST for matrix filters
- New moon: `2026-05-16 20:00 UTC`, so the matrix `New Moon (+/-1 day)` window covers the R11 Magic Round dates
- Saturday night by matrix rule means local kickoff >= 18:00 on Saturday

Notable matrix reads:
- Eels vs Storm: strongest Saturday night Eels fade / Storm lean
- Warriors vs Broncos: cleanest new-moon side/handicap confluence toward Warriors
- Sharks vs Bulldogs: best new-moon totals under confluence
- Souths vs Dolphins: cleanest 10-20% side cluster fading Souths / leaning Dolphins

## Known issues / follow-up

- Matrix regeneration still fails because `.venv` is missing `ephem`
- `scripts/price_from_betmate.py` failed because `betmate_import_runs` table is missing; migration/preflight schema needs repair before using that wrapper
- Task Scheduler history is disabled; enable it for future debugging
- `BettingEngine NRL Pricing` task is `Interactive` logon type and missed the run while the machine was asleep despite `StartWhenAvailable`
- Panthers/Dragons referee still needs confirmation before final reprice
