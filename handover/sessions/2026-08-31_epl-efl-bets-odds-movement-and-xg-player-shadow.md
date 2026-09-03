# Session handover — EPL/EFL bets, odds movement and xG player shadow

Date: 31 August 2026

## Football betting-engine rule

Keep the normal production engine and player shadow separate.

- Only the normal engine may generate live bets.
- Player-shadow prices are comparison/evaluation only.
- A positive player-shadow EV cannot create, approve, rescue or increase a bet.
- Matrix evidence is a separate confirmation layer and must not be confused
  with player-shadow agreement.

Detailed rule:
`BettingEngine/handover/sessions/2026-08-31_epl-normal-vs-player-shadow-betting-rule.md`

## Saved football selections

EPL Week 2:

- Fulham to beat Sunderland at 3.46, normal EV +57.03%.
- Brentford to beat Leeds at 2.94, normal EV +49.10%.
- Everton to beat Bournemouth at 3.85, normal EV +39.25%.
- Newcastle to beat Tottenham at 3.32, normal EV +35.47%.
- Aston Villa to beat Arsenal at a later comparison price of 6.50,
  normal EV +82.55%; price availability/source requires verification because
  the earlier saved price was 3.51 and negative EV.
- Tottenham v Newcastle Over 2.5 at 1.769, normal EV +24.50%; final matrix
  qualification requires verification.
- No EPL BTTS bet was saved.

Files:

- `BettingEngine/outputs/football/epl/gw2_bets_2026-08-31.md`
- `BettingEngine/outputs/football/epl/gw2_bets_2026-08-31.csv`

EFL Championship Week 3:

- Burnley to beat Norwich at 2.83, normal EV +71.60%.
- Wrexham to beat Birmingham at 2.38, normal EV +34.20%.
- Preston to beat Charlton at 3.45, normal EV +20.70%.
- No price-verified normal-engine O/U 2.5 or BTTS selection exceeded 15% EV.

Files:

- `BettingEngine/outputs/football/championship/gw3_bets_2026-08-31.md`
- `BettingEngine/outputs/football/championship/gw3_bets_2026-08-31.csv`

These files record requested selections, not proof of placement. Confirm actual
bookmaker, obtainable price, stake and placement time before grading.

## EPL monthly draw finding

The initial October conclusion used an incomplete closing-price feature sample
ending in 2023/24. Rechecking the complete match/odds archive through 2025/26
showed October is not a durable draw month.

For calendar years 2021–2025, September was the clearest recent pattern:

- 149 matches;
- 27.5% draws versus 23.8% de-vigged market expectation;
- +3.7 percentage-point residual;
- +8.6% flat Bet365 draw ROI; and
- profitable draw betting in four of five Septembers.

September is a confirmation feature only, not an automatic system. October,
May and November should not receive positive month-only draw support from the
recent sample. Rebuild the matrix using the complete archive before relying on
month evidence.

## AFL/NRL odds snapshots

Logs prove a rich multi-bookmaker snapshot dataset was collected from 18 July
through 22 August 2026:

- 1,306 successful writes;
- 36 distinct dates;
- frequent intraday captures;
- H2H, handicap and totals lines/prices.

This is not full-season dense coverage. Earlier rounds have scattered CLV and
model-versus-market checkpoints. Collection stopped after 22 August following
API exhaustion/authorization failures. The raw CSV archive was written on the
Mac and is not present in the current Windows checkout. Recover and preserve
`/Users/elliotbladen/BetMate/data/odds_snapshots/2026/`.

Agreed next-season direction:

- resume monitored collection before Round 1;
- build closing-line, movement-direction and entry-timing models;
- evaluate EV-to-CLV conversion;
- keep fundamental pricing, market forecasting and bet decisions separate;
- use chronological match-level splits, never random snapshot-row splits;
- apply the NFL-style point-in-time player-availability and promotion gates;
- rebuild AFL's margin/H2H spine;
- retain the NRL core while repairing H2H calibration and staking discipline.

Research and forward decision:

- `research/afl_nrl_odds_movement_ml_and_next_season_plan.md`
- `handover/sessions/2026-08-31_afl-nrl-odds-movement-forward-direction.md`

## xG plus player-shadow architecture

The EPL normal engine is already xG-fed. The proposed combined shadow therefore
uses post-match xG to update team attack/defence strength and uses the player
layer only to estimate how the upcoming lineup differs from the reference
lineup already implicit in that strength.

Core flow:

```text
completed-match xG
  -> point-in-time team strength
  -> base lambdas
  -> reference lineup versus upcoming lineup
  -> centred, bounded player delta
  -> shadow lambdas
  -> one Dixon–Coles matrix
  -> shadow 1X2, O/U and BTTS prices
```

Do not add player xG/xA directly to team lambda. Train the player component on
residual adjusted xG after the frozen base, retain separate early and confirmed
lineup snapshots, and audit overlap with the current recent-form tier.

Compare four frozen candidates: normal production, refreshed team-xG base,
existing player shadow, and refreshed xG plus centred player shadow. The
combined model remains comparison-only until it passes chronological unseen
and prospective gates and the user explicitly changes the betting-engine rule.

Full design:
`BettingEngine/ml/football/player_layer/XG_PLAYER_SHADOW_ARCHITECTURE.md`
