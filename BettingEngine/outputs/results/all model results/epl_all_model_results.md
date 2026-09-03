# EPL all-model results — Weeks 1 and 2

Scope: every frozen normal-engine prediction available for 1X2 and O/U 2.5.  
Reference: de-vigged Football-Data average opening and closing markets.  
Lower RPS, Brier score and log loss are better.

## Coverage

| Week | Scheduled results | Frozen predictions | Coverage |
|---|---:|---:|---:|
| Week 1 | 10 | 10 | 100% |
| Week 2 | 10 | 9 | 90% |

Coventry v Hull is excluded from Week 2 because no frozen model prediction was
found. It was not reconstructed after the result.

## 1X2

| Week | Matches | Model RPS | Closing RPS | Model log loss | Closing log loss | Model accuracy | Closing accuracy | Value side shortened |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Week 1 | 10 | **0.2016** | 0.2253 | **0.8957** | 0.9684 | **70.0%** | 60.0% | 4/10 |
| Week 2 | 9 | 0.1811 | **0.1566** | 1.0027 | **0.9143** | 55.6% | 55.6% | 2/9 |
| **Combined** | **19** | **0.1919** | 0.1928 | 0.9464 | **0.9428** | **63.2%** | 57.9% | — |

EPL 1X2 was excellent in Week 1 and below the closing market in Week 2. Across
19 predictions, RPS is fractionally better than close while log loss is
fractionally worse. That is best described as approximately market-level with
encouraging top-pick accuracy, not a demonstrated edge.

The model's strongest closing-edge side shortened in only 6 of 19 matches.
Mean movement was -0.40% in Week 1 and -3.68% in Week 2, so the market did not
broadly validate the model's value direction.

## O/U 2.5

| Week | Matches | Model Brier | Closing Brier | Model log loss | Closing log loss | Model accuracy | Closing accuracy | Value side shortened |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Week 1 | 10 | **0.2015** | 0.2244 | **0.5900** | 0.6411 | 60.0% | **70.0%** | 3/10 |
| Week 2 | 9 | 0.2814 | **0.2246** | 0.7587 | **0.6406** | 44.4% | **55.6%** | 9/9 |
| **Combined** | **19** | 0.2394 | **0.2245** | 0.6699 | **0.6408** | 52.6% | **63.2%** | — |

EPL totals beat the market on probability score in Week 1 but failed clearly in
Week 2. The two-week model is worse than close on Brier, log loss and accuracy.
Interestingly, every Week 2 value direction shortened, averaging +5.16%
market-move CLV, but the outcomes still graded badly. Continue tracking, but do
not infer totals calibration from that CLV alone.

## Decision

- EPL 1X2: continue unchanged in prospective evaluation; currently near market.
- EPL O/U 2.5: amber; investigate Week 2 overconfidence and retain strict bet filters.
- Do not combine these results with Championship metrics.
