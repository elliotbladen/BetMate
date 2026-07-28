# World Cup 2026 Semifinal — England vs Argentina

Wed Jul 15, Mercedes-Benz Stadium, Atlanta — neutral venue, ~320m altitude (no adjustment, same house treatment as Kansas City ~270m in the QF).

Model: Dixon-Coles Poisson from ELO, tactical multipliers, T5 absences, T7 knockout motivation.

## ELO chain

- England: 1986 -> R32 1992 (beat DR Congo 2-1) -> R16 2005 (beat Mexico 3-2) -> QF 2020 (beat Norway 2-1 AET)
- Argentina: 2078 -> R32 2082 (beat Cape Verde 3-2 AET) -> R16 2087 (beat Egypt 3-2) -> QF 2097 (beat Switzerland 3-1 AET)

## Fair odds (90 minutes)

| Market | England | Draw | Argentina |
|---|---:|---:|---:|
| Probability | 27.2% | 29.5% | 43.3% |
| Fair odds | 3.67 | 3.4 | 2.31 |

## Totals

- Over 2.5: 46.9% @ 2.13
- Under 2.5: 53.1% @ 1.88

## Advance to Final (inc. ET/pens)

- England: 41.2% @ 2.43
- Argentina: 58.8% @ 1.7
- Pens split if 90min draw: England 47.4% / Argentina 52.6%

## Most likely scorelines

1-1 (14.1%), 0-1 (9.7%), 0-0 (9.4%), 1-2 (9.0%), 0-2 (8.2%), 1-0 (7.0%), 2-1 (6.9%), 2-2 (5.0%), 2-0 (4.8%), 1-3 (4.3%), 0-3 (3.9%), 3-1 (2.5%).

## T5 — Absences / data risk

- England: Jarell Quansah serving the 2nd match of an extended 2-game suspension (red card vs Mexico). Jordan Henderson out for the rest of the tournament (broken wrist) — squad depth, not a first-choice starter, minor impact. Reece James is fit again (was out for the QF) — a real defensive upgrade on the QF price. Ezri Konsa has a hamstring cramp scare from the Miami heat, being monitored — treated as a doubt. Net defensive absence eased to +0.03 (from +0.06 at the QF).
- Bukayo Saka is fit but managed on minutes by Tuchel (impact-sub role) — no attack penalty applied; he changed the Norway game after coming on at half-time.
- Argentina: no confirmed injuries or suspensions. Lautaro Martinez avoided a second yellow for a celebration incident vs Switzerland, and FIFA's post-QF yellow-card amnesty resets bookings regardless — fully available. Messi in career-best tournament form (8 goals). No adjustment.

## T7 — Motivation

- England +0.01: first World Cup semifinal since 1990 (Italia '90), significant historic weight but standard knockout-focus treatment.
- Argentina +0.02: defending champions, Messi's likely last World Cup, historic rivalry intensity (1986/1998/2002/2022 meetings) — judgment value, kept modest per house convention on motivation edges.

## Market check (web-sourced 2026-07-15, opening lines)

- Bookmaker 90-min: England ~+155 (2.55 decimal) / Argentina ~+205 (3.05 decimal).
- Bookmaker advance (inc. ET/pens): England ~56% / Argentina ~44%.
- Opta supercomputer 90-min simulation: England 38.2% / Draw 29.7% / Argentina 32.0%.
- **This model disagrees with the market, not just diverges slightly.** 90-min England win probability here is 27.2% vs Opta's 38.2% and the market-implied ~39.2% (1/2.55) — an 11-12pt gap. The advance number (41.2% England / 58.8% Argentina) has Argentina as the clear favourite where the market leans England. Driver: Argentina started the tournament ~90 ELO points above England and its knockout path (Cape Verde/Egypt/Switzerland) added more ELO than England's (DR Congo/Mexico/Norway) under the house K=40, no-MOV convention. This is an honest model output, not a validated edge — the WC engine has no CLV or closing-line track record (see Assumptions below). Do not stake against the market on this alone.
- UNDER 2.5 is the market favourite on the total; this model's split is 53.1% under / 46.9% over, directionally consistent.

## Assumptions / risk flags

- ELO chain uses house K=40 convention, no margin-of-victory or home-advantage scaling. Extra-time win counts 1.0; penalty shootout counts 0.5 (draw). Opponents taken at post-group baseline, not chained through their own knockout games (matches every prior WC script in this repo).
- SF pressure tier (0.007) applied instead of the QF's 0.004, per `knockout_context.py`'s `PRESSURE_EDGE_BY_ROUND` — a small bump reflecting greater composure variance at this stage.
- Mercedes-Benz Stadium (Atlanta, ~320m) is not in `VENUE_CONTEXT` — treated as negligible altitude, same as Kansas City (~270m) in the QF; consider adding both if more games get priced at these venues.
- Neutral venue; crowd will skew mixed given both fanbases travel well, no crowd adjustment applied (house convention: crowd only priced for host-nation games).
- This WC engine is a light ELO/Dixon-Coles model with no CLV or closing-line validation history — same caveat flagged on every prior WC output this tournament. Treat as directional, not a proven edge.
- Re-run this script if Konsa is ruled out (bump def_b back toward +0.05) or if either camp names a confirmed team news update before kickoff (19:00 local Jul 15).