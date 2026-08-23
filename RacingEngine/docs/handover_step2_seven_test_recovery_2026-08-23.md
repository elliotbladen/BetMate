# Handover — Step 2 seven-test recovery

Step 3 remains blocked. Accepted ratings were not changed.

## Deliberate pause — return next week

Work is deliberately paused here on 23 August 2026. We will return next week
to finish Step 2; Step 2 is not complete and Step 3 must not begin meanwhile.
The restart point is the pre-specified V2.6 target decomposition below, plus
appending any newly available race and next-start evidence to the frozen
forward ledger. Do not refit V2.4 or V2.5 against the August 22 holdout.

The major data problem is solved: official Victorian 200m split times and
positions are now ingested from Racing.com's public GraphQL service with CSV
fallback. Coverage is 1,330/1,341 races and 106,249 segments. The importer is
`racing_engine/victorian_200m.py` and all evidence is stored in
`v2_vic_200m_sectionals` with provenance and payload hashes.

V2.4 passed every directional historical ranking/MAE subdivision but failed the
next-start uncertainty gate and the tiny August 22 forward card. V2.5 tested a
distinct hierarchical par design; compensation-only came within +0.00143 of a
fully favourable next-start interval but still failed. Do not tune it further.

The stall is now understood as target separation, not absent signal. Sectionals
reliably improve retrospective race ranking, but current code asks one additive
number to represent achievement, trip compensation, persistent ability and
future pace suitability. Build V2.6 as specified in the notes: persistent pace
traits, multi-run/neutral-run latent targets, hierarchical partial pooling, and
a genuinely untouched 2026/live test.

Frozen evidence:

- `config/sectional_promotion_protocol_v2.json`
- `reports/v2_ratings/vic_200m_backfill.json`
- `reports/v2_ratings/energy_sectionals_v2_4_evaluation.json`
- `reports/v2_ratings/energy_sectionals_v2_5_evaluation.json`
- `reports/v2_ratings/sectional_forward_v2_4_20260822.json`

Do not proceed to Step 3 until the protocol passes. The next action is not more
V2.5 coefficient searching; it is the pre-specified V2.6 target decomposition.

When work resumes next week:

1. Append newly available NSW and Victorian meetings without changing frozen
   coefficients.
2. Score any now-observable next starts from the August 22 ledger.
3. Build V2.6 persistent pace traits and multi-run/neutral-run ability targets.
4. Train only on the designated pre-2025 window and preserve the final 2026/live
   test.
5. Run the complete frozen promotion protocol.
6. Finish Step 2 only if every required audit passes; otherwise document the
   failed component and test a separately versioned solution.

Add Natural Fling's 15 August 2026 four-length Caulfield Group 3 win to the
mandatory expert breakout audit. The hard achieved-performance acceptance range
is **100-110** on this engine's scale. This remains an evaluation constraint,
not a fitted training label: independent time, meeting variant, positive
winning-margin, WFA, 200m-sectional and collateral evidence must produce the
figure. Anything outside the band blocks promotion and requires an architecture
review. Compare the run with Ka Ying Rising's Everest only after equivalent
evidence treatment.

## Added priority — identify future Group horses early

On resumption, treat early high-class ability detection as a core ratings-engine
deliverable. Pure collateral is too late for the user's value-first approach.
Implement separate achieved-run, latent-current and forward-development states,
plus a pace-style vector and calibrated breakout probabilities. Build the
historical young-horse cohort point-in-time and compare with official rating,
class-only V2 and naive age/start baselines. Measure false positives and lead
time—not only later winners. Natural Fling is a hard sanity case, never the
training label. Read and follow `docs/future_group_horse_research.md` before
beginning V2.6.
