# Session 2026-05-12 — R10 Results Loaded, R11 Referees, ML Shadow CLV

## What happened

### R10 Results loaded
- `r10_results_2026.csv` was mislabeled (contained May 1-3 / R9 data)
- Ran `fetch_nrl_results.py --round 10` → fetched correct R10 results (May 7-10) from NRL API
- 8 results written (match_ids 294-301): Dolphins 44-12 Canterbury, Roosters 28-12 Titans, Cowboys 30-33 Eels, Dragons 10-44 Knights, Rabbitohs 36-12 Sharks, Manly 32-4 Broncos, Storm 44-16 Tigers, Raiders 18-30 Panthers
- prepare_round.py dry-run R11 now fully green — Step 1 ✅

### R11 Pricing — tonight 19:03
All data in place:
- R10 results: ✅ in DB
- R11 fixture: ✅ in DB
- T5 injuries: ✅
- T6 referees: 6/8 loaded (Rabbitohs vs Dolphins + Panthers vs Dragons not yet announced)
- T8 weather: fetched live at runtime
- prepare_round dry-run: ✅ passed all steps

### ML Shadow CLV — 3-round review (AFL R8-R9, NRL R10)
ML shadow is neutral: H2H -0.054%, Handicap +0.423 pts, Total -0.885 pts.
Normal model: H2H +0.026%, Handicap +1.577 pts.
Market signal (line movement) leads: Handicap +3.571 pts.

Architecture confirmed: T3/T4/T6/T8 are baked into XGBoost feature set (not missing).
Only T2/T5/T7 are explicit additive deltas on top of ML Raw.

### Strategy confirmed
Shadow runs each round. If ML handicap CLV pulls sustainably positive over 8-10 rounds → promote ML Raw as T1 baseline in normal engine. Flagged: add running MAE tracking (next session).

## DB State
| Round | Dates | Results |
|-------|-------|---------|
| 0-9 | Feb 28 – May 3 | ✅ In DB |
| 10 | May 7-10 | ✅ In DB (loaded this session) |
| 11 | May 15-17 | ⏳ Magic Round — prices ready |

## Pending
- [ ] Run `prepare_round.py --round 11 --season 2026` at 19:03 (automated)
- [ ] Re-run after 17:00 if full 8/8 referees become available
- [ ] Add MAE tracking to ML shadow report
- [ ] NRL R11 CLV — after round + historical lag (~Tue May 19)
- [ ] AFL R10 pricing next session
