# 2026-08-14 — Monday AFL/NRL Availability and Line-Movement Model

## User decision

The first actionable movement forecast must run on Monday for both AFL and NRL.
Tuesday NRL teams and Thursday AFL teams are too late to originate the signal;
they are confirmation/update checkpoints only.

The model must eventually self-learn from what it predicted correctly and
incorrectly. The objective for 2027 is to state, with calibrated confidence,
which player will miss, which direction the odds will move, and approximately
how far they will move.

## Implementation completed

- Repaired the AFL Footywire team-list parser. It now maps all 18 clubs,
  including clubs with unchanged teams, and refuses stale rounds.
- Repaired AFL injury-round selection. It uses the prepared pricing round rather
  than weeks-since-Round-1, which was wrong across bye rounds.
- Added `scripts/line_mover/forecast_availability.py`.
  - Produces `P(player misses next match)`.
  - Classifies likely out, doubtful or probable.
  - Assigns a player-value prior and expected absence points.
  - Aggregates projected absence burden by team.
- Added Monday mode to `run_pipeline.py` and `predict_movement.py`.
- Added AFL fixture fallback to the Monday odds snapshot when round prep does
  not yet exist.
- Monday and confirmation predictions have distinct immutable archive names.
- Added `collect_monday_intelligence.py` to collect AFL match reports, NRL
  post-game signals, judiciary reports and weekend injury changes.
- Installed launchd jobs:
  - Monday 07:15 — intelligence collection.
  - Monday 08:15 and 13:15 — NRL forecasts.
  - Monday 08:20 and 13:20 — AFL forecasts.
  - Tuesday NRL and Thursday AFL — confirmation runs.
- Eight targeted/regression tests passed.

## Non-negotiable self-learning design

Each Monday forecast must be frozen before later information arrives. Store one
row per player and one row per match with these timestamps and fields:

- forecast timestamp and information cutoff;
- sport, season, round, match and player identity;
- injury/news evidence and source reliability;
- predicted miss probability and player-value estimate;
- projected team absence points;
- contemporaneous H2H and handicap prices/lines;
- predicted movement direction and size distribution;
- eventual selected/not-selected outcome;
- actual opening-to-checkpoint and opening-to-close movement;
- Tuesday/Thursday confirmation changes and their timestamps.

After each round, a grader must create labels without changing the frozen
forecast:

1. Availability label: selected, emergency/substitute, late out or absent.
2. Direction label: home shortened, away shortened or no material move.
3. Magnitude label: probability-point change and handicap-point change.
4. Timing label: movement occurred before or after official team selection.
5. Error attribution: missed injury, false injury signal, wrong player value,
   wrong replacement assumption, market already moved, or non-personnel move.

## Learning loop required

Do not let the live job fit itself after every isolated result. Accumulate the
labels, then use expanding-window/time-split training:

- Calibrate player miss probabilities by sport, injury type, report wording,
  source, role, days to kickoff and prior games missed.
- Learn player and replacement value from historical team performance and
  closing-line response, with shrinkage for small samples.
- Train direction and magnitude models separately for H2H and handicap.
- Exclude totals from this movement project unless explicitly requested.
- Retain the rules model as the production fallback and run trained candidates
  as shadows until prospective calibration, CLV and error tests pass.
- Measure Brier score/log loss for availability and direction; MAE for handicap
  movement; calibration curves; CLV; and accuracy by confidence bucket.
- Version every model and preserve the exact training cutoff to prevent leakage.

## Promotion standard for next season

Before claiming confidence, require a prospective sample and demonstrate that:

- a stated 70% availability bucket resolves close to 70%;
- movement confidence buckets are monotonic;
- direction accuracy beats the no-change/market baseline;
- handicap movement MAE improves over the rules-only forecast;
- results hold by time split and are not driven by one club or a few large moves.

`availability_rules_v1` is the data-generating starting model. Its current
probabilities are priors, not historically calibrated claims. The 2026 remainder
must be treated as a prospective data collection and shadow-evaluation period.

## Key files

- `scripts/line_mover/forecast_availability.py`
- `scripts/line_mover/collect_monday_intelligence.py`
- `scripts/line_mover/predict_movement.py`
- `scripts/line_mover/run_pipeline.py`
- `scripts/line_mover/scrape_team_lists.py`
- `scripts/install_market_intelligence_launchd.py`
- `scripts/market_intelligence_refresh.py`
- `data/line_movement/availability/`
- `data/line_movement/predictions/`

