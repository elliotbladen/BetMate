# 2026-08-12 — AFL ML Data, PyTorch and Compute Strategy

## Decision

Keep the current classical tabular ML approach (XGBoost/CatBoost) as the AFL
baseline. Do not introduce PyTorch merely because it is available.

PyTorch is a possible future layer once the project has sufficient, reliable
player-level sequential and line-up data. It must earn promotion through a
strict prospective comparison with the classical baseline.

## Why Classical ML Remains the Default

The current model inputs are predominantly structured, moderate-volume tabular
data: team ratings, form, opponent strength, venue, rest, injuries and market
snapshots. Gradient-boosted trees are well suited to this setting: they are
strong with limited samples, fast to retrain, robust and relatively resistant
to unnecessary modelling complexity.

Changing the algorithm alone is not expected to create an edge. Data quality,
feature construction, leakage control, calibration and execution before the
market adjusts matter more.

## What Would Make PyTorch Worth Testing

Prioritise collection and validation of pre-match player data, including:

- Match-by-match player role, minutes/time on ground, disposals, contests and
  involvement.
- Confirmed line-ups, omissions, returns, injuries and substitute likelihood.
- The composition of each team and replacement effect by position.
- Player-versus-team and player-with-team-mate history where the sample supports
  it.
- A long, consistently defined multi-season historical record.

With that data, PyTorch could use sequence and embedding models to learn role
and combination effects that are awkward to hand-engineer: for example, how a
particular midfield combination changes a player's disposal share. It may also
support a multi-task model that jointly predicts score, margin, H2H probability,
totals and player props.

This is a hypothesis, not an assumed edge. AFL/NRL have small numbers of games;
neural models can easily overfit those samples.

## Free Player-Data Research and Timing

**Decision: defer implementation until next season, after a couple of months of
NBA/EPL/NFL work and once the AFL/NRL seasons have commenced.** Begin those
seasons using the established normal models. Build and run the player-data
pipeline in parallel as a shadow enhancement; it must be measured before it
can alter a live price. The first implementation should be a classical
player/line-up feature pipeline, not PyTorch.

Free sources appear sufficient for a credible first version:

| League | Proposed primary source | Backup / validation | Expected usable data |
|---|---|---|---|
| AFL | Kali AFL Stats API | AFL Tables | Player match stats from 2000 onward: standard and advanced box-score data, fixtures and player/team records. AFL Tables also provides game-by-game stats, percentage of game played and sub-on/off indicators. |
| NRL | beauhobba/NRL-Data open-source scraper/data | NRL public stats and Rugby League Project | Player game statistics, match data and team-list context; expected fields include tries, tackles, running metres, line breaks, offloads and kick metres. |

References (researched 2026-08-12):

- https://kaliaflstats.com/ — free/open-source API; advertises historical AFL
  data from 2000, advanced player stats and a free 1,000 request/day limit.
- https://github.com/MFergie121/kali-afl-stats
- https://afltables.com/afl/stats/2026.html
- https://github.com/beauhobba/NRL-Data
- https://www.nrl.com/stats/players/
- https://www.rugbyleagueproject.org/

The AFL source is the cleaner starting point. For NRL, retain our own raw weekly
snapshots and reconcile outputs against official/public results because public
scraped feeds can change format or lag.

The public feeds can support player baseline, recent form, role proxies,
availability, positional-group strength, replacement effects and player-prop
features. They are not equivalent to paid tracking data: do not assume reliable
access to AFL centre-bounce attendance or locations, NRL event coordinates,
training loads or confidential injury severity. Start with observable usage
patterns and manually reviewed material role changes.

### Next-Season Build Order

1. Build an AFL player-match table with stable player IDs, final team sheets and
   raw-source snapshots.
2. Create pre-game player state and team-composition features; benchmark their
   incremental value against the existing AFL rules/ML models.
3. Implement the NRL equivalent with data-source reconciliation.
4. Re-run at team announcement and at final 22/17 confirmation. The system
   matches named players to history and prices the composition; it should not
   rely on manual per-player data entry each match.
5. Consider a PyTorch sequence/line-up experiment only after this dataset and
   the XGBoost/CatBoost benchmark are stable.

### Live/Shadow Rollout

- **Live:** retain the normal established AFL/NRL pricing models at season
  commencement. They remain the source of actionable prices.
- **Shadow:** ingest player data and calculate the player-enhanced price beside
  the normal price for every match, without changing recommendations.
- **Review:** compare normal versus enhanced prices using only pre-game inputs,
  then grade calibration, closing-line value and settled outcomes over a
  meaningful prospective sample.
- **Promotion:** only introduce the player enhancement into the live blend if it
  improves consistently and does not destabilise price calibration. Preserve the
  normal model as a visible fallback throughout.

## Required Evaluation Standard

1. Construct a pre-game-only training table. Never allow post-match variables,
   later team news or closing information to leak into an earlier prediction.
2. Establish and retain XGBoost/CatBoost benchmarks.
3. Use time-ordered validation and a genuinely future-season holdout; never a
   random train/test split for match forecasting.
4. Compare probability calibration, log loss, Brier score, ATS/price performance
   and closing-line value.
5. Promote a PyTorch model only if it improves those measures consistently on
   untouched data. Keep the simpler model if it does not.

Immediate high-value AFL feature work remains opponent-adjusted form,
available-player strength, role changes and timely team/injury news. These
should be built before a neural-network experiment.

## Course Assessment

The linked Daniel Bourke PyTorch course is useful as a foundation, not a
direct betting-model recipe. The high-value sections are the PyTorch workflow,
classification, training/testing, loss functions, optimisation, evaluation and
overfitting material (approximately hours 4–13). The computer-vision and image
dataset sections are not relevant to the current BetMate roadmap.

Reference materials:

- https://github.com/mrdbourke/pytorch-deep-learning
- https://learnpytorch.io/

## Quantum Computing

Do not plan the product around quantum computing. Even on a ten-year horizon,
the likely bottlenecks remain timely clean data, team-news interpretation,
leakage prevention, validation and bet execution. Quantum may eventually be
useful for specialised large optimisation or simulation tasks (for example,
correlated portfolio staking), but it will not make poor features predictive
and is not a likely replacement for classical ML or PyTorch in match pricing.

Maintain modular data and model pipelines so future compute can be evaluated
without rebuilding the system.
