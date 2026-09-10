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
