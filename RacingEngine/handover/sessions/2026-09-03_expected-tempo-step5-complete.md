# Expected Tempo Engine — five-step build complete

Date: 3 September 2026
Status: SHADOW_ONLY_AMBER

Step 5 is implemented in `racing_engine/expected_tempo_shadow.py`. Governance is
frozen in `config/expected_tempo_shadow_policy.json`. All 14 Expected Tempo tests
pass.

Artifacts:

- `reports/expected_tempo/expected_tempo_step5_governed_snapshots.csv`
- `reports/expected_tempo/expected_tempo_step5_append_only_snapshots.jsonl`
- `reports/expected_tempo/expected_tempo_step5_scorecard.json`
- `reports/expected_tempo/expected_tempo_step5_findings.md`

There are 872 replay snapshots and 649 governed eligible updates. Aggregate
classification improves, and middle/late continuous MAE improves in all three
evaluation folds. Classification log loss loses to V0 in fold two, so the full
promotion policy does not pass.

Operational rule: keep early tempo at V0; store capped probability and
middle/late shadow updates after each completed same-going race. Do not feed any
of these outputs into horse prices until prospective results pass the stored
policy and a separate integration decision is recorded.

Production `form-first-v2.0`, V2.10 horse ratings and all betting/pricing models
remain unchanged.
