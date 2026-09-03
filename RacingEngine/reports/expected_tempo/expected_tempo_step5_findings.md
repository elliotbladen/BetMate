# Expected Tempo Engine — Step 5 governed shadow result

Date: 3 September 2026
Final status: **SHADOW_ONLY_AMBER**

## Safeguards implemented

- At least one completed race under the same going is required.
- Meeting-state reliability must be at least 0.20.
- A going change resets the evidence regime.
- Per-class probability movement is capped at five percentage points.
- Changes below half a percentage point are ignored.
- Middle and late score movements are capped at 0.50.
- Early tempo is always held at V0.
- Every V0/V1/V2 snapshot has reason codes and a deterministic SHA-256 hash.
- The JSONL snapshot ledger is append-only and rejects duplicate hashes.
- Horse-price integration remains disabled.

## Governed results

The replay contains 872 frozen snapshots and 649 updates passing the evidence
and confidence gates.

| Probability forecast | Log loss | Brier | Accuracy |
|---|---:|---:|---:|
| V0 | 1.2481 | 0.6799 | 41.76% |
| Governed live | **1.2394** | **0.6753** | **43.30%** |

The governed update improves log loss by 0.69%, Brier by 0.68%, and accuracy by
1.54 percentage points. It improves folds one and three but loses fold two
(1.2383 versus 1.2323 log loss). Therefore it fails the mandatory every-fold
classification gate.

| Continuous target | V0 MAE | Governed MAE | Improvement |
|---|---:|---:|---:|
| Early | 1.0676 | 1.0676 | Held unchanged |
| Middle | 1.0960 | **0.9830** | **10.31%** |
| Late | 1.0539 | **0.9275** | **11.99%** |

Middle and late MAE improve in every chronological fold. This part passes its
historical gates, but remains shadow because the full engine has not passed all
required gates or prospective operation.

## Decision

The five-step architecture is built. The governed tempo engine is suitable for
prospective shadow collection, not horse-price changes. V0 remains authoritative;
middle/late live estimates and capped probabilities should be recorded beside
it until the every-period probability gate passes on new meetings.
