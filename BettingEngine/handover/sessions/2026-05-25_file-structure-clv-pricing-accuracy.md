# Session 2026-05-25 — File Structure Overhaul + CLV/Pricing/Accuracy Organisation

## What happened

Full data folder restructure for BettingEngine. Three new organised data folders
created with consistent naming conventions across NRL and AFL. Scripts written to
automate the ongoing upkeep.

---

## Changes made

### 1. CLV Running Total — R8/R9 supplement added

`scripts/update_clv_running.py` updated to read `data/clv/running/model_clv_supplement_nrl_2026.csv`.
This file contains game-level model CLV for NRL R8 and R9 (rounds where no actual bets
were tracked in the ledger, only model-level reports existed).

NRL running CLV is now **+7.94%** across 4 rounds (23 data points):
- R8: +12.31%  (8 games, model CLV only, $0 P&L)
- R9: +10.29%  (8 games, model CLV only, $0 P&L)
- R10: -2.69%  (3 actual bets, +$131.50)
- R11: +2.48%  (4 actual bets, -$13.00)
- 78.3% positive CLV rate

### 2. Model Accuracy folder — `data/model_accuracy/`

New script: `scripts/generate_model_accuracy.py`

Reads ml_comparison CLV files, extracts rules model vs ML shadow vs market close
for H2H / handicap / totals per game. Outputs per-round CSVs and a running summary.

Key findings (bias = rules_model - market_close):
- NRL H2H: rules overrates home teams consistently (+9–11%) — ML is better (+1–6%)
- NRL Handicap: rules overrates home margin (+8–9pts) — ML better (+2–5pts)
- NRL Totals: rules well calibrated (~0pts) — ML underestimates (-4 to -10pts)
- AFL Totals: both models underprice vs market (-8 to -25pts — known systematic bias)

Files created:
- `data/model_accuracy/nrl/NRL_MODEL_ACCURACY_R09_2026-04-28.csv`
- `data/model_accuracy/nrl/NRL_MODEL_ACCURACY_R10_2026-05-05.csv`
- `data/model_accuracy/nrl/NRL_MODEL_ACCURACY_R11_2026-05-12.csv`
- `data/model_accuracy/afl/AFL_MODEL_ACCURACY_R08_2026-05-05.csv`
- `data/model_accuracy/afl/AFL_MODEL_ACCURACY_R09_2026-05-12.csv`
- `data/model_accuracy/MODEL_ACCURACY_RUNNING_2026.csv`

To add a new round: add a line to `SOURCES` in `generate_model_accuracy.py` pointing
at the new ml_comparison CSV, then rerun.

### 3. Pricing folder — `data/pricing/`

New script: `scripts/convert_pricing_files.py`

Converts all txt pricing outputs to CSV and copies/renames all existing pricing CSVs
into a clean folder with consistent naming.

Files created:
```
data/pricing/nrl/
  NRL_PRICING_R09_2026-04-28.csv            (full T1-T8 rules model)
  NRL_PRICING_R09_2026-04-28_tier_breakdown.csv
  NRL_PRICING_R09_2026-04-28_ml_shadow.csv
  NRL_PRICING_R10_2026-05-05.csv
  NRL_PRICING_R10_2026-05-05_ml_shadow.csv
  NRL_PRICING_R11_2026-05-12.csv
  NRL_PRICING_R11_2026-05-12_ml_shadow.csv
  NRL_PRICING_R12_2026-05-25.csv

data/pricing/afl/
  AFL_PRICING_R07_2026-04-28.csv            (T1+T2 only, early engine)
  AFL_PRICING_R07_2026-04-28_t1t2t3t4.csv  (T1-T4+T5 version)
  AFL_PRICING_R08_2026-05-05.csv            (full T1-T7)
  AFL_PRICING_R09_2026-05-12.csv
  AFL_PRICING_R11_2026-05-25.csv
```

---

## Naming conventions (canonical, going forward)

All output files follow `{SPORT}_{TYPE}_R{rr:02d}_{YYYY-MM-DD}[_suffix].csv`

| Type | Suffix options |
|------|---------------|
| CLV | `_ml_comparison`, `_ml_shadow`, `_rules_vs_ml`, `_manual` |
| PRICING | `_ml_shadow`, `_tier_breakdown`, `_t1t2t3t4` |
| MODEL_ACCURACY | (none — one file per round) |

Weekly bets: `YYYY-MM-DD_AFL-R{rr}_NRL-R{rr}.csv` in `data/bets/weekly/`

---

## Weekly pipeline (updated sequence)

**Monday** — bet results come in
- Add to `data/bets/weekly/YYYY-MM-DD_AFL-RXX_NRL-RXX.csv`
- Append to `data/bets/actual_bets_2026.csv`

**Tuesday** — pipeline day (automation fires + pricing)
- Opening/closing lines arrive → fill `data/clv/nrl/` and `data/clv/afl/`
- Run `uv run python scripts/update_clv_running.py` → updates running CLV
- Run `uv run python scripts/generate_model_accuracy.py` → updates accuracy running file
- Run `scripts/run_nrl_pricing.ps1` → new round priced
- Run `uv run python scripts/convert_pricing_files.py` → landing in `data/pricing/`

---

## What's next

- R12 CLV: opening/closing lines not yet available — fill in when ready, rerun scripts
- AFL totals bias: both rules and ML consistently underprice vs market — T1 expected-points review needed
- NRL H2H home bias: rules model consistently overrates home teams — may need T4 venue calibration
- ML shadow incorporation decision: ML better for NRL H2H and handicap, rules better for totals — accumulate full season before deciding
