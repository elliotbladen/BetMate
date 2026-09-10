# Current horse-ratings state

Last updated: 10 September 2026.

## 9 September continuation — clock integrity and unfinished blend

The working tree contains unfinished changes to `form_first_v3.py`: par-v2
input, tempo-dependent two-way blending and missing-clock imputation. These
changes have not been promoted. The older model descriptions and sample
ratings below predate the corrected Sydney data and must not be treated as
fresh validation results.

Completed this continuation: `build_pars` now removes stale pars for the
requested model/cutoff before storing the rebuilt set. Previously a corrected
clock could leave a bucket below its minimum sample size while its old stored
par remained available to daily-variant estimation. Other models and cutoffs
remain intact. Regression tests cover impossible clocks, cutoff exclusion,
and removal of an ineligible par after a source correction. The focused clock,
par-v2, Step 11 and V2 suite passed all 39 tests on temporary databases.
No production database rebuild or model promotion was performed.

Next: finish the point-in-time audit of the pending blend before rebuilding.
Its speed loader selects the latest par snapshot without an evaluation cutoff;
alignment and missing-clock imputation fit across the entire available sample.
These paths need effective-date handling before historical concordance can
support a promotion decision. Validate the corrected-data candidate against
last-start and official-mark baselines on identical eligible rows.

Governance discrepancy: this document's older sections call v3.0 production,
but `AGENTS.md` and `config/v2_10_promotion_policy.json` still identify v2.0 as
accepted. No new promotion decision is recorded here; use the stored policy
and keep candidates explicitly labelled research/shadow.

## 10 September 2026 — Lindermann / Tempted sectional correction

The 5 September Randwick comparison confirms the rating concern. Lindermann's
Group 2 1600m was a sit-and-sprint: approximately 50.19 seconds for the first
800m and 45.41 for the last 800m. Tempted's Group 2 1000m was run harder
throughout: approximately 23.78 seconds for the first 400m and 21.53 for the
last 400m. The old `form-first-v2.0` therefore produced **117.5** for
Lindermann versus **110.7** for Tempted because it used collateral opposition
and explicitly did not use the clock or sectionals for the race level.

Implemented and rebuilt `performance-par-v2.0` through 6 September with a
sectional pace fallback for races missing a trained pace-shape row. It compares
equal early and late split blocks, labels sprint-home / sustained-pressure
shapes, and gives a bounded negative adjustment when a runner benefited more
than the field from a sprint-home pattern. The rebuild used the fallback on 752
races; the focused performance suite still passes.

Rebuilt `form-first-v3.0` after that change. The same runs now show:

| horse | old v2 form run | par-v2 speed run | v3 blended run |
|---|---:|---:|---:|
| Lindermann | 117.5 | 96.7 | 101.9 |
| Tempted | 110.7 | 110.1 | 103.8 |

This is the intended ordering direction: Tempted's better sustained speed
evidence places her above Lindermann on the blended run figure. These are run
ratings, not current horse-state ratings or prices. The fallback is a research
change pending walk-forward validation; it has not changed the accepted model
or promotion policy.

The accepted v2 clean history and form layer were rebuilt through the exclusive
cutoff 2026-09-06, then par-v2 and form-first-v3 were rebuilt on the same
database. The v3 rebuild rated 29,498 runs; 752 races used the sectional pace
fallback. The three-year v3 leaderboard covers 2023-09-06 through 2026-09-05.

## Models — state as at 8 September 2026

## Dan-aligned research shadow — 10 September 2026

Implemented `dan-aligned-wfa-v0.1` as a separate research table,
`dan_aligned_run_performances`. It reads the point-in-time `form-first-v3.0`
run figures, removes the stored runner-level pace allowance, applies the
official effective-dated Australian WFA schedule where age/sex coverage exists,
and applies an explicit elite-tail calibration (`knee=106`, slope `0.55`).
The first build covers 29,498 runs; WFA profile coverage is 39.0% and 10,093
runs had a runner pace term removed. It remains a shadow model and has not
changed accepted production ratings or pricing inputs.

The implementation and research rationale are documented in
`docs/dan_osullivan_blend_research_2026-09-10.md`. The first three-year
leaderboard is Via Sistina 115.1, Gold Trip 110.1, Prognosis 109.5, Sir Delius
108.8, Joliestar 108.8, Without A Fight 108.7, Pericles 108.6, Giga Kick 108.5,
Militarize 108.3 and Autumn Glow 108.3. These values are calibration evidence,
not a promotion decision; the next required work is increasing effective WFA
profile coverage and testing the race-strength layer walk-forward.

## Weather test — Randwick 5 September 2026

