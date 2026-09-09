# Scope correction: this is a HORSE RATING ENGINE — and the gates now match

Date: 9 September 2026

## The problem the user spotted

The engine was being promoted/rejected on **top-pick strike rate and log loss**.
Those come from `prediction_test`, which fits a softmax temperature over the
ratings and scores picks. That is a **pricing-layer** measurement — it scores
`ratings -> probabilities -> picks`, and the conversion is not part of the rating.

The build plan already drew this line and it had been crossed:

> Stage 6 — Pricing integration and market EV test. *"No profit claim is
> permitted from ratings alone."*

Judging a rating on strike rate fails in both directions:

* **False negative** — a well-ordered rating fails because one global temperature
  cannot map ratings to probabilities across field sizes, distances and class.
  The symptom was already recorded: *"temperature maxed the grid — the optimiser
  wants to flatten the ratings almost entirely."*
* **False positive** — a flat rating can look acceptable in aggregate while
  ordering horses badly inside races, which is the only thing a rating does.

**The rating is expected to be 50-60% of the pricing signal when that engine is
built.** It has to be right on its own terms first.

## What changed

### New: `racing_engine/rating_quality.py` — four rating-layer gates

| Gate | Question |
|---|---|
| **Concordance** | Does PRIOR form order the finish? Pairwise, no probability, no fitted parameter. |
| **Repeatability** | Does a horse's figure predict its NEXT figure? The Timeform/Ragozin criterion. |
| **Margin calibration** | Does a prior rating gap translate into the lengths the scale claims? |
| **Scale** | Can it express an elite run? (audit F1) |

`python3 -m racing_engine.rating_quality --compare form-first-v2.0 performance-par-v2.0 form-first-v3.1`

**Circularity caught during the build.** The first version scored the run figure
against its own race and returned concordance 0.84 — but a run figure is
*derived* from that race's beaten margin, so it was grading the model on its own
arithmetic. Both concordance and margin calibration now use each horse's prior
figure (median of its last 3 runs before the race). Any concordance near 0.85+ is
the signature of that mistake returning.

### `form-first-v2.0` measured as a rating

| Metric | Value | Read |
|---|---:|---|
| Concordance (prior form) | **0.553** | barely above a 0.50 coin flip — it does not order fields |
| Repeatability | **0.644** | good; the figure reliably reproduces itself |
| Points per length | **0.165** | a 1-point prior gap predicts 0.165 L, against a scale claiming 0.33-1.0 L |
| Scale p5 / p95 / max | 48.9 / 103.0 / 127.4 | compressed through the middle |

**Stable but not discriminating** — it repeats well while failing to separate a
field. That is the compression finding (everything bunched 85-105) seen from the
rating side, and it is exactly what a strike-rate test obscures.

### Relabelled, not deleted

`prediction_test` stays, with a docstring stating plainly that it is a
DIAGNOSTIC and a pricing-layer proxy, never a promotion gate. It is still a
useful early read on whether ratings will survive the pricing layer.

### Documentation

- `AGENTS.md` — new opening section: THIS IS A HORSE RATING ENGINE, which gates
  apply, which do not, and why. Read every session.
- Scope banner added to `README.md`, `project_tracker.md`, `ratings_build_plan.md`,
  `rating_system_audit_2026-09.md`, `rating_model_selection_2026-09.md`.
- Past session handovers were deliberately NOT rewritten. They are a record of
  what was believed at the time.

## Where this leaves the ratings

The data foundation is now sound (NSW clock 0% -> 87.9%, 362 wrong distances
corrected, coverage gate passing) and the franking leakage is effective-dated.
The open question is no longer "does it pick winners" but:

**Does par-v2 / v3.1 order a field better than v2.0's 0.553, and does franking
improve repeatability above 0.644?** Franking claims to correct a race level
using better information, so it should raise both. If it does not, the franking
layer is adding noise and should be reconsidered rather than tuned.

`par_run_performances` and `franked_run_performances` do not exist on the Mac, so
run the comparison on the PC.
