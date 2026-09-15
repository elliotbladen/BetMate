# EPL 2026/27 — Gameweek 5 model prices

**Built:** 2026-09-15 · Fixtures 18–20 Sep · Engine: `ml/football/price_match.py` via
`scripts/price_epl_week5_2026.py` · Market: Odds API (uk), best available, 2026-09-15

Data is current: `fetch_results.py --league epl --live-merge` pulled GW4 this session
(30 → 40 rows for 2026/27), and **xG coverage is 40 of 40** — football-data now supplies
`HxG`/`AxG` for every 2026/27 match.

## Prices

| fixture | λ home–away | P(H) | P(D) | P(A) | fair H/D/A | P(O2.5) | fair O / U |
|---|---|---|---|---|---|---|---|
| Brentford v Chelsea | 1.82–2.29 | 39.0% | 23.4% | 37.7% | 2.57 / 4.28 / 2.65 | **77.8%** | 1.29 / 4.50 |
| Tottenham v Aston Villa | 1.76–1.62 | 41.5% | 24.8% | 33.7% | 2.41 / 4.04 / 2.97 | 63.9% | 1.56 / 2.77 |
| Brighton v Arsenal | 1.35–1.90 | 27.7% | 24.3% | 48.0% | 3.61 / 4.12 / 2.08 | 58.5% | 1.71 / 2.41 |
| Everton v Ipswich | 1.95–1.01 | 55.9% | 24.4% | 19.7% | 1.79 / 4.09 / 5.09 | 52.2% | 1.92 / 2.09 |
| Newcastle v Hull | 2.58–1.21 | 58.9% | 21.3% | 19.8% | 1.70 / 4.70 / 5.06 | **67.3%** | 1.48 / 3.06 |
| Nott'm Forest v Coventry | 1.64–1.06 | 49.7% | 26.8% | 23.5% | 2.01 / 3.73 / 4.26 | 50.5% | 1.98 / 2.02 |
| Bournemouth v Liverpool | 1.95–2.13 | 33.7% | 23.2% | 43.0% | 2.96 / 4.30 / 2.32 | **77.8%** | 1.29 / 4.50 |
| Leeds v Crystal Palace | 1.91–1.51 | 46.9% | 24.8% | 28.3% | 2.13 / 4.03 / 3.54 | **67.3%** | 1.48 / 3.06 |
| Man City v Sunderland | 2.31–0.72 | 68.2% | 20.0% | 11.8% | 1.47 / 5.00 / 8.49 | 54.3% | 1.84 / 2.19 |
| Fulham v Man United | 1.69–1.84 | 35.3% | 24.5% | 40.3% | 2.84 / 4.08 / 2.48 | **67.3%** | 1.48 / 3.06 |

## ⚠️ Fault 1 — the O/U 2.5 calibrator is quantised, and it is visible on this slate

Ten fixtures produce **seven distinct P(Over) values**. `77.8%` appears twice and
`67.3%` **three times** — Newcastle v Hull, Leeds v Palace and Fulham v Man United all
price at an identical fair 1.48 despite λ totals of 3.79, 3.42 and 3.53.

This is the documented EPL isotonic-calibrator fault (quantised, censored above raw
~0.77) and it means **O/U selections cannot be ranked against each other.** Rank on the
raw λ column, not on the calibrated price.

## ⚠️ Fault 2 — the model still runs high on totals

```
model mean P(Over 2.5)      63.7%
de-vigged market mean       57.5%
                            +6.2pp HIGH
```

The documented GW4 figure was +10.2pp (0.661 vs 0.559), so the gap has narrowed — real
xG now covers 40 of 40 matches, where before the spine was on the `FTHG × 0.85` fallback.
**It has not closed.** Every positive Over EV on this slate inherits that bias.

## ⚠️ Fault 3 — three fixtures involve promoted clubs

`Everton v Ipswich`, `Newcastle v Hull` and `Nott'm Forest v Coventry`.
`_reset_new_team_dc_ratings` sets a club new to the division to exact league average
(att = def = 1.00) and discards its current-season results. T8, the ClubElo prior built
for this, is **disabled for EPL** (`epl.yaml` has no `t8_decay_games`).

Note the Championship got a fix for this on 2026-09-15 — `new_team_reset_1x2: elo_seeded`,
better in 10 of 10 seasons. **EPL did not.** It still runs `league_average` on both
markets. Porting it is the single highest-value change available to this engine.

## Tier coverage

| tier | state |
|---|---|
| D-C + Elo spine | ✅ current through GW4, full xG |
| T2 pressing | ⚠️ `get_ppda` has no recency guard (documented) |
| T3 rest | ✅ |
| T5 injuries | ⚠️ **PARTIAL — 6 clubs audited, 12 unaudited** (see 2_bets.md) |
| T6 referee | ❌ not injected |
| T8 ClubElo prior | ❌ disabled for EPL |
| player shadow | ❌ not run — ESPN XI feeds not refreshed for GW5 |
