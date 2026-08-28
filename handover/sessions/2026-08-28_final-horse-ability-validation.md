# Final Horse Ability validation handover

Date: 2026-08-28

Implemented `racing_engine/horse_ability_final_v2.py` and locked model
`horse-ability-v2.8-final-research-freeze`.

Frozen configuration: responsive four-run state, 90-day half-life, 25% peak
blend, 1.5-run reliability prior, 10% trajectory; 25% initial handicap response;
effective-dated collateral revisions; no campaign decay; no distance/going
base adjustment; probability temperature 60.

Validation (876 races) improves log loss versus rejected V2 by 0.01866, V1 by
0.00464 and uniform by 0.01144. Historical holdout (835 races) improves against
all three. The validation interval versus V1 crosses zero, so this is a final
research freeze rather than production promotion.

Named chronological audits all pass. Natural Fling achieved 104.22/current
99.67. Sheza Alibi achieved 116.24 versus Gringotts 112.37 and current initial
ability is 110.83 versus 110.28. Retrospectively revised current ratings are
Gringotts 110.87 and Sheza Alibi 110.83 and remain separately labelled.

Next task: one-year untouched Betfair backtest. Lock the date interval, Betfair
price timestamp/type, commission, value threshold and staking rule before
examining profit. Prices are comparator/execution evidence only; ratings remain
the sole model input.
