# NRL 2026 H2H Diagnosis and 2027 Plan

## Conclusion

The NRL H2H loss was caused by both bet selection and model pricing, but pricing was the larger problem. Sensible staking and removing multis or unsupported bets would have improved the overall NRL result. However, betting only H2H selections showing at least 10% model EV would not have made the price-complete H2H sample profitable.

## Published H2H evidence

BetMate published 34 settled pre-match NRL H2H bets:

- Record: 15 wins and 19 losses.
- Result: -4.49 units.
- Nineteen bets stored both a contemporaneous model fair price and taken odds.
- Fifteen later bets have no saved model price, largely during the period when the odds/market feed was unavailable. Their EV must not be reconstructed using later information.

On the 19 price-complete bets:

| Model-EV filter | Bets | Record | Flat P&L | Flat ROI | Average price CLV |
|---|---:|---:|---:|---:|---:|
| All price-complete H2H | 19 | 8-11 | -4.23u | -22.3% | -3.0% |
| EV >= 0% | 15 | 7-8 | -2.08u | -13.9% | +1.8% |
| EV >= 5% | 14 | 7-7 | -1.08u | -7.7% | +3.7% |
| EV >= 10% | 11 | 5-6 | -1.62u | -14.7% | +3.0% |
| EV >= 20% | 6 | 2-4 | -2.02u | -33.7% | +3.2% |

Therefore a minimum 10% EV rule alone did not solve H2H. The increasingly poor result at very large stated EV is a warning that extreme edges often represented model overconfidence rather than exceptional market value.

A retrospective 10%-to-25% EV band went 5-4 and made approximately +0.38 flat units. This is useful evidence for an extreme-edge veto, but it is only nine bets and the upper bound was inspected after results were known. It is not a validated betting system and must be tested prospectively.

## Primary technical cause

The rules engine converts expected margin to H2H probability using:

`P(home win) = normal_cdf(expected_margin / margin_std_dev)`

The production configuration uses `margin_std_dev: 12.0`. This makes probabilities extremely confident. The newer NRL ML margin work uses an out-of-sample residual scale closer to 18 points and derives H2H probability from that measured error distribution.

Illustration:

| Expected favourite margin | Probability with scale 12 | Fair price | Probability with scale 18 | Fair price |
|---|---:|---:|---:|---:|
| 12 points | 84.1% | $1.19 | 74.8% | $1.34 |
| 24 points | 97.7% | $1.02 | 90.9% | $1.10 |

The 2026 round archives contain very short rules prices such as Panthers $1.03 from a 23.7-point margin and Warriors $1.02 from a 26.1-point margin. Those prices leave too little allowance for NRL upset variance, team-list uncertainty, Origin effects and model error. When the bookmaker offered a much larger price, the system could report enormous EV even when the model—not the market—was wrong.

Early model-accuracy reports also identified a rules-model home bias. Across NRL Rounds 9-11, rules H2H probabilities overrated the home side by approximately 8-11 percentage points. Contextual tiers changed expected margin, but the final H2H conversion treated that adjusted margin as more precise than the evidence justified.

## 2027 H2H rebuild

1. Use predicted margin as the single source of truth for handicap and H2H.
2. Estimate the margin-error distribution strictly out of sample with rolling seasonal folds; remove the fixed 12-point assumption.
3. Test whether uncertainty should vary by expected margin, favourite status, Origin period, venue type, team-list certainty and finals state.
4. Calibrate margin-derived probabilities on a disjoint period and assess Brier score, log loss and reliability diagrams—not winner accuracy alone.
5. Compare three frozen candidates: rules-margin probability, coherent ML-margin probability and a conservative model/no-vig-market blend.
6. Promote only a candidate that improves calibration and closing-price performance across multiple time-split samples.

The first NRL ML classifier disagreed with its margin model in 79 of 426 games (18.5%). BetMate has already corrected the architecture so margin is the source of truth. The margin-derived method improved walk-forward winner accuracy from 61.03% to 62.68% and Brier score from 0.2316 to 0.2313. It remains a challenger until the historical closing-price coverage is repaired and prospective evidence accumulates.

## Proposed 2027 betting policy

- Minimum auditable model EV: 10%.
- EV above 25%: anomaly/manual-review flag, not an automatic larger stake.
- Pass when rules and ML nominate different winners.
- Pass when the H2H price and fair handicap are incoherent.
- Pass when critical team-list, market or timestamp data is missing.
- Use quarter Kelly with a hard bankroll cap and a combined exposure cap per match.
- Exclude multis and winning-margin bets from the model bankroll.
- Store discretionary bets in a separate ledger and grade them independently.

The 10% minimum and 25% review ceiling are proposed rules. They must be frozen and tested prospectively; the small retrospective 10%-to-25% result is insufficient for promotion.

## Required data repair

Before the 2027 season, recover contemporaneous prices for later 2026 rounds only from timestamped saved artefacts. Do not substitute closing prices or regenerated model outputs. Every future prediction must store match ID, model/config hash, prediction time, data cutoff, rules and ML margins, calibrated probabilities, bookmaker/no-vig market probability, taken price, stake, close, result and whether the bet was model-led or discretionary.

