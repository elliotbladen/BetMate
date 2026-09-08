# Current horse-ratings state

Last updated: 8 September 2026.

## Models — state as at 8 September 2026

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
