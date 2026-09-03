# UCL versus EPL/EFL implementation audit

## What the proven EPL/EFL pipeline actually does

The production research path is `backtest/walk_forward.py`. It performs
chronological gameweek snapshots, fits the shared Dixon–Coles model on xG,
blends Dixon–Coles and ClubElo probabilities (default 70/30), prices scorelines
and derived markets, then evaluates against results and Pinnacle opening/closing
fields. Tier stacks are applied only in the tier run and compared with the base
run. The player layer is a separate residual/shadow model, trained from
timestamped pre-match availability and observed minutes; it is not allowed to
rewrite the base model before its walk-forward gate passes.

## UCL gap identified

The UCL work built a parallel results-only Elo/Poisson baseline and tournament
simulators. That is useful format scaffolding, but it is not yet a mirror of the
EPL/EFL predictive pipeline: it lacks the shared xG-fed Dixon–Coles fit, the
EPL/EFL tier stack, cross-league feature inputs, and a recent-season market join.

## Correct rebuild direction

Keep the UCL format/state modules (draw, league table, ties and final), but
replace the match forecast core with the shared Dixon–Coles + Elo walk-forward
engine. Add UCL-specific configuration for seasons, xG source, cross-league
club identity and stage-aware evaluation. Keep T0–T3+ shadows and the player
layer structurally identical to EPL/EFL. Only then run the 2024/25–2025/26
market test against recent odds.
