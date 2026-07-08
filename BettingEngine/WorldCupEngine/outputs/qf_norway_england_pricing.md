# World Cup 2026 Quarterfinal — Norway vs England

Sat Jul 11, Miami Stadium (Hard Rock Stadium) — neutral venue, sea level.

Model: Dixon-Coles Poisson from ELO, tactical multipliers, T5 absences, T7 knockout motivation.

## ELO chain

- Norway: 1889 -> R32 1901 (beat Ivory Coast 2-1) -> R16 1924 (beat Brazil 2-1)
- England: 1986 -> R32 1992 (beat DR Congo 2-1) -> R16 2005 (beat Mexico 3-2)

## Fair odds (90 minutes)

| Market | Norway | Draw | England |
|---|---:|---:|---:|
| Probability | 30.4% | 29.8% | 39.7% |
| Fair odds | 3.29 | 3.35 | 2.52 |

## Totals

- Over 2.5: 46.8% @ 2.14
- Under 2.5: 53.2% @ 1.88

## Advance to SF (inc. ET/pens)

- Norway: 44.6% @ 2.24
- England: 55.4% @ 1.81
- Pens split if 90min draw: Norway 47.6% / England 52.4%

## Most likely scorelines

1-1 (14.3%), 0-0 (9.5%), 0-1 (9.1%), 1-2 (8.7%), 1-0 (7.6%), 2-1 (7.4%), 0-2 (7.4%), 2-0 (5.4%), 2-2 (5.1%), 1-3 (4.0%), 0-3 (3.4%), 3-1 (2.9%).

## T5 — Absences / data risk

- Norway: fully fit squad, no injuries or suspensions (Ryerson recovered). No adjustment.
- England: Reece James (hamstring, out since R32), Tino Livramento (calf, replaced pre-tournament), Jarell Quansah (suspended for QF — red card vs Mexico, on top of the ankle knock that cost him R32). Djed Spence is the only specialist cover and was undercooked coming off the bench vs Mexico. Defence absence bumped to +0.06 (from +0.05 at R32) — the position has degraded, not recovered.
- Bukayo Saka: Achilles doubt, subbed early vs Mexico. Treated as a doubt (-0.02 attack), not confirmed out. Re-price with atk_b=0.00 if passed fit, or -0.04 if ruled out.

## T7 — Motivation

- Norway +0.02: first-ever World Cup quarterfinal in the federation's history — underdog energy.
- England +0.01: experienced knockout side, standard tournament focus.

## Assumptions / risk flags

- ELO chain uses house K=40 convention (matches group-stage methodology in `elo_ratings.py`), no margin-of-victory or home-advantage scaling.
- Miami Stadium is sea-level and neutral for both sides — no altitude or host-nation adjustment (contrast with England's Azteca altitude game against Mexico).
- Re-run this script if Saka's fitness is confirmed either way before matchday.