# World Cup 2026 FINAL — Spain vs Argentina

Sun Jul 19, MetLife Stadium, East Rutherford NJ — neutral venue, sea level.

Model: Dixon-Coles Poisson from ELO, tactical multipliers, T5 absences, T7 knockout motivation.

## ELO source — CORRECTED 2026-07-16

Earlier WC scripts in this engine (including the first draft of this Final and the England/Argentina semifinal) chained ELO from `data/elo_ratings.py`, a hand-maintained file that was never actually verified against real eloratings.net data — it had Argentina ~94 points above Spain pre-tournament. Fact-checked against two independent sources and it does not hold up: eloratings.net direct (Jul 7, mid-tournament) had **Spain 2177 (#1) ahead of Argentina 2151 (#2)**; blog.recommend.games, citing eloratings.net from Jun 10 (day before kickoff), had **Spain a 35.3% tournament win probability vs Argentina's 23.0%** — Spain the clear pre-tournament favourite by real Elo, not Argentina.

- Spain: **2232** (world #1, eloratings.net direct, current as of 2026-07-16, post-semifinal)
- Argentina: **2177** (world #2, eloratings.net direct, current as of 2026-07-16, post-semifinal)
- Gap: Spain +55 — reverses the earlier chained-ELO draft, which had Argentina ahead by ~66 using the internal engine's unverified baseline.

## Fair odds (90 minutes)

| Market | Spain | Draw | Argentina |
|---|---:|---:|---:|
| Probability | 40.2% | 29.9% | 29.8% |
| Fair odds | 2.48 | 3.34 | 3.35 |

## Totals

- Over 2.5: 46.3% @ 2.16
- Under 2.5: 53.7% @ 1.86

## Lift the trophy (inc. ET/pens)

- Spain: 55.9% @ 1.79
- Argentina: 44.1% @ 2.27
- Pens split if 90min draw: Spain 52.4% / Argentina 47.6%

## Most likely scorelines

1-1 (14.3%), 0-0 (9.6%), 1-0 (9.3%), 2-1 (8.7%), 0-1 (7.6%), 2-0 (7.5%), 1-2 (7.3%), 0-2 (5.3%), 2-2 (5.0%), 3-1 (4.0%), 3-0 (3.5%), 1-3 (2.8%).

## T5 — Absences / data risk

- Spain: no fresh injury news for the final. Pre-tournament doubts (Yamal hamstring, Merino stress fracture, Nico Williams hamstring) all resolved or squad-managed weeks ago. Spain have conceded once in the entire tournament and are unbeaten in 37 straight games — essentially full strength. No adjustment.
- Argentina: Cristian "Cuti" Romero has carried a partial MCL tear since a group-stage knock (R2 vs Austria), came off at halftime of extra time vs Switzerland (QF) exhausted, but played through the England semifinal with no reported withdrawal — treated as a managed knock, not a confirmed absence. Small opponent-facing defensive adjustment applied (def_b +0.02). Lisandro Martinez is the ready deputy if Romero doesn't start. Messi has no fitness concerns and played every minute of the quarterfinal.

## T7 — Motivation

- Spain +0.01: first World Cup final since 2010, riding a 37-game unbeaten run — historic weight, standard knockout-focus treatment per house convention.
- Argentina +0.02: defending champions going for back-to-back titles, Messi's likely last World Cup — judgment value, kept modest per house convention on motivation edges.

## Market check (web-sourced 2026-07-16, opening lines)

- Bookmaker 90-min: Spain ~5/4 (2.25 decimal) / Argentina ~5/2 (3.50 decimal).
- Bookmaker to lift the trophy: Spain -156 (~1.64 decimal, ~58% implied) / Argentina +136 (~2.36 decimal, ~43% implied) — Kalshi has it at a similar 58/43 split.
- **This model now agrees with the market on the favourite (Spain), after correcting the ELO input.** 90-min: Spain 40.2% vs market-implied ~44.4% (1/2.25) — same side, model a touch less bullish on Spain. Champions market: Spain 55.9% here vs the market's ~58%; Argentina 44.1% here vs the market's ~43% — closely aligned once the real eloratings.net figures (Spain 2232, Argentina 2177, current as of 2026-07-16) replaced the flawed internal `elo_ratings.py` baseline that had Argentina ~66 points ahead post-knockout. That earlier number drove both the first draft of this Final and the England/Argentina semifinal pricing — this correction should be read back onto that SF writeup too.
- Squawka's own prediction (Spain 2-1 Argentina) now points the same direction as this model's favoured side, for what that's worth as one more data point.

## Assumptions / risk flags

- **ELO input corrected 2026-07-16** — see the ELO source section above. The rest of the engine (Dixon-Coles pricing, T2 tactical multipliers, T5/T7 adjustments, pressure tier) is unchanged and uses the same house K=40 convention as every prior WC script for context, but Spain/Argentina's actual ratings are now sourced directly from eloratings.net rather than derived from it.
- Final pressure tier (0.010) applied per `knockout_context.py`'s `PRESSURE_EDGE_BY_ROUND` — the largest pressure/composure edge of the tournament, reflecting maximum stakes.
- MetLife Stadium (East Rutherford, NJ) is sea-level and neutral for both sides — no altitude or host-nation adjustment. Crowd will likely skew heavily Argentine (as it did in the semifinal) but the model does not price crowd for non-host nations, per house convention.
- This WC engine is a light ELO/Dixon-Coles model with no CLV or closing-line validation history. The ELO-source bug found and fixed here (internal baseline file never verified against the real site it claimed to be based on) likely also affected every earlier WC price in this tournament that used `elo_ratings.py` — worth a full audit before trusting any of the QF/SF writeups' exact numbers, even though the QF picks themselves (Norway/England, Argentina/Switzerland) happened to land on the right side.
- Re-run this script if either camp names a confirmed team news update before kickoff (3:00pm ET Jul 19).