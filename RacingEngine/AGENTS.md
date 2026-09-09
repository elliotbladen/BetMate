# RacingEngine persistent operating instructions

Before trusting any metric or source comparison, read
`../handover/DATA_INTEGRITY_LESSONS.md` — ten real cases from this repo where a
confident, well-evidenced number was wrong, including three where the checking
tool itself was the fault.

## THIS IS A HORSE RATING ENGINE

It answers "how good was that run" and "how good is that horse", on a scale where
a point means a consistent amount of merit. It is not a tipping model, not a
pricing model and not a betting model.

The Pricing Engine comes LATER and is a separate build (ratings build plan stage
6). It will combine the rating with barrier, projected map and tempo, going,
weight-for-the-day, jockey/trainer and the market. **The horse rating is expected
to be 50-60% of that pricing signal, which is exactly why the rating has to be
right on its own terms first.**

**Judge a rating as a rating.** Use `python3 -m racing_engine.rating_quality`:
concordance on prior form, run-to-run repeatability, margin calibration, scale.
Do NOT promote or reject a rating on win probability, top-pick strike rate, log
loss or ROI — those measure the ratings-to-price conversion, which is not built
yet. `prediction_test` in `franked_form.py` is retained as a labelled DIAGNOSTIC
only. The build plan is explicit: "no profit claim is permitted from ratings
alone."


Read `handover/CURRENT_RATINGS_STATE.md` and
`config/v2_10_promotion_policy.json` before changing, rebuilding, reporting or
promoting horse ratings.

The accepted production model is `form-first-v2.0`. The model
`achieved-run-v2.10-young-wfa-shadow` is comparison-only. Never silently use a
shadow rating for betting, pricing or production output, and never promote it
without satisfying the stored promotion policy and recording the decision.

For every newly completed meeting, preserve point-in-time accepted ratings,
V2.10 achieved-run ratings, V2.10 next-start state estimates, evidence
availability and model versions. Do not overwrite frozen prospective snapshots.

When asked for a horse rating, label the accepted and shadow figures explicitly.
When continuing V2.10 work, update the current-state handover and promotion
ledger/report so a later session does not depend on chat memory.
