# 2026-08-12 — AFL Rules + ML Combined Model Research

## Objective

Investigate whether the archived AFL rules-engine prices and legacy ML shadow
predictions should be combined for H2H and handicap markets. Totals were explicitly
excluded; the rules totals model remains unchanged.

## Model Roles

- Official price remains the T1–T8 rules engine.
- `legacy_primary` is a reconstructed, market-independent XGBoost H2H model.
- `current_shadow` is the newer calibrated, market-aware model.
- Missing bookmaker probabilities may not be replaced by ELO. The current shadow
  abstains when a genuine market input is unavailable.

The exact old binary had previously been overwritten, so the legacy model is a
reproducible reconstruction rather than the original pickle.

## Versioned H2H Comparison

Both candidates were rebuilt from a common 2009–2025 history and walk-forward
tested over 2023–2025.

| Model | Accuracy | Log loss | Brier | 7pp closing bets | ROI |
|---|---:|---:|---:|---:|---:|
| Legacy primary | 64.81% | 0.6449 | 0.2224 | 395 | -6.89% |
| Current shadow | 63.43% | 0.6451 | 0.2222 | 417 | -7.89% |

Neither standalone historical candidate demonstrated an edge over the close.

## Archived 2026 Blend Test

Predictions were recovered for R8–R22. The settled evaluation contains 108 games
through R21 across 13 stored rounds. R20 has no archived price-up. R22 predictions
exist but outcomes were not yet present in the historical workbook, so they were
left ungraded. Fixture dates are required in the join to prevent repeated matchups
from being matched to the wrong game.

### Frozen Combined Specification

H2H:

```
combined_home_probability = 0.60 * rules_probability + 0.40 * legacy_ml_probability
trigger = 7 probability points versus no-vig closing market
```

Handicap:

```
combined_margin = 0.25 * rules_margin + 0.75 * legacy_ml_margin
trigger = 6 points versus closing handicap
```

Totals: rules-only; no combined model.

### Settled Results

| Market | Bets | Record | Profit | ROI |
|---|---:|---:|---:|---:|
| H2H, actual closing prices | 58 | 37–21 | +$12.96 | +22.34% |
| Handicap, standard $1.90 | 67 | 40–27 | +$9.00 | +13.43% |
| Combined | 125 | 77–48 | +$21.96 | +17.57% |

H2H probability quality for the frozen 60/40 blend: Brier 0.1830 and log loss
0.5352. Complete handicap closing lines were used, but closing handicap prices were
not complete, so handicap ROI was settled at a uniform $1.90.

These weights were chosen retrospectively from the same sample. Their headline ROI
contains selection optimism and is not yet independent proof. Do not tune them in
response to R23–R24; grade those rounds prospectively with the weights frozen.

## R23 Pretend Combined Prices

| Match | Combined H2H | Combined fair handicap |
|---|---:|---|
| Fremantle vs Adelaide | $1.34 / $3.96 | Fremantle -2.2 |
| Richmond vs St Kilda | $3.79 / $1.36 | St Kilda -33.6 |
| North Melbourne vs Geelong | $3.78 / $1.36 | Geelong -31.4 |
| Brisbane vs Gold Coast | $1.08 / $12.84 | Brisbane -39.1 |
| Hawthorn vs Collingwood | $1.38 / $3.65 | Hawthorn -20.4 |
| Port Adelaide vs Melbourne | $2.30 / $1.77 | Melbourne -24.0 |
| GWS vs West Coast | $1.13 / $8.63 | GWS -42.8 |
| Western Bulldogs vs Carlton | $1.44 / $3.27 | Bulldogs -12.0 |
| Essendon vs Sydney | $11.99 / $1.09 | Sydney -47.1 |

Fremantle–Adelaide is internally inconsistent: the combined H2H strongly favours
Fremantle while the combined margin is only Fremantle -2.2. Treat this as an
abstention/data-review flag rather than a coherent price.

## Round 23 Market-Movement Alerts

- Port–Melbourne: Melbourne moved from -10.5 to -29.5.
- Bulldogs–Carlton: Bulldogs -2.5 reversed through zero to Carlton -13.5.
- Richmond–St Kilda: Richmond moved from +36.5 to +22.5 and $6.05 to $3.60.

Richmond was the cleanest multi-model disagreement. Port and Bulldogs were large,
unstable single-model disagreements and should not be automatic bets.

## Files

- `scripts/backtest_afl_blends_r8_r22.py`
- `outputs/backtests/afl_blends_r8_r22/fixed_combined_summary.csv`
- `outputs/backtests/afl_blends_r8_r22/fixed_combined_game_results.csv`
- `scripts/compare_afl_h2h_versions.py`
- `outputs/backtests/afl_h2h_versions/`
- `outputs/forward_tests/afl_h2h_r23_2026.csv`
- `docs/afl_ml_rules_integration_architecture.md`

## Next Actions

1. Keep the official rules prices unchanged for the remainder of 2026.
2. Add the frozen combined H2H and handicap prices as visible shadow fields.
3. Grade R23 and R24 without changing weights or triggers.
4. Refresh R22 outcomes and include them once the historical workbook is current.
5. At season end, assess Brier/log loss, closing-price ROI, handicap ATS, CLV,
   threshold stability and round-cluster uncertainty before promotion.
