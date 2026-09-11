# Pre-registration — single-use vault test of the market-anchored O/U 2.5 rule

**Frozen:** 2026-09-10, **before** the 2025/26 result was computed or inspected.
**Branch:** `research/efl-totals-vault-test`
**Runner:** `ml/football/backtest/efl_totals_market_anchored.py --mode vault`

This document exists so the vault result cannot be rationalised after the fact.
Everything below is fixed. If the test fails, it fails.

## The rule

| Element | Frozen value |
|---|---|
| Sharp anchor | de-vigged **Betfair Exchange** opening (`BFE>2.5`/`BFE<2.5`), falling back to de-vigged **Pinnacle** (`P>2.5`/`P<2.5`) where BFE is absent. Match skipped if neither exists. |
| Model | `LogisticRegression(max_iter=2000)`, default L2, on `[logit(anchor), logit(dc_raw)]` |
| `dc_raw` | production Dixon-Coles raw P(Over 2.5), from the isolated vault walk-forward (`clv_vault/backtest_results.csv`) |
| Training seasons | **2022/23, 2023/24, 2024/25** — no vault data, ever |
| Execution price | best available opening, `Max>2.5` / `Max<2.5` |
| Bet rule | for each side, `p_side * best_price - 1 >= 0.03` → stake **1u flat** |
| Sides | both Over and Under |
| CLV | `taken_price / closing_consensus (AvgC) - 1` |
| **PASS** | **ROI >= 0 OR CLV >= 0** (the user's bar: equal the line at worst) |

## Why this anchor, and why not the consensus

Measured on development seasons, same model and execution, only the anchor changed:

| Anchor | Bets | Strike | ROI | CLV |
|---|---:|---:|---:|---:|
| Pinnacle (sharp) | 243 | 47.3% | **+8.97%** | +2.00% |
| Consensus `Avg` | 330 | 41.2% | −3.91% | +2.93% |

De-vigging a consensus that contains soft books produces a worse probability
estimate than de-vigging a sharp book. Overrounds: Pinnacle 1.0342, consensus
1.0540, best-of-market 1.0169.

Betfair Exchange substitutes for Pinnacle: correlation **0.979**, mean absolute
difference **0.0062** (n=545, 2024/25). Held-out check, blend fitted on
2022/23+2023/24 only and applied to 2024/25:

| Anchor | Bets | Strike | ROI | CLV |
|---|---:|---:|---:|---:|
| Pinnacle | 75 | 60.0% | +17.41% | +2.81% |
| Betfair Exchange | 80 | 58.8% | +15.03% | +2.83% |

BFE is chosen because it is the only sharp anchor that still exists going forward
(Pinnacle: full through 2024/25 → 260/552 in 2025/26 → column absent in 2026/27).
A rule anchored on Pinnacle could pass the vault and still be undeployable.

## Known risks, stated in advance

1. **Search burden.** Roughly 30 configurations were examined before this one was
   frozen. That is exactly why a sealed hold-out is being spent.
2. **The likely mechanism is execution, not forecasting.** The blend weights are
   ~+0.98 on the market and ~+0.39 on the D-C model. Most of the edge probably comes
   from taking best-of-market price against a sharp de-vigged probability, i.e.
   harvesting book disagreement — not from the totals model having a view.
3. **Development ROI is uneven**: +6.8% (n=93), +7.1% (n=141), +17.4% (n=75).
4. **CLV is flattered** — best price versus consensus close is not pure timing edge.

## Commitment

The vault is run **once**. No re-runs with adjusted thresholds, anchors, side
filters or training windows. A FAIL closes the market-anchored line of work; a PASS
licenses reworking the model and re-pricing GW7, with the caveat in risk 2 carried
into any write-up.

---

# RESULT — run once, 2026-09-10, after the commit above

```
train 1653 rows (2022/23, 2023/24, 2024/25)  ->  test 514 rows (2025/26)
blend coefficients: anchor +0.9987   dc_raw +0.4727   intercept +0.0187

bets 203   104W-99L (51.2%)   43% Unders
P&L -11.76u   ROI -5.79%   CLV +2.87%
ROI 95% bootstrap CI [-18.32%, +6.89%]   P(ROI>0) 18.0%
```

## Verdict: technical PASS, substantive FAIL. Do not deploy.

The pre-registered bar was "ROI >= 0 **OR** CLV >= 0" and CLV is +2.87%, so the rule
passes as written. That bar was badly specified and the vault has exposed why:

**CLV is trivially positive here and carries no information.** It compares a
best-of-28-books price against the consensus close. That gap is the price shop, and it
is mechanically positive whatever the model does. Development CLV was +2.0% to +2.9%;
the vault returned +2.87%. It did not move, because it never depended on the model.
It should never have been allowed to satisfy the bar on its own.

**ROI, the number that matters, did not replicate.** Development gave +6.8% (n=93),
+7.1% (n=141) and +17.4% (n=75). The vault gave **-5.79%** over 203 bets. The
development edge was the product of ~30 searched configurations, exactly as risk 1
warned, and it did not survive contact with held-out data.

## How it failed

| | |
|---|---|
| Strike rate | 51.2% (104W-99L) — respectable |
| Average price taken | 1.847 |
| Average price needed to break even at that strike | **1.952** |
| Winners' average price | 1.839 |
| Losers' average price | 1.856 |
| Model mean probability | 0.5865 |
| Realised win rate | 0.5123 |
| **Overconfidence** | **+7.4 percentage points** |

It picked sides at a fair rate and paid too little for them. The blend is
systematically overconfident by 7.4pp, which is precisely the failure a market-anchored
model is supposed to be immune to — the `dc_raw` coefficient of +0.47 pulled it away
from the market often enough to matter, and in the wrong direction.

## Consequences

1. **The market-anchored line of work is closed**, per the commitment above. No re-runs
   with adjusted thresholds, anchors, side filters or training windows. No mining this
   result for a subset that worked.
2. **The vault is spent.** 2025/26 can no longer serve as a clean hold-out for
   Championship totals. Any future totals work needs a new sealed season — 2026/27
   is the obvious candidate once complete, and must not be looked at before then.
3. **The original probe verdict stands**: Championship O/U 2.5 has no signal beyond the
   market in the data we hold. Do not price it as a bettable market.
4. **Bar correction for future work: ROI is the bar.** CLV is only meaningful when the
   taken price and the reference price come from the same market. With best-of-market
   execution against a consensus close, CLV is an execution statistic, not evidence.

## What survives

The data repairs are real and worth keeping regardless: `Avg`/`AvgC`/`Max`/`MaxC`
totals odds restored for 2019/20-2025/26 (the local file had none before 2026/27), and
Betfair Exchange columns added to the fetcher as Pinnacle is retired from E1.

The measurement that a **sharp** de-vigged anchor beats a de-vigged consensus (47.3%
vs 41.2% strike on identical model and execution) also stands, and is worth carrying
into 1X2 work — where the model does at least have a live disagreement with the market.
