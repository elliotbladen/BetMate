# World Cup 2026 Quarterfinal — Argentina vs Switzerland

Sat Jul 11, Kansas City Stadium (Arrowhead) — neutral venue, ~270m altitude (no adjustment).

Model: Dixon-Coles Poisson from ELO, tactical multipliers, T5 absences, T7 knockout motivation.

## ELO chain

- Argentina: 2078 -> R32 2082 (beat Cape Verde 3-2 AET) -> R16 2087 (beat Egypt 3-2)
- Switzerland: 1875 -> R32 1887 (beat Algeria 2-0) -> R16 1887 (0-0 Colombia, won 4-3 pens = ELO draw)

## Fair odds (90 minutes)

| Market | Argentina | Draw | Switzerland |
|---|---:|---:|---:|
| Probability | 55.2% | 26.8% | 18.0% |
| Fair odds | 1.81 | 3.73 | 5.56 |

## Totals

- Over 2.5: 48.1% @ 2.08
- Under 2.5: 51.9% @ 1.93

## Advance to SF (inc. ET/pens)

- Argentina: 70.1% @ 1.43
- Switzerland: 29.9% @ 3.34
- Pens split if 90min draw: Argentina 55.4% / Switzerland 44.6%

## Most likely scorelines

1-1 (12.8%), 1-0 (11.2%), 2-0 (10.9%), 2-1 (9.7%), 0-0 (8.9%), 3-0 (6.2%), 3-1 (5.5%), 0-1 (5.2%), 1-2 (5.0%), 2-2 (4.3%), 0-2 (3.0%), 4-0 (2.6%).

## T5 — Absences / data risk

- Argentina: effectively fully fit. Medina's R32 knock was cramps/exhaustion, not structural. No suspensions (yellow accumulation resets at the QF; no reds in either knockout game). No adjustment.
- Switzerland: Johan Manzambi (knee) ruled out of the R16 with no update since — treated as out. Breel Embolo subbed off vs Colombia with a possible injury — doubt (-0.02). Silvan Widmer (hip/thigh) bench-only since the group stage (+0.02 defensive absence). Aebischer, Sow and Vargas all carrying knocks after 120 minutes — flagged, not separately priced.
- Re-price: atk_b=-0.02 if Embolo and Manzambi are both passed fit; atk_b=-0.05 if both are confirmed out.

## T7 — Motivation

- Switzerland +0.02: first World Cup quarterfinal since 1954 — historic underdog energy.
- Argentina +0.01: defending champions, experienced knockout side; Messi on 8 tournament goals.

## Assumptions / risk flags

- ELO chain uses house K=40 convention, no margin-of-victory or home-advantage scaling. Extra-time win counts 1.0; penalty shootout counts 0.5 (draw). Opponents taken at post-group baseline, not chained through their own knockout games (matches the Norway/England QF script).
- Both teams last played Jul 7 (equal calendar rest), but Switzerland went 120 minutes plus a shootout while Argentina finished in 90. Recovery tier held neutral per house convention (RECOVERY_EDGE_BY_ROUND has no verified input layer) — the Swiss price is therefore the optimistic end of the range.
- Kansas City Stadium is not in VENUE_CONTEXT (~270m — negligible, no altitude adjustment). Neutral venue for both; crowd will skew heavily Argentine but the model does not price crowd for non-host nations.
- Re-run this script when Switzerland's matchday squad news lands (Embolo/Manzambi).