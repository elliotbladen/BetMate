# Rating model selection audit — form-first-v3.0

Date: 8 September 2026

## Trigger

User asked: is `form-first-v3.0` the model to use, audit it, and settle on
**one production model + one shadow**. Prompted by noticing a horse (Lindermann)
showing ~102 when it should be ~117 — the ~102 is `performance-par-v1.0` leaking
out of `horse_rating_states`, the only per-horse rollup table, which still holds
the legacy model.

## Work done

- Read `form_first_v3.py`, `v2_ratings.py`, the 6 Sep audit, the v3 build report,
  the two post-build fix commits (`35bbedf` weight-as-merit, `ead102a`
  pace-collapse direction), and the Sep 6 handover.
- Independent audit script (scratchpad, not committed) reproducing the audit's
  F1 (compression) and F6 (naive predictive) tests for par-v1 / v2 / v3, plus
  coverage, scale and Spearman-vs-official.
- Wrote **`docs/rating_model_selection_2026-09.md`** — full findings + decision.

## Findings

- **v3 is the right production choice** — supersedes v2 (real bug fixes, saner
  scale sd 17.4→13.5, pace corrections, margin taper). Running v2 keeps known-wrong
  WFA/tempo figures.
- **But v3 is not a validated betting input.** Its headline lever (form+speed dual
  rating, audit rec #1) is **built but dormant** — blocked on `performance-par-v2.0`.
- **v3 was shipped without re-running the audit's mandated gates, and fails both:**
  - F6 naive predictive (1,238 test races): v3 log loss 2.369 — worse than uniform
    (2.345) and worse than par-v1 (2.318); ≈ v2 (2.362).
  - Sanity Spearman vs official: v3 **0.47**, below the 0.50 gate v2 passes (0.65).
    n=24, elite set, some divergence intended — soft evidence, but a flag.
- Nothing consumes any rating model for pricing yet (`price_card.py` uses
  `base-lengths-v0.1`), so this is a research decision for now.

## Decision

| Role | Model |
|---|---|
| Production form rating | `form-first-v3.0` (with gates re-run — see doc §6) |
| Shadow | `performance-par-v1.0` (the speed figure; only model that beats uniform) |
| Retire | `horse-ability-v2.1…2.6`, `achieved-run-v2.x`, `base-lengths-v0.1` |

## Resume points (in priority order)

1. **`performance-par-v2.0`** — weight/class/going/pace-adjusted speed figure.
   Unblocks the v3 dual-rating blend. Everything else waits on this.
2. Flip `form_first_v3.py` change 1 to a two-way blend once par-v2 exists.
3. Re-run F6; require v3 to beat uniform AND par-v1. Re-run the sanity Spearman
   on the full set and explain the 0.47.
4. **`v3_horse_rating_states`** — consolidated per-horse rollup (recency-weighted
   overall + peak + recent + reliability). Repoint consumers off the legacy
   `horse_rating_states`.
5. Market-price / CLV backtest — still never run; the only test that settles
   "sufficient for betting".

## Refresh (8 Sep, done)

DB was already current (last metro meeting 5 Sep). Backed up to
`data/racing_engine.sqlite.bak-pre-refresh-0908`, rebuilt all three models
`--as-of 2026-09-08`:
- `performance-par-v1.0`: 34,636 perf / 14,137 states
- `form-first-v2.0`: 29,541 perf, sanity gate passes (Spearman 0.686), built-in
  predictive test log loss **2.520** vs uniform 2.345 vs par-v1 2.325 — confirms
  F6 on fresh data.
- `form-first-v3.0`: 29,498 perf.

## Architecture finding (doc §8b)

`form-first-v2.0` collapsed Step 1 of the ratings architecture into *collateral
only* — a winner is rated at the official marks of the horses they beat. The
architecture doc requires Step 1 to be *positive performance evidence about the
horse* (adjusted time/margin/weight/WFA/pace); collateral is Step 3, a bounded
revision layer. It drifted because the clock data couldn't yet carry a speed
figure (490/4104 races have no official time) and form-first was the only thing
that passed the (circular) sanity gate.

**Correction: build `performance-par-v2.0` as the Step-1 spine** by composing the
already-researched pieces (daily variant, carried weight, pace shapes) into one
adjusted speed figure, coefficients from prior research not fitted fresh. Then
demote collateral to a franked Step-3 layer on top.

## Rebuild started — increment 1 DONE

- `racing_engine/performance_par_v2.py` + `tests/test_performance_par_v2.py` (8 tests pass)
- `par_run_performances` table, explicit attributable components
- Increment 1 = raw_time_vs_par + daily_track_variant + clock quarantine + last-400 + margin
- **Naive predictive gate PASSED:** par-v2 **2.2988** < par-v1 2.3061 < uniform 2.3484.
  (form-first-v2.0 = 2.520, fails.)
- Report: `reports/v2_ratings/par_v2_build_report.json`

## Resume — par-v2 increments (doc §9)

1. **Increment 3 first (highest value): pace adjustment** from `v2_race_pace_shapes` /
   `v2_runner_pace_ratings` — slow-run race add-back, collapse dock. This is what
   fixes Lindermann's Chelmsford (currently 96 on par-v2, truth ~110-113) without
   the stale-collateral inflation.
2. Increment 2: weight merit (0.9 hcp / 0.2 WFA pts/kg).
3. Increment 4: one-sided class anchor for thin fields.
4. Increment 5: scale calibration (open the compressed p5-p95 ≈ 83-105 spread).
5. Re-run the gate at each increment; must keep beating uniform AND par-v1.
6. Then par-v2 becomes the base of `form-first-v3.1`; collateral → Step-3 franked revision.
7. `v3_horse_rating_states` consolidated per-horse rollup.

## Not done

- Seed not rebuilt (still 30 Aug — separate task).
- Retiring the stale shadow models (`horse-ability-v2.x`, `achieved-run-v2.x`,
  `base-lengths-v0.1`) — decision recorded, not executed.
- par-v2 is increment 1 only — NOT yet a usable rating (slow-run features badly
  under-rated until increment 3). Do not consume it.
