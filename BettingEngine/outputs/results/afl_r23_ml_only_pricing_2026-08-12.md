# AFL R23 2026 — ML-only price sheet

Raw XGBoost outputs, generated 12 August 2026. No rules-engine price and no
T2–T7 overlay is included. Handicap is shown from the margin model; H2H odds
come from the separate ML win-probability classifier.

| Date | Match | ML margin | ML H2H (home / away) | ML total |
|---|---|---:|---:|---:|
| 14 Aug | Fremantle Dockers v Adelaide Crows | Fremantle -4.8 | 1.84 / 2.19 | 163.9 |
| 15 Aug | Brisbane Lions v Gold Coast Suns | Brisbane -45.7 | 1.56 / 2.78 | 170.7 |
| 15 Aug | Hawthorn Hawks v Collingwood Magpies | Hawthorn -9.0 | 1.80 / 2.25 | 172.2 |
| 15 Aug | North Melbourne Kangaroos v Geelong Cats | Geelong -22.9 | 3.78 / 1.36 | 167.1 |
| 15 Aug | Port Adelaide Power v Melbourne Demons | Port Adelaide -0.9 | 2.12 / 1.89 | 163.2 |
| 15 Aug | Richmond Tigers v St Kilda Saints | St Kilda -44.2 | 1.97 / 2.03 | 164.5 |
| 16 Aug | Essendon Bombers v Sydney Swans | Sydney -38.6 | 11.74 / 1.09 | 169.6 |
| 16 Aug | Greater Western Sydney Giants v West Coast Eagles | GWS -51.6 | 1.11 / 9.89 | 177.2 |
| 16 Aug | Western Bulldogs v Carlton Blues | Western Bulldogs -12.6 | 1.70 / 2.43 | 148.3 |

The Richmond–St Kilda models disagree sharply: the margin model has St Kilda
by 44.2, while the independent H2H classifier gives Richmond 50.8%. Treat that
game as an ML conflict, rather than combining it with any rules-based signal.
