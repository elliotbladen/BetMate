# Expected Tempo Engine — Step 4 live replay

Date: 3 September 2026
Status: shadow research; no horse-price integration

## Design

The replay reconstructs each meeting in race order. Race 1 receives V0. Before
Race 2, only Race 1 may update the meeting state; before Race 3, only Races 1–2
may contribute, and so on. Every stored forecast has a V-number equal to the
number of races already completed on that card.

Earlier races are weighted by distance similarity, recency and sectional
coverage. A change in official going starts a new evidence regime: observations
from Good receive zero weight once the target race is Heavy, for example.
All meeting-state estimates shrink toward neutral when evidence is limited.

The evaluation contains 872 chronological out-of-fold races, of which 738 had
at least one relevant earlier race under the same going.

## Four-way probabilities on live-eligible races

| Forecast | Log loss | Brier | Accuracy | Calibration ECE |
|---|---:|---:|---:|---:|
| Original V0 | 1.2334 | 0.6713 | 43.63% | 0.0271 |
| Full live replacement | 1.2748 | 0.6898 | 42.68% | 0.0682 |
| Conservative live blend | **1.2298** | **0.6699** | **44.31%** | **0.0217** |

The conservative live blend improves log loss by 0.29% and Brier by 0.22%
versus V0. Its permitted live weight was selected strictly inside each training
window. It won the first and third test periods but lost the middle period, so
the probability updater remains shadow-only. A full live replacement clearly
fails and must not be used.

## Continuous pace scores

| Target | V0 MAE | Live MAE | Change |
|---|---:|---:|---:|
| Early | **1.0889** | 1.1126 | 2.18% worse |
| Middle | 1.1136 | **0.9780** | 12.18% better |
| Late | 1.0587 | **0.9138** | 13.69% better |

Earlier races contain strong information about how the middle and late phases
will run on the day. They do not currently improve prediction of field-driven
early pressure. This supports keeping the horse/map-driven early-tempo forecast
largely at V0 while allowing the live surface state to influence middle and
late expectations.

## Decision

- Preserve V0 as the anchor.
- Never replace V0 outright with the live classifier.
- Retain the conservatively blended probabilities in shadow.
- Allow Step 5 safeguards to consider middle/late live updates.
- Do not allow an early-score update until it demonstrates improvement.
- Do not modify horse prices yet.

The output is evidence that the meeting updater is learning surface/meeting
behaviour rather than reliably predicting the next field's early tactical
pressure.