Imported ten timestamp-matched wind observations into `race_weather` under
`wunderground-observed-halfhour-v1`, using Rosebery Sydney Station
(`ISYDNEY618`) as the nearby observed proxy. Raw source rows are preserved in
`data/raw/weather/wunderground/randwick_2026-09-05.json`. The meeting opened
with northerly wind around 32–37 km/h, shifted west by Race 6, then strengthened
to approximately 42–66 km/h with a peak observed gust around 85 km/h around
Races 8–9 before easing for Race 10. No ratings have been changed yet; this is
an evidence and matching test only.

The Randwick wind sensitivity run is stored as
`dan-aligned-wind-test-randwick-v0.2` in `wind_adjusted_run_test`. It applies a
conservative eastbound home-straight vector, 25% race exposure, and a final
sectional-position shelter factor. This is a shadow sensitivity test only; it
is not yet a production weather adjustment.

Full story: `docs/rating_model_selection_2026-09.md`. Current ratings snapshot:
`docs/current_ratings_2026-09-08.md`.

**The new rating chain (research state, not yet promoted for betting):**

| Layer | Model | What it is |
|---|---|---|
| Step 1 run figure | **`performance-par-v2.0`** | adjusted speed figure: time vs par − daily track variant + pace add-back + weight merit + thin-par class anchor + winner ceiling. Strictly as-of. Beats par-v1 and uniform on the naive gate (2.293 / 2.306 / 2.348). |
| Step 3 franked form | **`form-first-v3.1`** | par-v2 + bounded franked collateral — a race's level is revised once its beaten field runs again, anchored on their *proven* later ability (not stale official marks). Gate strike 18.2% but the number is optimistic (see below). |
| Current ability | **`par-v2-ability-v1.0`** | per-horse: 90-day recency blend of v3.1 runs + reliability shrinkage + uncertainty + head-to-head cap (can't out-rate a horse that beat you last start). **This is the "what do we rate X" table** (`par_v2_horse_rating_states`). |

**Promotion blocker (increment 9):** `form-first-v3.1`'s predictive score used
future franking (the franked prior for a 2025 race saw the beaten field's
post-2025 runs). Needs effective-dated revisions + a walk-forward gate before it
replaces the old production model.

**Previous production (`form-first-v3.0`) / shadow (`performance-par-v1.0`)** stay
in place until v3.1 clears increment 9. **Retire** `horse-ability-v2.1…2.6`,
`achieved-run-v2.x`, `base-lengths-v0.1` — decision recorded, not executed.

All models rebuilt `--as-of 2026-09-08`. DB backups:
`racing_engine.sqlite.bak-pre-refresh-0908`, `.bak-ratings-rebuild-0908`.

**Sample ratings (`par-v2-ability-v1.0`):** Autumn Glow 107.5 (13 runs, ±2.0),
Tempted 106.9 (peak/last 110.4), Lindermann 101.4 (peak 111.0, last 99.3),
Ceolwulf 101.3 (head-to-head capped below Lindermann). `form-first-v2.0` had
Lindermann at 117.5.

## Prior note (still valid)

- `achieved-run-v2.10-young-wfa-shadow`: calculated over 2,732 races / 29,355
  performances, **amber / shadow only**, must not feed betting or pricing.
  Folds into the "retire the stale shadows" decision above unless it earns a
  promotion.

## Headline audit ratings

| Horse and run | Accepted | V2.10 achieved run |
|---|---:|---:|
| Guest House, Rosehill R8, 29 Aug 2026 | 98.46 | 104.30 |
| Oliveanotherday, Caulfield R6, 29 Aug 2026 | 110.46 | 110.36 |
| Natural Fling, Caulfield R6, 15 Aug 2026 | 83.53 | 98.55 |

Guest House's 104.30 is an achieved-run shadow, not its automatic next-start
forecast. Historical three-year-old Group/Listed validation selected 15% carry
forward of the achieved-run uplift. Full carry-forward failed.

## Completed work

- Added `racing_engine/achieved_run_young_wfa.py`.
- Added `tests/test_achieved_run_young_wfa.py`.
- Rebuilt race-time context and hierarchical sectional evidence through
  29 August 2026.
- Saved `reports/v2_ratings/achieved_run_v2_10_young_wfa.json` and findings.
- Stored fixed promotion rules in `config/v2_10_promotion_policy.json`.

## Required next implementation

Build an append-only prospective snapshot and outcome monitor. After every
meeting it must freeze the accepted rating, V2.10 achieved rating, 15%-shrunk
three-year-old next-start state, evidence availability, calculation timestamp
and model versions. When the horse next runs, attach the result without
altering the original prediction. Generate monthly green/amber/red scorecards
against the stored promotion gates and formal reviews at three, six and twelve
months.

No claim should be made that monitoring is automatic until that snapshot,
matching and scheduled-report workflow actually exists.
