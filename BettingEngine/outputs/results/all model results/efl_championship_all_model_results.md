# EFL Championship all-model results — Weeks 1 and 2

Scope: every frozen normal-engine prediction available for 1X2 and O/U 2.5.  
Reference: de-vigged Football-Data average opening and closing markets.  
Lower RPS, Brier score and log loss are better.

## Coverage

| Week | Scheduled results | Frozen predictions | Coverage |
|---|---:|---:|---:|
| Week 1 | 12 | 12 | 100% |
| Week 2 | 12 | 11 | 91.7% |

Derby v Cardiff is excluded from Week 2 because no frozen model prediction was
found. It was not reconstructed after the result.

## 1X2

| Week | Matches | Model RPS | Closing RPS | Model log loss | Closing log loss | Model accuracy | Closing accuracy | Value side shortened |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Week 1 | 12 | **0.2305** | 0.2422 | **1.1268** | 1.1634 | **33.3%** | 25.0% | 3/12 |
| Week 2 | 11 | **0.2213** | 0.2495 | **1.1176** | 1.2008 | **36.4%** | 27.3% | 4/11 |
| **Combined** | **23** | **0.2261** | 0.2457 | **1.1224** | 1.1813 | **34.8%** | 26.1% | — |

The Championship 1X2 model beat the closing market on RPS, log loss and top-pick
accuracy in both weeks. This is the strongest all-model result so far.

However, its strongest value side shortened in only 7 of 23 matches. Average
movement was +0.85% in Week 1 and -1.24% in Week 2. The probability result is
encouraging, but price movement does not yet provide broad confirmation.

## O/U 2.5

| Week | Matches | Model Brier | Closing Brier | Model log loss | Closing log loss | Model accuracy | Closing accuracy | Value side shortened |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Week 1 | 12 | 0.2652 | **0.2583** | 0.7235 | **0.7100** | 33.3% | **58.3%** | 5/12 |
| Week 2 | 11 | 0.2748 | **0.2362** | 0.7429 | **0.6653** | 27.3% | **54.5%** | 3/11 |
| **Combined** | **23** | 0.2698 | **0.2477** | 0.7328 | **0.6886** | 30.4% | **56.5%** | — |

Championship totals lost to the closing market in both weeks and across every
reported scoring measure. Value directions shortened in only 8 of 23 matches,
with negative average movement in both weeks combined. This is a clear model
weakness, not just a losing bet shortlist.

## Decision

- Championship 1X2: promising; continue prospective collection without raising stakes.
- Championship O/U 2.5: red/rebuild candidate; do not loosen filters.
- Keep Championship analysis completely separate from EPL.
