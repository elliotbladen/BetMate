# Session Diary — 2026-08-12: NRL ML Shadow v1 Build

## Goal

Add an XGBoost shadow component to the successful NRL rules engine without
changing official prices. Research and architecture are recorded in
`docs/nrl_ml_shadow_architecture.md`.

## Audit Findings

- Existing long-history features: 3,469 matches, 2009–2026.
- Detailed match stats: 912 JSON files, 2022–2026.
- Market-movement training rows: 590, 2024–2026.
- Dormant model tests existed, but production binaries were absent locally.
- Old runner problems: T2–T8 were added on top of ML; rest categories became NaN;
  venue snapshots were hard-coded; the displayed H2H was derived from adjusted
  margin instead of the classifier; probability calibration was missing.

## Implemented

### Local feature and model contracts

- `ml/nrl/results/features_nrl.csv` — local 2009–2026 feature store.
- `ml/nrl/features.py` — 32 numeric pre-market features; broken string rest
  classes excluded.
- `ml/nrl/models.py` — versioned pickle-safe margin and H2H bundles.
- Genuine missing optional features remain NaN for XGBoost.

### Training

- `scripts/train_nrl_ml_shadow.py`
- XGBoost margin regression with shallow trees and regularisation.
- XGBoost H2H classification with sigmoid calibration on the final training
  season, disjoint from base-model fitting.
- Production model uses history through 2024 plus 2025 calibration and is tagged
  `nrl_premarket_shadow_v1_through_2025`.

### Walk-forward results

| Season | Games | Margin MAE | H2H accuracy | Brier | Log loss |
|---|---:|---:|---:|---:|---:|
| 2024 | 213 | 14.36 | 61.03% | 0.2287 | 0.6491 |
| 2025 | 213 | 14.31 | 59.15% | 0.2360 | 0.6648 |

The model is not promoted. Its probability performance is only modest and must
be compared prospectively with the strong rules model.

### Closing-market test

- `scripts/backtest_nrl_ml_shadow_market.py`
- Current historical workbook matches all 426 walk-forward games by fixture, but
  contains closing H2H/handicap fields for only 65 games across 2024–25.
- On that incomplete subset: H2H 7pp trigger 39 bets, +$5.60, +14.36%; handicap
  6pt trigger 17 bets, +$3.65, +21.48%.
- These ROI figures are preliminary and must not be treated as proof because the
  market coverage is incomplete and potentially non-random.

### Live deployment

- Repaired `ml/run_r9_shadow.py` to load the versioned models.
- ML margin/H2H outputs are now independent. Tier adjustments remain printed for
  diagnostics but are not added to predictions.
- `scripts/prepare_round.py` automatically runs the ML shadow after official
  pricing. `--skip-ml-shadow` disables it.
- A shadow failure is non-fatal and cannot change official rules prices.
- Predictions are stored in `ml_shadow_predictions`.

### R24 smoke test

Eight games successfully generated and stored. Output:
`outputs/results/nrl_r24_ml_shadow_v1_2026-08-12.txt`.

Largest observation flags:

- Broncos vs Warriors: ML margin Warriors -8 versus rules Warriors -16; ML home
  probability 46.4% versus rules 9.1%. This severe probability/margin mismatch
  requires review before trusting either H2H head.
- Knights vs Titans: ML Knights +13.6 versus rules +6.0.
- Bulldogs, Sharks, Dolphins and Cowboys games showed 10pp+ H2H differences.

These are shadow flags, not recommended bets.

## Tests

- Python compilation passed for all new/modified modules.
- `tests/test_nrl_ml_shadow.py` and existing AFL versioned tests: 4 passed.
- Normal pricing CLI exposes `--skip-ml-shadow`.

## Important Limitations

1. The current shadow uses stable-core features, not the detailed rolling 2022+
   process-stat challenger yet.
2. Venue/referee/weather completeness in the R24 live rows is only 74–79%.
3. The H2H classifier and margin model can disagree. Next version should compare
   the direct classifier with a calibrated probability derived from margin
   residuals and prefer the coherent version if it validates better.
4. Historical 2024–25 closing-price coverage needs repair before ROI conclusions.
5. Totals output is research-only and must not influence the official totals model.

## Next Steps

1. Repair/import complete 2024 and 2025 closing H2H/handicap markets.
2. Build rolling process-stat features from the 912 JSON files.
3. Add structured spine, injury and Origin availability features.
4. Compare core versus rich-stat models on identical 2024/2025 folds.
5. Add margin-derived calibrated H2H and coherence checks.
6. Grade every remaining 2026 round prospectively without retuning.
