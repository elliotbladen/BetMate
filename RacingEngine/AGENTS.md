# RacingEngine persistent operating instructions

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
