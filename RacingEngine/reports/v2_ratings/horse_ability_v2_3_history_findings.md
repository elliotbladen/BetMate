# Horse Ability V2.3 history/trajectory findings

Date: 28 August 2026  
Version: `horse-ability-v2.3-history-trajectory-shadow`  
Decision: **strongest candidate; not promoted**

## Training-only selection

Four predeclared state families were compared on 979 training races. Named
horses and their ordering were not fit targets. `responsive` won with training
log loss 2.34089: four-run window, 90-day half-life, 0.25 sustainable-peak
blend, 1.5 reliability-prior runs and 0.10 bounded trajectory blend.

## Evaluation

| Period | Candidate | vs rejected V2 | vs V1 | vs uniform |
| --- | ---: | ---: | ---: | ---: |
| Validation | 2.33020 | -0.01704 | -0.00302 | -0.00982 |
| Historical holdout | 2.32221 | -0.00458 | -0.01271 | -0.01856 |
| Observed prospective diagnostic | 2.23442 | -0.04383 | -0.04313 | -0.01505 |

Negative deltas favour V2.3. It is the first Horse Ability candidate to improve
headline log loss over every baseline in validation and historical holdout.
Promotion still fails because the validation paired interval versus V1 includes
zero. The prospective set is only 19 already-observed races.

## Named audit

- Sheza Alibi: **110.83**.
- Gringotts: **112.51**.

The gap narrows from V2.2's 4.56 points to 1.68 but the direct WFA ordering
still fails. Their latest achieved figures are correct at 116.24 versus 112.37.
The remaining reversal comes from Gringotts' deeper history, especially his
118.85 Doncaster handicap run despite finishing more than six lengths behind
Sheza. Audit that handicap weight response before another state-family change.

## Top ten achieved performances, three-year database

1. Via Sistina 132.13 — 2024 Cox Plate, won 8.0L.
2. Antino 128.70 — Caulfield G1, won 6.5L.
3. Pride Of Jenni 128.01 — Randwick G1, won 6.54L.
4. Pride Of Jenni 124.10 — Flemington G1, won 4.5L.
5. Sir Delius 123.36 — Randwick G1, won 2.21L.
6. Imperatriz 123.32 — The Valley G1, won 3.25L.
7. Globe 122.41 — Caulfield G1, won 3.0L.
8. Jigsaw 121.88 — Caulfield open race, won 3.5L carrying 61 kg.
9. Ceolwulf 121.34 — Flemington G1, won 0.06L.
10. Pericles 121.18 — same Flemington G1, second by 0.06L.

The broad hierarchy is plausible: seven of the top ten are G1 winners and the
same-race Ceolwulf/Pericles figures are coherent. Jigsaw's 121.88 open-race
figure and the size of some handicap weight components require a focused audit.
