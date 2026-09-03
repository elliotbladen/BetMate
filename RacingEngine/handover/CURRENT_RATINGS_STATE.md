# Current horse-ratings state

Last updated: 1 September 2026.

## Production and shadow models

- Production remains `form-first-v2.0`.
- `achieved-run-v2.10-young-wfa-shadow` has been calculated historically over
  2,732 races and 29,355 performances.
- V2.10 must not feed betting or pricing until its promotion policy passes.
- Current promotion status is **amber / shadow only**.

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
