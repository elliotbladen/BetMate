# EPL normal engine versus player shadow

Date: 31 August 2026

## Operating decision

Keep the EPL normal engine and player shadow completely separate.

- Only probabilities and EV produced by the **normal production engine** may qualify a live bet.
- The **player shadow** is comparison and evaluation only. It must not create, approve, rescue or increase the stake of a bet.
- Matrix evidence may be applied only to a candidate first produced by the normal engine, under the agreed EV and matrix filters.
- If the normal engine has negative EV but the player shadow has positive EV, the selection is **not a bet**.
- Record normal and shadow prices side by side after each round for calibration, accuracy and CLV comparison. Promotion requires a separate evidence-based decision after sufficient prospective results.

## Round-two implication

The Bournemouth v Everton Under 2.5 and BTTS No selections were positive only under the player shadow and therefore are excluded from the normal-engine betting list. Tottenham v Newcastle Over 2.5 was the saved goals-market candidate with at least 20% EV from the normal engine, subject to the separately agreed matrix rule.

## Week 2 result audit — 3 September 2026

The completed normal-versus-player-shadow probability, CLV and hypothetical ROI audit is saved at:

- `outputs/results/player_shadow_week2_2026-09-02.json`
- `outputs/results/player_shadow_week2_clv_roi_2026-09-03.md`
- `outputs/results/player_shadow_week2_clv_roi_2026-09-03.json`

Method: for each fixture and market, choose the side with the largest positive expected value at the Football-Data average opening odds and stake one hypothetical unit. CLV is `opening_odds / closing_odds - 1`. A second view applies the agreed 10% minimum EV rule.

Findings:

- The shadow improved broad 1X2 probability scores in EPL and Championship Week 2.
- At the strict 10% EV threshold, normal and shadow produced exactly the same 1X2 portfolios and therefore identical CLV and ROI. Shadow added no actionable benefit under the betting rule.
- EPL shadow totals had positive CLV but negative realised ROI in a four-bet sample.
- Championship shadow totals materially worsened: 10 positive-edge candidates returned -80.9% opening ROI and -0.9% mean CLV. At 10% EV, five bets returned -61.8% ROI.
- Do not promote the shadow. Keep it comparison-only, especially for O/U 2.5 and BTTS.
- These are retrospective hypothetical portfolios, not an actual placement ledger, and the one-round samples are far too small for promotion decisions.

## Two-week CLV benchmark — 3 September 2026

Across the 32 saved filtered EPL/EFL selections, the mixed-rule preliminary portfolio is +2.96 units (+9.25% ROI). Mean saved/reference-price CLV is +2.15%, but the more defensible consistent Football-Data open-to-close market movement is +0.53% because Week 1 EFL lacks independent placement prices and some references came from different books.

Across the broader 84-bet all-model test, weighted mean CLV is +1.72%: +1.70% for 1X2 and +1.74% for O/U 2.5.

The filtered portfolio's model probability edge against the de-vigged opening market is +10.2 percentage points (Week 1 +8.9pp; Week 2 +13.6pp). Treat this as theoretical model disagreement, not CLV. The much smaller realised closing-market confirmation means probability overconfidence remains a live calibration concern.
