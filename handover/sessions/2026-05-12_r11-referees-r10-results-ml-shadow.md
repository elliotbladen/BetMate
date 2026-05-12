# Session 2026-05-12 — R11 Referees, R10 Results Load, ML Shadow CLV Review

## What happened

### R10 Results — two loads required
The `r10_results_2026.csv` in BettingEngine was mislabeled — it contained May 1-3 (R9) results, not R10.
1. Loaded the mislabeled file → wrote R9 results to DB (match_ids 278-285, May 1-3 games). These may have already been in DB.
2. Ran `fetch_nrl_results.py --round 10` → fetched real R10 results (May 7-10) from NRL API, loaded 8 results (match_ids 294-301). This unblocked tonight's 19:03 pricing run.

### R11 Referees — 6/8 scraped manually
NRL.com team-lists article for R11 not yet published (scraper got 404s for all date variants).
Sourced 6/8 from Zero Tackle Magic Round article:
- Ashley Klein: Cronulla vs Canterbury
- Todd Smith: Wests Tigers vs Manly
- Adam Gee: Roosters vs Cowboys
- Wyatt Raymond: Eels vs Storm
- Gerard Sutton: Titans vs Knights
- Grant Atkins: Warriors vs Broncos

Missing (not announced at time of session):
- South Sydney Rabbitohs vs Dolphins
- Penrith Panthers vs St George Illawarra Dragons

Files written:
- `BetMate/data/nrl/referees/processed/latest-referees.csv` (6 rows)
- `BetMate/data/nrl/referees/processed/2026/round-11-referees.csv`
- `BetMate/data/nrl/referees/raw/2026/round-11.json`

### Referee Task Scheduler installed
Task: "BettingEngine NRL Referees Fetch"
Schedule: **Tuesday 14:00 + 17:00** (two triggers, weekly)
Wrapper: `scripts/run_nrl_referees.ps1`
Install: `scripts/install_nrl_referees_task.ps1`

The 17:00 trigger should catch any refs announced during the day.
If NRL.com publishes the team-lists article before 19:03, scraper will auto-update latest-referees.csv.
Re-run `prepare_round.py --round 11 --season 2026` after 17:00 to pick up full 8/8.

### prepare_round.py dry-run — all green
Steps 1-8 all passed:
- R10 results: ✅ 8/8 confirmed
- Team stats / ELO: ✅ would rebuild
- Injuries T5: ✅
- Referees T6: ✅ 6/8 loaded (2 missing → T6=0.0 for those games)
- Weather T8: ✅ fetched live at runtime (step 6a)
- Pricing: ✅ dry-run complete

### ML Shadow CLV review
Ran summary across AFL R8-R9 + NRL R10 (3 rounds):

| Signal | Market | W-L | Running CLV |
|--------|--------|-----|-------------|
| ML | H2H | 17-8 | -0.054% |
| ML | Handicap | 11-15 | +0.423 pts |
| ML | Total | 14-12 | -0.885 pts |
| Market | H2H | 16-9 | +0.095% |
| Market | Handicap | 14-7 | +3.571 pts |
| Normal | H2H | 19-6 | +0.026% |
| Normal | Handicap | 13-13 | +1.577 pts |

**ML is neutral as expected.** Market signal (line movement) has the strongest CLV — +3.57 pts handicap.

### ML Shadow architecture confirmed
T3/T4/T6/T8 are already baked into XGBoost's feature set (not missing):
- T3: rest_days, bye, prev_margin, win/loss streaks
- T4: travel_km, venue_avg_total, venue_home_win_pct
- T6: ref_total_diff, ref_penalty_rate, ref_home_bias, ref_home_win_pct (from game_log_referee.csv)
- T8: rain_mm, wind_kmh, temp_c (from weather_conditions table)

Only T2/T5/T7 are applied as explicit additive deltas on top of ML Raw.

### Strategy confirmed
Run shadow for remaining rounds. If ML handicap CLV pulls sustainably positive over 8-10 rounds → promote ML Raw as T1 replacement in the normal engine. Also flagged: add running MAE tracking to shadow report (next session task).

## Pending for next session
- [ ] Add running MAE tracking to ML shadow report + rolling CLV summary
- [ ] Install BVI weekly Task Scheduler task (Monday 08:00, `afl_bvi.py`)
- [ ] Telegram pricing alert wrapper (user asked for this — needs BotFather token first)
- [ ] Re-run `prepare_round.py --round 11` after 17:00 if refs updated
- [ ] NRL R11 CLV report — runnable after round completes (May 15-17) + historical data lag (~Tue May 19)
