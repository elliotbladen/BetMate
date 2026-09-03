# Saved 20%+ EV selections — results and flat-stake ROI

Graded: 2 September 2026  
Stake convention: one unit per saved selection  
Return convention: saved decimal price; losing bet returns zero

## EPL Week 2

| Match | Selection | Price | Score | Result | P/L |
|---|---|---:|---:|---|---:|
| Sunderland v Fulham | Fulham win | 3.46 | 1–0 | Loss | -1.00 |
| Leeds v Brentford | Brentford win | 2.94 | 1–1 | Loss | -1.00 |
| Bournemouth v Everton | Everton win | 3.85 | 1–1 | Loss | -1.00 |
| Tottenham v Newcastle | Newcastle win | 3.32 | 0–2 | **Win** | **+2.32** |
| Aston Villa v Arsenal | Aston Villa win | 6.50 | 0–1 | Loss | -1.00 |
| Tottenham v Newcastle | Over 2.5 | 1.769 | 0–2 | Loss | -1.00 |

All six literal saved rows:

- Bets: 6
- Wins: 1
- Stakes: 6.00 units
- Returns: 3.32 units
- Profit: **-2.68 units**
- ROI: **-44.67%**

The five 1X2 rows alone returned -1.68 units from five stakes: **-33.60% ROI**.
The single goals bet lost: **-100% ROI**.

The Aston Villa 6.50 row was explicitly saved as `price_verification_required`.
The Tottenham Over 2.5 row was explicitly saved as
`matrix_verification_required`. Excluding those two leaves the four ordinary
saved EPL rows: one win, -0.68 units, **-17.00% ROI**.

## EFL Championship Week 3

| Match | Selection | Price | Score | Result | P/L |
|---|---|---:|---:|---|---:|
| Norwich v Burnley | Burnley win | 2.83 | 4–1 | Loss | -1.00 |
| Wrexham v Birmingham | Wrexham win | 2.38 | 1–2 | Loss | -1.00 |
| Charlton v Preston | Preston win | 3.45 | 1–0 | Loss | -1.00 |

- Bets: 3
- Wins: 0
- Stakes: 3.00 units
- Returns: 0.00 units
- Profit: **-3.00 units**
- ROI: **-100.00%**

All three were genuinely frozen selections. However, their saved notes say the
final matrix qualification was not preserved. They can be graded as the saved
20%+ EV list, but should not be retrospectively described as proven +6
net-matrix qualifiers.

## Combined literal saved list

- Bets: 9
- Wins: 1
- Stakes: 9.00 units
- Returns: 3.32 units
- Profit: **-5.68 units**
- ROI: **-63.11%**

## Interpretation

This was a poor weekend for the high-EV shortlist. Draws defeated three EPL
away-win selections, and every Championship selection lost. The result is only
nine bets and is not sufficient to reject the model, but it is strong evidence
against treating very large displayed EV as automatically trustworthy.

The next report should compare the frozen probabilities with no-vig closing
probabilities and separate:

1. genuinely preserved matrix-qualified bets;
2. EV-only selections;
3. price- or matrix-verification rows; and
4. normal-engine versus player-shadow outputs.

No actual staking claim is made: these are flat one-unit returns at the saved
prices, not confirmation that the bets were placed.
