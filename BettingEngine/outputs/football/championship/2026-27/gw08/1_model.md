# EFL Championship 2026/27 — Gameweek 8 model prices (1X2)

**Built:** 2026-09-15 · Fixtures 18–20 Sep · Script: `scripts/price_efl_week8_2026.py`
(successor to `price_efl_week7_normal_shadow_2026.py`, the newest Championship pricer)
**Engine:** Dixon-Coles + Elo spine via `ml/football/price_match.py`, full tier stack

## ⚠️ These prices are NOT comparable with GW7 — the 1X2 engine changed today

`new_team_reset_1x2: elo_seeded` was merged on **2026-09-15**. Clubs new to the division
are now seeded from Elo instead of being wiped to exact league average with their
current-season results discarded. It was better in **10 of 10** walk-forward seasons
(1.0366 against a 1.0554 baseline). **Totals deliberately stay on `league_average`** —
all three candidate modes made totals worse, so the split is per-market.

Confirmed in this run: `reset_mode_1x2 = elo_seeded`, `reset_mode_totals = league_average`.

## Data state

`fetch_results.py --league championship --live-merge` run first. football-data has now
published GW7, so the ESPN supplement rows added earlier this session are fully replaced
by official rows (`SourceSupp` 0). Fit covers **81 matches**, complete through 13 Sep.

Rounds 1–7 played. GW6 had three postponements, so six clubs arrive on 6 games and
eighteen on 7. `matchweek` is passed per fixture as games actually played, because T8's
prior weight is a per-team decay, not a calendar week.

## Prices — 1X2 at a 105% book

| fixture | mw | **H** | **D** | **A** | book | P(H) | P(D) | P(A) | λ H–A |
|---|---|---|---|---|---|---|---|---|---|
| Bristol City v Watford | 6 | **2.08** | **3.32** | **3.73** | 105.0% | 45.8% | 28.6% | 25.5% | 1.41–1.02 |
| Cardiff v Charlton | 7 | **2.82** | **3.07** | **2.70** | 105.1% | 33.7% | 31.0% | 35.3% | 1.33–0.94 |
| Millwall v West Ham | 6 | **2.86** | **3.21** | **2.57** | 105.0% | 33.3% | 29.7% | 37.0% | 1.25–1.11 |
| Stoke v Sheffield United | 7 | **2.56** | **3.25** | **2.84** | 105.0% | 37.2% | 29.3% | 33.5% | 1.24–1.19 |
| Birmingham v Middlesbrough | 6 | **2.93** | **3.58** | **2.33** | 105.0% | 32.6% | 26.6% | 40.8% | 1.33–1.63 |
| Portsmouth v Blackburn | 6 | **2.57** | **3.25** | **2.83** | 105.0% | 37.1% | 29.3% | 33.6% | 1.23–1.26 |
| Burnley v Derby | 7 | **1.87** | **3.67** | **4.13** | 104.9% | 51.0% | 26.0% | 23.1% | 1.44–1.22 |
| Lincoln v Swansea | 6 | **2.38** | **3.31** | **3.05** | 105.0% | 40.0% | 28.8% | 31.2% | 1.34–1.15 |
| QPR v Preston | 7 | **1.98** | **3.49** | **3.88** | 104.9% | 48.2% | 27.3% | 24.6% | 1.57–1.08 |
| Wrexham v Southampton | 7 | **2.84** | **4.00** | **2.24** | 104.9% | 33.6% | 23.8% | 42.6% | 1.70–2.01 |
| Wolves v West Brom | 6 | **2.06** | **3.33** | **3.77** | 105.1% | 46.2% | 28.6% | 25.3% | 1.36–1.06 |
| Norwich v Bolton | 7 | **1.74** | **3.81** | **4.67** | 105.1% | 54.6% | 25.0% | 20.4% | 1.78–1.13 |

Books land 104.9–105.1% from two-decimal rounding only.

## Six clubs are new to the division and run the new code path

`Cardiff`, `West Ham`, `Burnley`, `Lincoln`, `Wolves`, `Bolton` — all six trigger
`elo_seeded`. **Half the card is priced by a mode that has never run in production
before today.** Its walk-forward record is strong, but walk-forward is not live use.

## ⚠️ The draw tilt is present here too

```
mean model P(Draw)        27.8%
de-vigged market mean     25.5%
                          +2.3pp HIGH
```

EPL GW5 showed the same direction (model draw price shorter than market on nine of ten
fixtures). Two different leagues, same sign, which points at the shared spine rather
than at either fixture list. **The engine has no 1X2 calibrator** — `price_match.py`
fits an isotonic calibrator for totals only, and the 1X2 probabilities come straight
out of the scoreline matrix blended with Elo, uncalibrated. A draw tilt is the standard
signature of an uncalibrated Dixon-Coles.

## Tiers

| tier | state |
|---|---|
| D-C + Elo spine | ✅ current through GW7, 81 matches |
| new-team reset (1X2) | ✅ **elo_seeded** — new today |
| T2 PPDA (pressing) | ✅ fired 12/12 · ⚠️ `ppda_dated.csv` holds only matchweek-1 2026/27 rows and `get_ppda` has no recency guard, so these are stale pressing figures |
| T3 Form | ✅ fired 12/12 |
| T3 Rest | ➖ fired 0/12 — every club on 6–7 days, below the fatigue threshold |
| T5 injuries | ✅ **AUDITED** — 15 published absentees checked against appearance data, all 15 already in the ratings, so T5 correctly contributes 0. See `_supporting/gw08_t5_audit.json` |
| T6 referee | ❌ 0/12 — EFL had not published GW8 appointments |
| T7 Set-piece (corners) | ✅ fired 12/12 |
| T8 New-team ClubElo prior | ✅ fired 6/12 — only the new-to-division clubs; magnitudes are small (e.g. Cardiff λ −0.024, wt 0.53) |
| T9 New manager | ➖ fired 0/12 — configured (`t9_manager_adj: 0.07`), no changes this week |

**There is no T4 in the football engine** — the tier fields are T2, T3 (form and rest),
T5, T6, T7, T8, T9. T4 (venue) exists in the NRL engine, not this one.

So **four tiers contributed and four did not.** The adjustments that did fire are small:
across the card they move λ/μ by roughly ±0.05 xG. **Effectively these are Dixon-Coles +
Elo prices with a light pressing/form/set-piece dressing** — the spine is doing almost
all the work, which is worth knowing before reading any EV off them.

⚠️ **Bristol City, Lincoln, Middlesbrough and Millwall play a rearranged GW6 fixture on
15 Sep** (Bristol City v Lincoln, Middlesbrough v Millwall). That result is **not** in
this fit — those four clubs are priced one game short. Re-run after it lands.
