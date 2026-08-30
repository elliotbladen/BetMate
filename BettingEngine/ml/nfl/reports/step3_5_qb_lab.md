# NFL Step 3.5 — Deep quarterback shadow

## Cost decision

The first build uses nflverse-hosted FTN charting and costs USD $0. PFF+ is the
cheapest plausible paid research addition at USD $119.99 annually (or $24.99
monthly), with CSV exports but no subscription API. NFL+ Premium is cheaper at
USD $99.99 annually but is a viewing and analysis product, not a licensed model
feed. SIS and Genius/Next Gen Stats require commercial quotes.

No paid subscription was purchased.

## What was built

The QB laboratory adds Bayesian, prior-game-only posteriors for catchable passes,
interception-worthy decisions, QB-fault sacks, out-of-pocket play, blitz
exposure, play action, motion, throwaways and created receptions. The store has
1,087 regular-season games from 2022–2025. Evaluation used 544 games from
2023–2024, while the 2025 vault remained untouched.

| Shadow | Margin MAE | RMSE | MAE to close |
|---|---:|---:|---:|
| Core | **10.37** | **13.44** | **2.87** |
| Core + basic QB | 10.50 | 13.51 | 2.94 |
| Core + FTN | 10.47 | 13.51 | 3.27 |
| Core + basic QB + FTN | 10.58 | 13.60 | 3.29 |
| Core + shuffled FTN | 10.38 | 13.46 | 3.30 |

## Decision

The detailed FTN bundle is not promoted. It made both game-result and
closing-spread predictions worse. This does not prove every advanced QB field is
useless; the history is short and correlated rate features can overwhelm a
small sample. It does prove that more detail is not automatically more signal.

The code and data remain available for prospective 2026 collection. A stable
provider-neutral adapter defines identity, accuracy, decision, pressure and
context fields for a future PFF CSV or SIS API sample. Any paid trial must be
tested as a frozen one-family ablation and beat both the core and shuffled
control before renewal.

## Artefacts

- `ml/nfl/qb_lab.py`
- `data/nfl/features/qb_lab_ftn.parquet`
- `data/nfl/predictions/step3_5_qb_lab.csv`
- `ml/nfl/reports/step3_5_qb_lab.json`
- 18 architecture tests passing
