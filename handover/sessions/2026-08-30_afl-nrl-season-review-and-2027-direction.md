# AFL/NRL 2026 review and 2027 direction — 2026-08-30

## User decision

- Save the completed AFL/NRL review and the conclusions from this conversation.
- AFL needs a selective “half rebuild” informed by the EPL/NFL approach.
- Keep the good AFL components; do not throw away the entire system.
- NRL likely would have been materially more profitable with disciplined staking and without low-quality bets and multis.
- Proposed NRL rule for investigation and 2027 deployment: only bet when model EV is at least 10%.

## Correct review scope

The revised review uses every settled bet in BetMate's published model arrays in
`lib/researchData.ts`, rather than the incomplete mid-season cash/CLV extract:

- AFL: 105 settled published bets, 2026-04-15 through 2026-08-23.
- NRL: 96 settled published bets, 2026-03-19 through 2026-08-22.
- Results use the stored `plUnits` values.
- Combined result: +1.07 units (AFL -0.13u; NRL +1.20u).

## AFL findings and direction

- Standard pre-match markets: 102 bets, -3.30u.
- H2H: 28 bets, +1.12u.
- Handicap: 37 bets, -0.60u; 32 CLV records averaged -0.59 points with 43.8% positive.
- Totals: 37 bets, -3.82u; 30 CLV records averaged +0.60 points with 56.7% positive.
- Tiny live/multi sample added +3.17u and made the full page look almost flat; it is not evidence of a repeatable model edge.

2027 direction: retain useful AFL pipelines, contextual knowledge and the stronger rules totals candidate. Rebuild the H2H/handicap spine around a calibrated ML margin distribution, derive coherent H2H probabilities from it, and retain the frozen rules/ML blend as a shadow challenger. Use EPL/NFL-style immutable contracts, time-split tests, sealed holdout evaluation and explicit feature-promotion gates. Control correlated same-game exposure.

## NRL findings and direction

- Standard pre-match markets: 89 bets, +4.17u.
- H2H: 34 bets, -4.49u.
- Handicap: 29 bets, +3.58u; 26 CLV records averaged +0.88 points with 57.7% positive.
- Totals: 26 bets, +5.08u; 23 CLV records averaged +0.63 points with 56.5% positive.
- Multis lost -3.00u; margin and other specials further diluted the profitable handicap/totals core.

2027 direction: do not rebuild the NRL core. Freeze the rules handicap/totals champions, continue the coherent margin-derived ML H2H challenger, and rebuild the decision/staking layer. Proposed policy is model EV >=10%, no multis in the model bankroll, no unsupported bets, one match-level exposure cap, and a separate discretionary/entertainment ledger.

## Evidence caveat and required next test

Do not state that the EV >=10% rule definitely would have produced a particular historical profit yet. The public model records do not contain one consistent, point-in-time EV value for all 96 NRL bets. Before 2027:

1. Reconstruct pre-bet EV only where the contemporaneous model price and taken odds are available.
2. Report coverage and exclude missing rows rather than filling them with later prices.
3. Backtest thresholds (0%, 5%, 10%, 15%, 20%) on the same covered sample with flat stakes.
4. Freeze the chosen threshold before prospective testing.
5. Compare flat stake, quarter Kelly and capped quarter Kelly, including match-level exposure and drawdown.

## Canonical review

`research/afl_nrl_2026_season_review.md`

## NRL H2H follow-up

The detailed diagnosis is saved at
`research/nrl_2026_h2h_diagnosis_and_2027_plan.md`.

Key finding: a >=10% model-EV filter still lost on the 19 H2H bets with saved
point-in-time fair prices. The rules engine's fixed 12-point margin uncertainty made
H2H probabilities too confident. Recalibrate from out-of-sample margin residuals,
retain >=10% as a proposed minimum, and add an extreme-EV anomaly review rather than
assuming very large reported edges deserve larger stakes.
