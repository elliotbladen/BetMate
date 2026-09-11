# Cards over/under 3.5 — Championship GW7, 11-13 Sep 2026 (REFEREES CONFIRMED)

Appointments pulled from the FotMob match API (`/api/data/matchDetails`), which carries
the referee once the EFL publishes. efl.com itself is a JS shell that will not render
server-side, Transfermarkt still shows "Referee: Unknown", and ESPN only fills the
official in at kickoff. Steve Martin (Preston/Lincoln) independently confirmed via
The Stacey West preview.

League baseline 2022/23-2026/27: **3.78 cards/game, over 3.5 in 53.4%.** Cards are
yellows only — football-data's red-card columns are empty for this league.

## Method

Referee and team card rates are both **shrunk toward the league mean** by their own
sample noise (between-referee true spread tau = 0.366 cards/game, against within-referee
noise of 0.366 — so roughly half of a referee's raw deviation survives, far more than
the 1-16% that survives on the goals side, because cards genuinely persist: r=+0.42,
p=0.0001 across 80 referee-season pairs).

Expected match cards `lambda = ref_cards_pg x team_cards_pg / league_mean`, then
Poisson. Poisson was checked against the actual card distribution first and fits within
1pp at every line (o2.5 .735/.729, o3.5 .534/.523, o4.5 .336/.329, o5.5 .177/.182).

## The two bets

| | | |
|---|---|---|
| **OVER 3.5 — Preston v Lincoln (S Martin)** | **59.9%** | **beat 1.67** |
| **UNDER 3.5 — Charlton v Portsmouth (A Kitchen)** | **59.7%** | **beat 1.68** |

Both edges come almost entirely from the referee, on fixtures that are ordinary on team
profile — which is the right way round, because the referee is the half that repeats.

* **S Martin** — 95 Championship games, 4.21 cards/g shrunk, 63% over 3.5. Deep sample,
  strongest card referee working this round.
* **A Kitchen** — 80 games, 3.25 cards/g shrunk, 39% over 3.5. Equally deep sample at
  the opposite end.

## All 12

| fixture | referee | games | ref c/g | ref o3.5 | team c/g | lambda | P(o3.5) | BE over | BE under |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Preston v Lincoln | S Martin | 95 | 4.21 | 63% | 3.74 | 4.17 | **59.9%** | **1.67** | 2.49 |
| Watford v Stoke | L Smith | 52 | 3.63 | 46% | 4.10 | 3.92 | 55.2% | 1.81 | 2.23 |
| Sheffield United v Wolves | R Jones | 12 | 3.85 | 58% | 3.85 | 3.91 | 54.9% | 1.82 | 2.22 |
| West Brom v QPR | R Ricardo | 27 | 4.02 | 59% | 3.68 | 3.90 | 54.7% | 1.83 | 2.21 |
| West Ham v Wrexham | M Donohue | 112 | 3.98 | 61% | 3.68 | 3.87 | 54.1% | 1.85 | 2.18 |
| Blackburn v Millwall | J Smith | 101 | 3.81 | 62% | 3.71 | 3.74 | 51.4% | 1.95 | 2.06 |
| Southampton v Bristol City | S Allison | 63 | 3.69 | 56% | 3.83 | 3.73 | 51.2% | 1.95 | 2.05 |
| Middlesbrough v Norwich | A Herczeg | 33 | 3.74 | 52% | 3.77 | 3.73 | 51.1% | 1.96 | 2.05 |
| Swansea v Burnley | J Bell | 66 | 3.64 | 50% | 3.85 | 3.70 | 50.5% | 1.98 | 2.02 |
| Bolton v Cardiff | T Parsons | **0** | — | — | 3.66 | 3.66 | 49.8% | 2.01 | 1.99 |
| Derby v Birmingham | J Busby | 97 | 3.66 | 46% | 3.76 | 3.64 | 49.2% | 2.03 | 1.97 |
| Charlton v Portsmouth | A Kitchen | 80 | 3.25 | 39% | 3.76 | 3.22 | 40.3% | 2.48 | **1.68** |

## What changed once the referees were known

**Watford v Stoke is no longer the pick.** On team profile alone it was the standout
(4.22 expected cards, both clubs running hot). It drew **Lewis Smith**, a below-average
card referee — 46% over 3.5 across 52 games — and that pulls the fixture back to 55.2%.
This is the referee-over-fixture effect working exactly as the matrix said it would:
the spread across referees (39%-63% this round) is wider than the spread across fixtures.

**Two fixtures are not priceable on referee.** T Parsons has **zero** Championship
matches in the five-season window (National Group referee), so Bolton v Cardiff falls
back to the league mean and carries no referee signal at all — no bet. R Jones has only
12, so Sheffield United v Wolves is thin and its 54.9% should not be trusted to the
decimal.
