# NFL pre-open pricing architecture

Status: architecture and contracts implemented; model fitting/data backfill next.

## Decision

Use the **EPL engine pattern, not the EPL model**.

Keep its strongest engineering ideas: one config, immutable as-of snapshots,
independent fair prices, rolling-origin backtests, calibration, market baselines,
and a paper phase. Do not reuse Dixon–Coles, xG, the 70/30 blend, or football's
tier coefficients. NFL scoring is not well represented by independent Poisson
goals, and 17 games per team makes raw team estimates much noisier.

The NFL engine will predict two continuous quantities directly:

1. expected home margin (`home score - away score`), converted to the home
   handicap by changing the sign;
2. expected game total.

It will retain an empirical residual distribution so key numbers, tails, push
probability, moneyline probability and alternate lines are derived from actual
NFL errors rather than an unjustified normal distribution.

## Definition of winning

The prediction is frozen **before the market opens**. For each game:

```text
model error  = abs(model fair spread - consensus close)
opener error = abs(consensus open - consensus close)
improvement  = opener error - model error
```

A game is an opening-line win when improvement exceeds 0.25 points. Within
0.25 is a push. This is the primary research score because the stated task is
to beat the opener. It does not claim the close is truth; it is a stable market
benchmark. We separately report the points of CLV obtained by taking the
model's side at open, ATS results, calibration, and score MAE.

Promotion requires at least 250 games across two seasons, positive mean CLV,
positive opening-beat rate excluding pushes, and bootstrap uncertainty. No
single-season hit rate can promote a model.

## Why these inputs

The public base is nflverse:

- schedules contain results, rest, spread, total, prices, roof and surface;
- play-by-play provides EPA and success-rate inputs;
- weekly rosters go back to 2002;
- roster, injury and depth-chart feeds are updated automatically.

The nflfastR expected-points model values a play from game state rather than raw
yards. Research examples using nflfastR show opponent-adjusted EPA slightly
improves outcome prediction, exponentially weighted pass/rush offence and
defence are practical predictive inputs, defensive EPA is less stable than
offensive EPA, and EPA estimates require strong regression to the mean.

Sources:

