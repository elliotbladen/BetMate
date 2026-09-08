# Player shadow review — EPL GW3 (4–6 Sep 2026)

**Reviewed:** 2026-09-08 · **Driver:** `scripts/player_shadow_round_review.py`  
**Prices:** `1_model.json` (`normal` and `shadow` blocks, frozen 2026-09-03, pre-round)  
**Market:** football-data consensus averages, de-vigged  
**Betting:** 1u on each engine's best-EV side at the OPENING price, held to the close,
so ROI and CLV are like-for-like between the two engines.

Shadow status in the source file: `comparison_only_projected_last_xi` — it is a
comparison layer, not a production engine, and did not create any bet.

## Accuracy — lower is better

| Metric | Shadow | Normal | Market | Best |
|---|---:|---:|---:|:--|
| 1X2 RPS | 0.1536 | **0.1503** | 0.1508 | NORMAL |
| 1X2 log loss | 1.0890 | 1.0890 | **1.0728** | MARKET |
| 1X2 Brier | 0.6545 | 0.6531 | **0.6516** | MARKET |
| O/U log loss | **0.6952** | 0.7053 | 0.7448 | SHADOW |

## Betting — 10 notional picks per market

| Measure | Shadow | Normal |
|---|---:|---:|
| 1X2 P&L | -10.00u | -8.31u |
| 1X2 ROI | **-100.00%** | -83.10% |
| 1X2 avg CLV | +1.61% | +1.43% |
| O/U P&L | +3.77u | +3.00u |
| O/U ROI | **+37.70%** | +30.00% |
| O/U avg CLV | +1.04% | **+4.05%** |

Shadow picked differently from normal on **2/10** 1X2 games and **3/10** O/U games.

## Per match

| Match | Score | Shadow RPS | Normal RPS | Market RPS | 1X2 picks (S/N) | O/U picks (S/N) |
|---|---:|---:|---:|---:|:--|:--|
| Ipswich v Liverpool | 0-2 | 0.1402 | 0.1229 | 0.1048 | H/H | O/U |
| Newcastle v Bournemouth | 2-2 | 0.1528 | 0.1541 | 0.1427 | A/A | O/O |
| Brentford v Sunderland | 1-1 | 0.1501 | 0.1530 | 0.1767 | A/A | U/O |
| Brighton v Leeds | 1-1 | 0.1415 | 0.1499 | 0.1505 | A/A | O/O |
| Fulham v Crystal Palace | 2-3 | 0.3983 | 0.3737 | 0.3534 | H/H | O/O |
| Man City v Coventry | 1-0 | 0.0187 | 0.0227 | 0.0236 | D/A | U/U |
| Nott'm Forest v Tottenham | 0-0 | 0.1322 | 0.1372 | 0.1297 | H/H | U/O |
| Hull v Aston Villa | 0-0 | 0.1416 | 0.1386 | 0.1527 | H/H | O/O |
| Everton v Man United | 2-2 | 0.1421 | 0.1453 | 0.1556 | H/H | O/O |
| Arsenal v Chelsea | 2-1 | 0.1186 | 0.1057 | 0.1186 | A/H | O/O |

## Read

**The shadow's one clear win is totals.** It beat both the normal engine and the
market on O/U log loss (0.6952 vs 0.7053 vs 0.7448) and returned +37.70% against
the normal engine's +30.00%. That is the second week running the totals side of the
shadow has looked like the better layer.

**On 1X2 it was worse than normal and worse than the market.** RPS 0.1536 against
normal's 0.1503 and the market's 0.1508, and every one of its ten 1X2 picks lost
(-100% ROI vs normal's -83.10%).

**But the two engines barely disagreed.** Shadow changed only 2 of 10 1X2 picks and
3 of 10 O/U picks, so almost all of the difference above rests on a handful of games.
Ten matches, two differing picks — this is far too little to promote or reject the
shadow on, and it should stay a comparison layer.

**CLV is the one place normal is clearly ahead on totals** (+4.05% vs the shadow's
+1.04%), which is worth noting because the shadow won the same market on accuracy
and ROI. Price capture and probability quality are pulling apart there.

## EFL Championship GW5 — no review possible

**No shadow prices were produced for that round.** The GW5 `1_model` artefact does
not exist at all (`price_efl_week4_2026.py` prints to stdout), and no shadow run was
made. The Championship player-shadow model exists
(`ml/football/data/championship/player_layer/player_shadow.joblib`) but
`scripts/compare_championship_player_shadow.py` is hardcoded to GW1 dates, and the
5–6 Sep match feeds are not in the cache (0 of 1,534 feeds reference those dates).

I have not reconstructed shadow prices after the fact. Generating them now would be
a retrospective fit, not a frozen pre-round forecast, and the project's governance
treats those as different things. To have an EFL shadow review next round: fetch the
GW6 feeds, generalise the compare script off its hardcoded GW1 window, and run it
**before** the round.
