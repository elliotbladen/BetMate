# 2026-09-11 — Championship referee matrix, and the cards market it found

**Branch:** `research/efl-totals-vault-test` (still open, uncommitted at time of writing)

## What was built

A **referee-centric** confluence matrix for the Championship, the transpose of the
existing team workbook (which carries referees only as "Barnsley when A Davies referees",
n=5). One sheet per referee, 51 sheets, 2021/22–2024/25.

| file | what |
|---|---|
| `scripts/efl_championship_referee_matrix.py` | builds the workbook |
| `outputs/football/_reference/efl_championship_referee_goals_matrix.xlsx` | 51 referee sheets |
| `scripts/_referee_matrix_viewer.py` | renders the same data as a local HTML page |
| `outputs/football/_reference/referee_matrix_viewer.html` | the viewer (served on :8777) |
| `scripts/efl_cards_weekend.py` | **the weekly job** — fixtures+refs from FotMob, ranked bets |

Sections mirror the team workbook (day of week, month, moon phase, price band, team)
plus referee-specific ones: kickoff slot, referee's own rest, team rest, market totals
band, season. Extra columns: Goals/game, Fouls/game, Cards/game, plus `$1 OVER ROI` /
`$1 UNDER ROI` (flat stake at best closing price) and `Cards o3.5 %` / `Cards BE odds`.

## The finding that matters

**Referee O/U 2.5 goals edge does not exist. Referee card tendency does.**

Same test, same referees, same seasons, 80 referee-season pairs:

```
goals edge vs closing price, year over year:   r = +0.08   (CI -0.12 to +0.29)
cards per game,              year over year:   r = +0.42   p = 0.0001
```

The goals half is noise by every measure taken: 1,309 cells produced 69 at p<0.05 where
chance predicts ~65 (**ratio 1.05x**), and **zero** survive Benjamini-Hochberg at q=0.10.
A power check by planting effects of known size showed an 8pp between-referee spread
would have been caught in 99% of simulations — so this is evidence of absence at any
size worth betting, though a 2-5pp effect could exist unseen and would not be harvestable.

⚠️ **A claim was corrected mid-session:** the between-referee spread estimator returns
1.99pp, and that was initially reported as the true spread. It sits at the **66th
percentile of its own null** (p=0.34; the estimator returns 1.46pp on data with no effect
at all). Consistent with zero. The README and viewer were rewritten to say so.

Also corrected: an apparent **negative** split-half correlation (r=-0.59 on 16 referees)
that survived a placebo test and looked like real reversal. It vanished on the proper
pooled design (80 pairs, r=+0.08). Small-sample fluke, not a mechanism.

## Noise control now in the workbook

- **Empirical-Bayes shrinkage** on every cell. `Over edge pp (shrunk)` keeps only the
  share of an edge not explicable as noise: n=10 keeps 1.6%, n=30 4.5%, n=119 15.8%.
  S Allison's headline −20.0pp becomes **−1.25pp**; a 5-game cell at 0% overs becomes
  −0.38pp. The raw column stays beside it.
- **FDR flags, not percentage points.** The team workbook's ±7.5pp rule lit 58% of these
  cells because referee cells are half the size of team cells.
- Cards shrinkage is far gentler (tau 0.366 cards/g against within-referee noise of
  0.366, so ~half a referee's deviation survives) — because cards genuinely persist.

## First bets placed

`scripts/efl_cards_weekend.py --start 2026-09-11 --end 2026-09-13 --round 7`

| bet | selection | referee | model p | odds | stake |
|---|---|---|---|---|---|
| **2026-0118** | Preston v Lincoln, Over 3.5 cards | S Martin (95g, 63%) | 0.599 | 1.85 | $25 |
| **2026-0119** | Charlton v Portsmouth, Under 3.5 cards | A Kitchen (80g, 39%) | 0.597 | 1.85 | $25 |

EV +10.8% / +10.4%. Bootstrapped, the Preston bet has a **21% chance of being −EV**
(S Martin's 95 games only pin his rate to ±13pp); Charlton is the better bet at 64.3%
with a 3% chance of being −EV. `market_type: cards` was added to `log_actual_bet.py`
so booking bets never pool with goals totals in the CLV reports.

Method: referee and club card rates shrunk, combined as
`lambda = ref_cpg x team_cpg / league_mean`, then Poisson — validated against the actual
card distribution first, fits within 1pp at every line (o2.5 .735/.729, o3.5 .534/.523,
o4.5 .336/.329, o5.5 .177/.182).

## Data sources learned

- **Referee appointments: FotMob** `https://www.fotmob.com/api/data/matchDetails?matchId=`
  carries the referee as soon as the EFL publishes. This is the only working route.
  efl.com is a Nuxt SPA returning a 7KB shell to every URL (curl and WebFetch alike),
  Transfermarkt shows "Referee: Unknown" until kickoff, ESPN fills it in only at kickoff,
  worldreferee/footballwebpages/11v11 all 403 or 404. Fixture list from
  `.../api/data/matches?date=YYYYMMDD`, English Championship is `ccode ENG`.
- **Cards odds:** the Odds API DOES carry `alternate_totals_cards` /
  `alternate_spreads_cards` — but **not for the Championship**. Zero books across
  uk/eu/au. EPL returns Pinnacle 1.80/2.02 (5.1% margin), MyBookie, and Betfair at a
  34.7% overround (i.e. no exchange liquidity). Pinnacle covers Championship (league
  1977 on their guest API) but does not price its cards.
- **The Odds API carries no Asian bookmaker at all** — 63 books across uk/eu/au/us, none
  of SBOBET/IBC/188Bet/MaxBet. Do not treat its coverage as "the market"; that mistake
  was made once this session and had to be retracted.
- Pinnacle's guest API (`guest.api.arcadia.pinnacle.com`) exposes leagues, matchups and
  markets but **zeroes the `limit` field** for unauthenticated requests, EPL included.
  Real limits are only visible in a logged-in betslip.

## Open

1. **Settle 2026-0118 / 2026-0119** once football-data publishes the 12-13 Sep round
   (`HY`/`AY`), then `log_actual_bet.py settle --bet-id ... --result win|loss`.
2. **Nothing is committed.** Whole session sits in the working tree.
3. **Local server** `python3 -m http.server 8777` still running on the viewer directory.
4. **Worth building:** the same cards matrix for the **EPL**, where Pinnacle actually
   prices the market — that gives a live price to measure real EV and CLV against,
   instead of the break-even-odds proxy the Championship version has to use.
5. `ephem` was installed into the BettingEngine venv (moon-phase rows); it was already a
   project dependency, just absent on this machine.