- [nflverse schedules and field dictionary](https://nflreadr.nflverse.com/reference/load_schedules.html)
- [nflverse automated datasets](https://github.com/nflverse/nflverse-data)
- [nflverse roster, injury and depth-chart pipeline](https://github.com/nflverse/nflverse-rosters)
- [nflfastR expected-points calculation](https://nflfastr.com/reference/calculate_expected_points.html)
- [nflfastR model construction and calibration](https://github.com/nflverse/open-source-football/blob/master/_posts/2020-09-28-nflfastr-ep-wp-and-cp-models/nflfastr-ep-wp-and-cp-models.Rmd)
- [opponent-adjusted EPA experiment](https://opensourcefootball.com/posts/2020-08-20-adjusting-epa-for-strenght-of-opponent/)
- [rolling EPA game model](https://opensourcefootball.com/posts/2021-01-21-nfl-game-prediction-using-logistic-regression/)
- [EPA team ability and regression](https://opensourcefootball.com/posts/2021-06-27-estimating-team-ability-from-epa/)
- [reproducible expected-points/player-value research](https://arxiv.org/abs/1802.00998)

NFLverse's schedule line is useful as a market baseline, but it is not enough
to prove the opening objective because it does not preserve the full quote
history. The Odds API historical endpoint supplies timestamped spread, total
and moneyline snapshots from June 2020, at five-minute resolution since
September 2022. We therefore archive every available bookmaker quote and define
the consensus opener mechanically, rather than trusting a mutable `open` label.

- [The Odds API historical snapshot specification](https://the-odds-api.com/historical-odds-data/)

Published NFL market-efficiency work is a warning, not a feature recipe: lines
are strong forecasts, apparent rules often fail out of sample, and opening and
closing prices must be evaluated separately. That supports the market as a hard
benchmark and the paper-only posture; it does not justify blindly blending the
opening line into the pre-open model.

- [NFL betting-line predictive performance study](https://arxiv.org/abs/1211.4000)
- [NFL betting-market efficiency study](https://doi.org/10.1080/00036840500368904)
- [opening and closing NFL moneyline efficiency study](https://ideas.repec.org/a/mve/journl/v50y2024i2p87-117.html)

## Revised model stack: NRL patterns, NFL evidence

The NRL system contributes an engineering pattern rather than NFL coefficients.
Its best features are: a transparent official engine, capped and logged context
tiers, an independent ML shadow that cannot alter official prices, coherent
margin-derived probabilities, early-season shrinkage, abstention, and a frozen
rules-versus-ML-versus-market ledger. Those transfer cleanly to NFL.

Matrix confluence **does transfer** as an NFL inefficiency detector. Its job is to
identify matchup, personnel and context information that several independent
matrices agree the market has not fully priced. Unlike the structural fair-price
engine, confluence is evaluated at the available market line and can produce an
actionable edge flag. Correlated rows are grouped so one underlying fact cannot
manufacture several votes.

```text
POINT-IN-TIME FEATURE STORE
        │
        ├── STRUCTURAL ENGINE (official candidate)
        │     regressed EPA team state + explicit capped tiers
        │     every adjustment logged with reason and source timestamp
        │
        ├── ML SHADOW (independent challenger)
        │     shallow boosted margin, direct H2H and isolated total heads
        │     does not ingest tier outputs and cannot mutate official prices
        │
        └── MARKET SHADOW (only after open)
              predicts close-minus-open for bet timing
              never credited with beating an opener it has already observed
        │
        ▼
COHERENT PRICING + MATRIX CONFLUENCE LAYER
  empirical out-of-fold margin residuals -> H2H and cover probabilities
  expected scores = (total ± margin) / 2
  structural/ML/matchup matrices vs market -> unpriced-edge score
        │
        ▼
APPEND-ONLY LEDGER
  feature/model/config hashes, tier audit, opener, close, outcome and CLV
```

No blend is permitted initially. After 500 genuinely frozen predictions, a
small convex rules/ML blend may be trained using old folds only, and only if it
beats both parents out of sample.

## NFL tier specification

| Tier | NFL implementation | Initial state | Reason |
|---|---|---:|---|
| T0 data health | Stale feed, unresolved QB, bad mapping or insufficient books | Active abstention | Bad information should stop a price, not become false precision. |
| T1 team strength | Opponent-adjusted EWMA pass/rush EPA, success rate and aggressively shrunk defence/ST | Active | EPA is state-aware; opponent adjustment and regression have empirical support. |
| T2 QB/personnel | Probabilistic starter mixture; snap/position-weighted QB, OL and receiver availability | Shadow | Player-value research identifies QB and passing positions as especially valuable, but public injury estimates need validation. |
| T3 continuity | Returning snaps, unit continuity, coach/coordinator changes | Shadow | Useful preseason information; effect and decay must be learned rather than hand scored. |
| T4 venue/travel | Shrunk venue HFA, international travel, altitude/roof/surface | Shadow | Team-specific HFA is too noisy without a hierarchical prior. |
| T5 rest/schedule | Bye, mini-bye and short-week differential with near-zero prior | Shadow | A modern Bayesian study found no significant post-2011 bye/mini-bye advantage, so the NRL-style rest bump is not justified. |
| T6 weather | Timestamped wind/humidity/precipitation; totals first | Shadow | Published work finds weather affects scoring; margin effects require separate evidence. |
| T7 scheme/matchup | Neutral-script PROE, early-down efficiency, pressure/sack and explosive-play interactions | ML shadow | Interactions are numerous and correlated; boosting can learn them under walk-forward controls. |
| T8 market disagreement | Structural vs ML vs opener/market-shadow comparison | Diagnostic | Useful for timing and error discovery; opener is prohibited from the pure price. |
| T9 matrix confluence | Compare market-implied expectation with independent team, matchup, personnel, context and ML matrices | Active after open | Agreement across distinct matrices identifies potentially unpriced information; conflicts reduce or cancel the edge. |

All numeric caps are safety rails, not assumed edge. T2-T7 remain shadow until
their walk-forward ablation improves the relevant target and prospective frozen
results confirm the gain. The rest tier begins near zero specifically because
current evidence contradicts a generic bye-week premium.

Supporting NFL evidence:

- [Opponent-adjusted EPA showed a modest prediction improvement](https://opensourcefootball.com/posts/2020-08-20-adjusting-epa-for-strenght-of-opponent/), while [EPA team estimates require substantial regression because plays are volatile](https://opensourcefootball.com/posts/2021-06-27-estimating-team-ability-from-epa/).
- [nflWAR uses multilevel models for reproducible player value](https://arxiv.org/abs/1802.00998), and [positional WAR research finds QB and passing positions among the highest-value groups](https://journals.sagepub.com/doi/pdf/10.1177/1527002515580931?download=true).
- [A 2024 Bayesian state-space study found no significant bye or mini-bye advantage since 2011](https://www.frontiersin.org/journals/behavioral-economics/articles/10.3389/frbhe.2024.1479832/full).
- [NFL weather research links wind and humidity with deviations from expected scoring](https://doi.org/10.1177/155862351701200102).

## Model stack

```text
PRESEASON PRIORS
  prior-year opponent-adjusted EPA
  QB posterior + backup depth
  coaching/scheme continuity
  returning snaps / OL / receiver / secondary continuity
  draft and free-agent changes (structured, timestamped)
           │
           ▼
WEEKLY TEAM STATE (only games completed before cutoff)
  pass offence EPA + success rate      highest weight
  pass defence EPA + success rate      stronger shrinkage
  rush offence/defence                 lower weight
  early-down and neutral-script splits
  pressure/sack and explosive-play rates
  special-teams EPA                    aggressively shrunk
  opponent adjustment + EWMA recency
           │
           ▼
MATCH CONTEXT
  named starting QB and QB change
  injury/depth-chart availability
  rest / bye / Thursday / international travel
  home field by venue, roof and surface
  forecast wind/temperature/precipitation (totals first)
           │
           ▼
PARALLEL MARGIN + TOTAL ENGINES
  structural: regularised linear/ridge plus active audited tiers
  ML shadow: gradient boosting with shallow trees, independent of tier outputs
  ensemble prohibited until the prospective promotion gate
           │
           ▼
EMPIRICAL RESIDUAL DISTRIBUTION
  fair spread, fair total, win probability
  cover/over probabilities at actual quoted lines
  uncertainty and no-price flags
```

### Why a simple baseline first

There are only 272 regular-season games per year and team identities/coaches/QBs
change. A large neural model would have far more flexibility than trustworthy
independent samples. Ridge with hierarchical shrinkage is the production
candidate until a boosting challenger wins rolling-origin tests across seasons.

### Three engines, never mixed in reporting

- **Structural:** explainable pre-open official candidate with active capped tiers.
- **ML shadow:** independent pre-open challenger. Margin is primary; a separately
  calibrated direct H2H head is compared with the coherent margin-derived H2H.
- **Market shadow:** after open, predicts `close - open` from our pre-open edge,
  disagreement across books and new information. Useful for timing a bet, but
  never reported as if it predicted the opener.

## Data timing and leakage rules

Every feature row carries `as_of` and per-source timestamps. The contract rejects
any source newer than `as_of`.

- Week N team statistics are shifted and may use Week N-1 or earlier only.
- Injury status is whatever was public at the freeze time, not the final inactive
  list unless the strategy is explicitly repriced at that later timestamp.
- Opening snapshots cannot enter the pure pre-open feature table.
- Closing lines and game results are labels only.
- Preseason win totals may be a separate market-informed benchmark, never silently
  included in the pure model.
- Rescheduled games retain the information cutoff that would have been available
  at the actual prediction time.

## Market snapshot rules

1. Poll all available NFL spreads/totals every five minutes.
2. Save the raw response append-only with request and provider timestamps.
3. Normalise team aliases and use one sign convention: home handicap.
4. A book's opener is its first valid two-sided quote.
5. Consensus open is the median of book openers within the opening window;
   consensus close is the median sharp/eligible quote nearest kickoff.
6. Never overwrite an opener. Corrections create a new row with provenance.
7. Report stale-book count and dispersion; high dispersion raises uncertainty.

## Backtest

Rolling origin is mandatory:

```text
train 2014-2018 -> test each week of 2019
train through 2019 -> test each week of 2020
...
development ends 2024
2025 is a one-shot vault season
2026 is live paper tracking
```

Within each test season, update ratings only after a week finishes. Hyperparameter
selection is nested inside earlier seasons. Report:

- model vs close RMSE and opener vs close RMSE;
- opening-beat win/push/loss and mean improvement points;
- mean/median CLV and distribution around key numbers 3 and 7;
- margin/total MAE, Brier, log loss and calibration;
- ATS/total outcomes at the obtainable opener, with pushes explicit;
- Weeks 1-4 vs 5-18, QB changes, favourites/underdogs, international games,
  weather and injury-news segments;
- bootstrap confidence intervals clustered by season/week.

Baselines that must be beaten:

1. consensus opener;
2. prior close carried forward as a team power rating;
3. simple Elo + fixed home field;
4. previous-season regressed EPA ridge;
5. market-informed preseason prior (reported separately).

## Delivery sequence

### Phase 1 — data and audit

- Fetch nflverse schedules/PBP/weekly rosters/injuries/depth charts for 2014-2025.
- Backfill The Odds API snapshots for 2020 onward and archive live 2026 polling.
- Produce a coverage report and manually audit 50 games for line sign, timestamp,
  team mapping and opener definition.

### Phase 2 — baselines

- Build shifted weekly EPA features and opponent adjustment.
- Fit Elo and ridge margin/total baselines.
- Freeze preprocessing and run rolling-origin evaluation.

### Phase 3 — personnel and context

- Add each T2-T7 component in shadow mode, one family at a time.
- Add QB posterior/backup delta first; then injuries and roster continuity.
- Treat rest as a near-zero-prior test; weather primarily targets totals.
- Require walk-forward ablation and prospective confirmation before activation.

### Phase 4 — challenger and calibration

- Add an independent shallow gradient-boosting shadow without tier outputs.
- Compare direct calibrated H2H against margin-derived H2H; keep margin-derived
  pricing authoritative unless the direct head wins Brier/log loss consistently.
- Do not learn ensemble weights before 500 frozen prospective predictions.
- Fit empirical residual distributions by era/total band without using the test fold.

### Phase 5 — vault and paper season

- Freeze code/config/model hashes.
- Run 2025 once. Do not tune to the vault result.
- Publish 2026 pre-open prices with timestamp and archive the first obtainable line.
- No real staking until the sample gate and positive CLV requirements are met.

## Implemented now

- `config.yaml`: objective, sources, priors and promotion gates.
- `contracts.py`: timezone-aware feature, prediction and market contracts with
  leakage validation, engine identity, tier audit and an explicit spread convention.
- `tiers.py`: capped active/shadow tier application with coherent expected scores.
- `market.py`: deterministic median consensus snapshots.
- `evaluation.py`: opening-beat, CLV and aggregate scoreboard.
- `tests/test_nfl_architecture.py`: sign, leakage and scoring regression tests.

This is deliberately architecture, not a claim that an NFL edge already exists.
The first evidence gate is historical quote coverage; the first model gate is the
rolling-origin baseline; the first betting gate is live paper CLV.

## Detailed implementation plan saved 2026-08-21

### Tier modelling

- **T0 data health:** validate QB status, feature freshness, roster/injury feed
  coverage, game mappings, weather age and bookmaker coverage. Output a normal
  price, a price with wider uncertainty, or abstain; it never moves the line.
- **T1 team strength:** estimate separate pass/rush offence and defence, early-down
  and neutral-script EPA, success rate, explosives, pressure/sacks and special
  teams. Use opponent adjustment, EWMA recency and learned early-season shrinkage.
  Passing receives more weight; defence and special teams regress more strongly.
- **T2 QB/personnel:** build regressed QB ratings from passing EPA, success rate,
  sack avoidance, turnovers and scrambling. An uncertain starter is a timestamped
  probability mixture of starter and backup. Other injuries are snap- and
  position-weighted, with OL and receiving-unit continuity included.
- **T3 roster/coaching continuity:** returning snaps, OL and QB/receiver continuity,
  coach/coordinator changes, scheme change and rookie/free-agent usage. Its weight
  decays as current-season games provide stronger evidence.
- **T4 venue/travel:** hierarchically shrink league, venue and team home-field
  effects. Test roof, surface, altitude, neutral/international venues, travel/time
  zones and divisional familiarity without trusting small team samples.
- **T5 rest/schedule:** test rest differential, Thursday/Monday turnaround, bye,
  consecutive travel and international scheduling with a near-zero prior. No
  automatic bye bump is permitted.
- **T6 weather:** use timestamped wind/gust, precipitation, temperature, humidity,
  roof, surface, forecast confidence and age. Learn nonlinear effects and begin
  with totals; spread effects require their own validation.
- **T7 scheme/matchup:** expose PROE/pace, early-down efficiency, pressure versus
  protection and explosive-play interactions to the ML shadow. Avoid subjective
  matchup points.
- **T8 market disagreement:** after open only, compare structural, ML, consensus
  and book dispersion to detect information arrival and assist bet timing.
- **T9 matrix confluence:** compare the available line with separate team-strength,
  matchup, personnel, context/weather and ML matrices. Each matrix emits direction,
  magnitude, freshness and confidence. Agreement across distinct families produces
  an unpriced-edge score; correlated rows count once and conflicts reduce or cancel
  the signal. Its selections and thresholds are frozen and backtested separately.

Every proposed tier is tested as core, core-plus-tier and core-plus-shuffled-tier.
It remains shadow until it improves walk-forward results across seasons and then
confirms that improvement on frozen prospective predictions.

Matrix confluence has a different target: whether the available market line has
failed to incorporate information already present in our matrices. It is tested
at timestamped obtainable lines against subsequent closing-line movement and the
game result. We report coverage, CLV, ATS/total performance, edge-size calibration
and results by matrix combination. A combination is retained only when it repeats
across walk-forward seasons and prospective frozen selections.

### ML construction

The ML shadow shares the point-in-time feature store, but it does not ingest the
structural engine's tier outputs. This preserves an independent challenge.

1. Fit ridge and elastic-net baselines.
2. Fit a strongly regularised shallow boosted-tree challenger with conservative
   depth, learning rate, leaf sizes, row/feature sampling and early stopping.
3. Maintain separate margin-regression, total-regression and direct-H2H heads.
4. Make the margin head primary. Convert its out-of-fold empirical residuals into
   win, cover and push probabilities, including NFL key-number behaviour.
5. Keep direct H2H in shadow unless it repeatedly improves Brier score, log loss
   and calibration without breaking spread/moneyline coherence.
6. Store the game, cutoff and source timestamps, feature/config/model hashes,
   predictions and eventual opener, close and outcome for every row.
7. Widen uncertainty or abstain for missing inputs, unresolved QBs and
   out-of-distribution games.

No neural network is planned initially because the effective NFL sample is small.
No structural/ML blend is allowed before 500 frozen predictions; any later convex
blend must beat both parents using old out-of-sample folds only.

### Backtest protocol

Use a strict weekly rolling-origin simulation:

```text
train 2014-2018 -> predict each week of 2019
train through 2019 -> predict each week of 2020
...
development through 2024
2025 untouched one-shot vault
2026 frozen prospective shadow ledger
```

Ratings update only after completed games. Hyperparameters and calibration are
chosen using periods earlier than the test period. The 2025 vault is opened once
and is never used for iterative tuning.

Primary evaluation is whether the pre-open model is closer to consensus close
than consensus open, using the 0.25-point win/push tolerance. Also report spread
and total MAE/RMSE, H2H Brier/log loss/calibration, obtainable ATS/totals results,
CLV, key-number performance and clustered bootstrap uncertainty.

Segment diagnostics include early/late season, QB changes and rookies, favourites
and underdogs, divisional games, venue type, international games, severe weather,
key-number lines and total bands. Segments are diagnostic rather than permission
to create post-hoc betting systems.

Promotion requires at least two successful out-of-sample seasons, positive mean
opening improvement and CLV, improvement in the relevant predictive metric,
adequate market coverage, stable results, zero timing leakage and prospective
frozen confirmation.

### Next build order

1. Historical data ingestion, immutable snapshots and timestamp audit.
2. Opponent-adjusted EPA/ridge structural baseline.
3. Independent ML margin, total and direct-H2H shadows.
4. QB/personnel shadow tier.
5. Weather totals shadow tier.
6. Remaining context tiers, one-family-at-a-time ablations.
7. Frozen 2025 vault evaluation.
8. Live 2026 shadow tracking and opener/close ledger.
