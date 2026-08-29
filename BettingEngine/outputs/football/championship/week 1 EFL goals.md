# Week 1 EFL goals

Frozen pre-match Championship prices. Model timestamp: 2026-08-15 Australia/Sydney; information cutoff: 2026-08-14 pre-kickoff.

| Match | O2.5 % | Fair O2.5 | U2.5 % | Fair U2.5 | BTTS % | Fair BTTS | No BTTS % | Fair No BTTS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Wolves v Blackburn | 44.9% | 2.22 | 55.1% | 1.82 | 50.8% | 1.97 | 49.2% | 2.03 |
| Bolton v Preston | 44.9% | 2.22 | 55.1% | 1.82 | 52.1% | 1.92 | 47.9% | 2.09 |
| Bristol City v Millwall | 44.9% | 2.22 | 55.1% | 1.82 | 53.0% | 1.89 | 47.0% | 2.13 |
| Charlton v Derby County | 44.9% | 2.22 | 55.1% | 1.82 | 45.2% | 2.21 | 54.8% | 1.83 |
| Middlesbrough v Lincoln | 44.9% | 2.22 | 55.1% | 1.82 | 49.7% | 2.01 | 50.3% | 1.99 |
| Norwich v West Brom | 44.9% | 2.22 | 55.1% | 1.82 | 48.2% | 2.08 | 51.8% | 1.93 |
| Portsmouth v QPR | 47.6% | 2.10 | 52.4% | 1.91 | 57.5% | 1.74 | 42.5% | 2.35 |
| Stoke v Swansea | 47.6% | 2.10 | 52.4% | 1.91 | 54.9% | 1.82 | 45.1% | 2.22 |
| Sheffield United v Birmingham | 47.6% | 2.10 | 52.4% | 1.91 | 49.0% | 2.04 | 51.0% | 1.96 |
| Watford v Southampton | 60.4% | 1.66 | 39.6% | 2.53 | 69.9% | 1.43 | 30.1% | 3.32 |
| Burnley v West Ham | 44.9% | 2.22 | 55.1% | 1.82 | 53.7% | 1.86 | 46.3% | 2.16 |
| Cardiff v Wrexham | 47.6% | 2.10 | 52.4% | 1.91 | 58.6% | 1.71 | 41.4% | 2.41 |

## Reference market snapshot

Current best available Over/Under 2.5 prices were frozen from the BetMate feed at 2026-08-15 09:24:47 Australia/Sydney, where the match remained available. BTTS was not present in that feed and is model-only.

| Match | Market O2.5 | Book | Market U2.5 | Book |
|---|---:|---|---:|---|
| Wolves v Blackburn | — | — | — | — |
| Bolton v Preston | 2.00 | playup | 1.82 | tabtouch |
| Bristol City v Millwall | 1.93 | tabtouch | 1.83 | playup |
| Charlton v Derby County | 2.12 | playup | 1.68 | playup |
| Middlesbrough v Lincoln | 1.68 | playup | 2.23 | tabtouch |
| Norwich v West Brom | 1.90 | playup | 1.86 | unibet |
| Portsmouth v QPR | 1.95 | playup | 1.88 | tabtouch |
| Stoke v Swansea | 2.08 | playup | 1.72 | playup |
| Sheffield United v Birmingham | 1.98 | unibet | 1.80 | playup |
| Watford v Southampton | 1.74 | tabtouch | 2.05 | playup |
| Burnley v West Ham | 1.72 | playup | 2.05 | tabtouch |
| Cardiff v Wrexham | 1.72 | playup | 2.05 | tabtouch |

## Audit notes

- Uses the same frozen Week 1 injury inputs as the 1X2 sheet.
- T2 pressing inactive (no Championship PPDA); T6 referee inactive (failed validation/unavailable appointments).
- T3, T5, T7 and T8 applied wherever inputs were available. T9 was not forced without a qualifying verified trigger.
- Over/Under 2.5 is the calibrated model output. BTTS is derived directly from the adjusted Dixon-Coles score matrix and is not separately calibrated.
- Closing prices and actual results must be appended later without overwriting this frozen forecast.

## Frozen 15%+ value positions

Recorded 2026-08-15 10:32:09 AEST. These are observed prices at the time of the scan, not automatically labelled as the market opener.

| Match | Selection | Model % | Model fair | Observed odds | Source | Expected value | Status |
|---|---|---:|---:|---:|---|---:|---|
| Middlesbrough v Lincoln | Under 2.5 | 55.1% | 1.82 | 2.23 | Grosvenor / BetMate-TABtouch snapshot | +22.9% | Frozen candidate |
| Burnley v West Ham | Under 2.5 | 55.1% | 1.82 | 2.15 | BetOnline | +18.5% | Frozen candidate |

### Post-round audit fields

| Match | Selection | True opening odds | Closing odds | Beat opener? | Beat close? | Result | $1 P/L |
|---|---|---:|---:|---|---|---|---:|
| Middlesbrough v Lincoln | Under 2.5 | Pending snapshot audit | Pending | Pending | Pending | Pending | Pending |
| Burnley v West Ham | Under 2.5 | Pending snapshot audit | Pending | Pending | Pending | Pending | Pending |

Evaluation rules:

- Recover the earliest available 2.5-goal snapshot as the opener; do not substitute the observed candidate price.
- Use the final available pre-kickoff snapshot as the close.
- The model beats a reference price when its fair probability implies a shorter price than that no-vig market probability.
- The captured bet beats the close when its obtainable odds are higher than the same-selection closing odds.
- Grade each candidate at a flat $1 stake after the official result is confirmed.
