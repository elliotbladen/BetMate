# Week 2 player-shadow CLV and ROI

Hypothetical flat one-unit comparison. The selected side is the largest positive model EV at Football-Data average opening odds. CLV is opening odds divided by closing odds minus one.

## EPL

| Market | Filter | Engine | Bets | Wins | Mean CLV | +CLV | Opening P/L | Opening ROI | Closing ROI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1x2 | all_positive_edge | base | 10 | 5 | +2.5% | 6/10 | +7.18u | +71.8% | +68.2% |
| 1x2 | all_positive_edge | shadow | 9 | 6 | +3.5% | 6/9 | +11.28u | +125.3% | +119.6% |
| 1x2 | ev_10_percent | base | 6 | 3 | +5.1% | 4/6 | +7.04u | +117.3% | +109.2% |
| 1x2 | ev_10_percent | shadow | 6 | 3 | +5.1% | 4/6 | +7.04u | +117.3% | +109.2% |
| ou25 | all_positive_edge | base | 4 | 3 | +1.2% | 3/4 | +0.61u | +15.2% | +16.5% |
| ou25 | all_positive_edge | shadow | 4 | 2 | +7.6% | 4/4 | -0.80u | -20.0% | -21.5% |
| ou25 | ev_10_percent | base | 3 | 2 | +4.0% | 3/3 | +0.20u | +6.7% | +4.7% |
| ou25 | ev_10_percent | shadow | 2 | 1 | +4.9% | 2/2 | -0.49u | -24.5% | -25.5% |

## CHAMPIONSHIP

| Market | Filter | Engine | Bets | Wins | Mean CLV | +CLV | Opening P/L | Opening ROI | Closing ROI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1x2 | all_positive_edge | base | 9 | 2 | +6.3% | 7/9 | +1.68u | +18.7% | +2.1% |
| 1x2 | all_positive_edge | shadow | 8 | 2 | +6.3% | 6/8 | +2.68u | +33.5% | +14.9% |
| 1x2 | ev_10_percent | base | 5 | 2 | +5.6% | 3/5 | +5.68u | +113.6% | +83.8% |
| 1x2 | ev_10_percent | shadow | 5 | 2 | +5.6% | 3/5 | +5.68u | +113.6% | +83.8% |
| ou25 | all_positive_edge | base | 5 | 1 | +2.2% | 3/5 | -3.09u | -61.8% | -64.0% |
| ou25 | all_positive_edge | shadow | 10 | 1 | -0.9% | 5/10 | -8.09u | -80.9% | -82.0% |
| ou25 | ev_10_percent | base | 1 | 0 | -7.8% | 0/1 | -1.00u | -100.0% | -100.0% |
| ou25 | ev_10_percent | shadow | 5 | 1 | +2.2% | 3/5 | -3.09u | -61.8% | -64.0% |

## Interpretation

This is a diagnostic, not an actual-bets ledger. A one-round ROI result is highly volatile; CLV is the more useful early signal, while promotion of the shadow engine requires a much larger prospective sample.
