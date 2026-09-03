# NFL Step 5 — 2025 vault result

## Permanent status

The 2025 vault was frozen, predicted and opened exactly once on 31 August 2026
(Brisbane time). Models trained through 2024 only. The label-free file contained
272 predictions and was hashed before scores or markets were attached. Staking
remained disabled. This result must be recorded without retrospective tuning.

## Core result

| Margin predictor | Games | MAE | RMSE |
|---|---:|---:|---:|
| Ridge structural candidate | 272 | 10.162 | **12.978** |
| Shallow-tree shadow | 272 | **10.137** | 13.014 |
| QB/continuity oracle shadow | 272 | 10.343 | 13.063 |
| Opening spread | 253 | 9.747 | 12.351 |
| Closing spread | 190 | 9.768 | 12.136 |

The tree improves ridge MAE by only 0.026 points and again worsens RMSE. This is
not enough for promotion. The personnel oracle is worse than the core, so its
historical Step 3 development gain did not survive the vault.

Opening and closing spread coverage differs. On the same 190 games, opener MAE
was 10.011 and close MAE was 9.768; opener RMSE was 12.337 and close RMSE was
12.136. The closing line retained a modest advantage.

## Totals

| Total predictor | Games | MAE | RMSE |
|---|---:|---:|---:|
| Ridge | 272 | 10.609 | **13.387** |
| Shallow-tree shadow | 272 | 10.688 | 13.500 |
| Opening total | 253 | 10.605 | 13.727 |
| Closing total | 253 | **10.518** | 13.659 |

The ridge total is competitive with the opener on MAE but does not beat the
closing total. The tree adds no value.

## Head-to-head probabilities

| Source | Brier | Log loss | Accuracy |
|---|---:|---:|---:|
| Margin-derived | 0.2230 | 0.6362 | 65.81% |
| Direct classifier shadow | 0.2282 | 0.6485 | 61.76% |
| Closing market | **0.2084** | **0.6014** | **67.19%** |

Margin-derived H2H again beats the direct classifier and remains authoritative.
The market remains better calibrated and more accurate.

## Opening-line diagnostic

The tree was closer to the close than the opener in only 49 of 166 non-push
comparisons (29.52%) and was 0.99 points farther from the close on average. It
did record mean directional CLV of +0.49 points, but that did not translate into
a reliable spread result.

At a predeclared three-point model edge, the ridge produced 56 wins and 47
losses on 103 available opening-spread rows: 54.37% and synthetic ROI +3.80% at
assumed -110. This is **not an accepted profit result**. Exact historical spread
prices were unavailable, opener definitions remain unaudited, and the threshold
cannot be selected after viewing the vault. It is retained only as a diagnostic
for future frozen paper tracking.

## Decision

- Keep ridge as the explainable structural paper candidate.
- Keep the tree independent and shadow-only.
- Reject promotion of the direct H2H and personnel oracle models.
- Do not blend models and do not stake.
- Do not tune against 2025.
- Begin timestamped 2026 paper predictions and require at least 500 frozen
  prospective predictions plus positive CLV before any promotion review.

