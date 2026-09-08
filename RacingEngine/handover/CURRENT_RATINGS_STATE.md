# Current horse-ratings state

Last updated: 8 September 2026.

## Production and shadow models

Model selection settled 8 Sep — see `docs/rating_model_selection_2026-09.md`.

- **Production form rating: `form-first-v3.0`** (supersedes v2 — real bug fixes,
  saner scale, pace corrections). Gates still to be re-run; nothing consumes it
  for pricing yet.
- **Shadow: `performance-par-v1.0`** (the speed figure; the only model that beats
  a uniform guess on the naive ranking test). Form-vs-speed cross-check.
- **Retire:** `horse-ability-v2.1…2.6`, `achieved-run-v2.x`, `base-lengths-v0.1`
  — stale, unused, and the cause of "one horse, four ratings". Decision recorded,
  not yet executed.
- All models rebuilt `--as-of 2026-09-08` (refresh). DB backup:
  `data/racing_engine.sqlite.bak-pre-refresh-0908`.

## Rebuild in progress — `performance-par-v2.0` (the new Step-1 spine)

`form-first` rates a winner off the *official marks of the horses they beat*; the
architecture requires Step 1 to be the horse's own adjusted performance. Building
`performance-par-v2.0` as a composed adjusted speed figure (variant + weight +
pace + thin-field anchor). **Increments 1 + 3 done** (daily variant, clock
quarantine, pace add-back). Naive predictive gate passes and improves each step
(2.2931 vs par-v1 2.3061 vs uniform 2.3484). Lindermann/Tempted now match the
expert anchor (Lindermann ~101, Tempted ~110). Increments 2 (weight), 4 (class
anchor), 5 (scale) pending — not yet the promoted rating.

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
