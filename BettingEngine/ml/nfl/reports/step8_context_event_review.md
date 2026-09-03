# NFL context-event (“emotional tier”) review

## Decision

Do not add emotional points to NFL prices. Add a timestamped, objective event
register and study it prospectively as a diagnostic.

The project-wide emotional table contains assumed boosts for milestones,
coaching changes, tragedy, returns, rivalries and “must win” games. Those values
were not estimated for NFL and NFL explicitly does not inherit them. Motivation
is not directly observable, labels are easy to choose after a result, rare
events provide tiny samples, and public stories may already be in the odds.

## What we record

Each event needs a game and team, a fixed type, official announcement time,
source URL and model cutoff. News published after cutoff is rejected. Head-coach
changes, bereavements and milestones remain context diagnostics with zero
points. Player returns go to T2 availability. Rivalry, playoff and elimination
context belongs in T1 schedule state, preventing double counting.

Bereavement records describe only the public event. The system must not infer a
player’s grief, mental state or expected response.

## Promotion test

Freeze labels before kickoff, collect several seasons, compare core versus
core-plus-event and a shuffled-event control, and measure closing-line value as
well as score error. Promotion requires repeatable out-of-sample improvement;
until then every event has `model_points = 0` and `betting_action = none`.
