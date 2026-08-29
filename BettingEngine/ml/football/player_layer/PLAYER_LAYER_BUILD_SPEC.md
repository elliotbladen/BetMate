# EPL and Championship player-layer build specification

Status: foundation built; model training deliberately blocked until historical
player and line-up data are collected and audited.

## Objective

Compare exactly two prices for every eligible fixture:

1. `baseline_v1`: the existing league-specific D-C/Elo/tier price, frozen.
2. `baseline_v1 + player_layer`: the same price with learned, bounded player
   corrections to home and away expected goals.

The player layer is never a separate match winner model and never replaces the
base engine.

## Snapshot contract

| Field | Early price | Final price |
|---|---|---|
| Cutoff | fixed pre-match checkpoint | after official team sheet |
| Line-up | start probabilities + expected minutes | named starters override probability to 1 |
| Injury news | only source-attributed evidence before cutoff | same, plus official XI |
| Valid use | early market/shadow comparison | final market/shadow comparison |

All availability assertions retain `event_time`, `recorded_at`, source type and
source URL. Historical rows are append-only. This prevents the most damaging
backtest error: using the eventual line-up to pretend an early price knew it.

## Database records now implemented

`players`
: competition, team, player, primary position, active flag.

`availability_updates`
: availability state, starting probability, expected minutes, source, evidence
timestamps and note. Valid states: available, doubtful, injured, suspended,
rest-risk, international duty and out.

`match_snapshots` / `snapshot_players`
: immutable early or final set of inputs for one fixture. A final team sheet
does not alter the early snapshot.

## Training data contract — next collection step

One row per player per historical match, with data available strictly before the
relevant snapshot time:

```text
league, match_id, kickoff_at, snapshot_stage, snapshot_cutoff_at,
team, opponent, home_away,
player_id, position_group, recent_team, player_start_probability,
player_expected_minutes, actual_started, actual_minutes,
rolling_xg90, rolling_xa90, rolling_shots90, rolling_key_passes90,
rolling_defensive_features, goalkeeper_features,
days_rest, previous_30_day_minutes, availability_status, source_confidence,
base_lambda_home, base_lambda_away, final_home_goals, final_away_goals
```

Player rolling statistics must be calculated only from matches before the
fixture. New signings and sparse-minute players will receive position/league
priors rather than noisy individual estimates.

## The planned PyTorch layer

For each team, a small position-aware set encoder:

```text
player features + position embedding
  → shared small MLP
  → expected-minutes weighted pool for GK / defence / midfield / attack / bench
  → home-v-away comparison MLP
  → delta_home, delta_away
```

Final output:

```text
lambda_home = baseline_lambda_home × exp(clamp(delta_home, -0.12, +0.12))
lambda_away = baseline_lambda_away × exp(clamp(delta_away, -0.12, +0.12))
```

The ±12% initial cap is a safety rail, not a fitted conclusion. It remains until
walk-forward evidence justifies a change. The established D-C score matrix then
creates all markets from the adjusted lambdas, keeping H2H, handicap and totals
consistent.

## Evaluation gate

Use rolling season-forward splits, with identical fixture/timestamp pairs for
both models. Keep Championship 2025/26 as the existing sealed vault season.

Primary: scoreline likelihood and 1X2 RPS. Secondary: calibration, closing-line
value and fixed-rule betting segments. Report paired round-level bootstrap
intervals, overall and on the key-absence/line-up-change subset. The player
layer is eligible for live shadow use only if it improves consistently on unseen
seasons without worsening calibration.

## Operational sequence for the coming season

1. Import both league rosters.
2. Record meaningful absences/returns and rotation risks as news appears.
3. Freeze the early snapshot at the agreed weekly time.
4. Freeze the final snapshot when official XIs publish.
5. Archive actual starts/minutes and results after the match.
6. Do not let the shadow price influence real bets until its walk-forward gate
   passes.
