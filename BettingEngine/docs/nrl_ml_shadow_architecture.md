# NRL ML Shadow Engine Architecture

## Executive decision

Keep the successful NRL T1–T10 rules engine as the official pricing system. Build
an independent XGBoost shadow that initially prices H2H and handicap. Do not add
the rule-tier adjustments to the ML output: the shadow must be independently
measurable before any blend is considered.

Totals remain a separate workstream. The architecture can support a totals head,
but it must not affect official totals until the existing totals calibration and
movement model pass their own validation gates.

## What already exists

- 3,469 engineered match rows from 2009–2026 in the older feature store.
- 912 detailed match-stat JSON files covering 2022–2026.
- 590 opening/closing market-movement rows covering 2024–2026.
- An old XGBoost trainer and live shadow runner.
- Archived 2024 and 2025 tests: H2H accuracy 61.3% and 59.4%; margin MAE 14.68
  and 14.94 points respectively.

The current workspace does not contain the old model binaries. Copies dated April
2026 exist in the sibling legacy repository, but they should be reference artifacts,
not production dependencies.

## Why the old runner should not be revived unchanged

1. It adds T2–T8 rule adjustments to the ML margin, so its output is not an
   independent model and tier information may be counted twice.
2. Its categorical rest classes are converted to NaN before XGBoost inference.
3. Venue statistics are hard-coded and several values have tiny samples.
4. Referee features are constructed from a latest-50 snapshot rather than a
   clearly versioned as-of-game calculation in the live runner.
5. The displayed adjusted H2H probability is derived from adjusted margin with a
   fixed 13-point standard deviation, not from the trained H2H classifier.
6. Probability calibration, Brier score, log loss and closing-market ROI were not
   first-class validation outputs.
7. The old 2026 feature file stops after 48 games and must be rebuilt.

## Proposed architecture

```text
Historical results/fixtures ───────┐
Rolling team process statistics ───┤
ELO/rest/travel/venue ─────────────┤
Injury, spine and Origin features ─┤
Weather/referee as-of features ────┤
                                   ▼
                     Point-in-time feature store
                                   │
                  ┌────────────────┴────────────────┐
                  ▼                                 ▼
       Independent pre-market model       Market-aware challenger
          (no bookmaker inputs)             (real market only)
                  │                                 │
          XGB margin regressor               XGB margin regressor
          Calibrated H2H head                Calibrated H2H head
                  └────────────────┬────────────────┘
                                   ▼
                       Shadow prediction ledger
                                   │
              ┌────────────────────┼─────────────────────┐
              ▼                    ▼                     ▼
        Rules comparison      Market/CLV audit       Outcomes audit
```

## Model targets

### 1. Handicap/margin head — primary ML target

Train an XGBoost regressor on actual home margin. This is the most useful shadow
target because it produces a coherent fair handicap and can later be converted to
H2H probability using a residual distribution learned strictly out of sample.

Evaluate:

- margin MAE and RMSE;
- winner direction accuracy;
- ATS record at closing line;
- mean/median model edge to closing line;
- performance by edge threshold, favourite/underdog, season phase and Origin period.

### 2. H2H probability head

Maintain two candidates:

- a direct XGBoost classifier;
- probability derived from the margin model's walk-forward residual distribution.

Calibrate each on an independent later period using sigmoid calibration initially.
Choose using Brier score and log loss, not winner accuracy alone. Margin-derived H2H
has the advantage that the handicap and H2H prices cannot contradict each other.

### 3. Totals head — isolated research only

A totals regressor may be trained and logged, but it remains operationally separate.
No blending with official totals until it independently improves MAE, interval
coverage, closing-total performance and calibration across multiple seasons.

## Point-in-time features

Every feature must contain only information available before kickoff.

### Stable core

- current ELO and ELO difference;
- rolling attack and defence ratings;
- exponentially weighted points for/against and margin over 4, 8 and 16 games;
- opponent-adjusted form;
- home, away and neutral venue indicators;
- rest days, bye state, travel distance and timezone change;
- season, round and finals indicators.

### Rugby-league process features

Use rolling pre-game differences and rates derived from the 2022–2026 match-stat
archive:

- run metres and post-contact metres;
- line breaks and line-break assists;
- tackle busts and effective offloads;
- opposition-20 tackles and forced dropouts;
- completion rate and incomplete sets;
- errors, penalties and six-again infringements;
- missed-tackle rate and defensive efficiency;
- kick metres, long kicks and attacking kicks;
- possession and territory.

Use rates per set, run or tackle where appropriate, plus opponent differences.
Research on NRL performance indicators identifies attacking production, run metres,
line breaks, offloads and missed tackles as useful explanatory signals. These are
post-match statistics, so only their rolling historical values may enter a pre-game
model—never statistics from the match being predicted.

### Availability/context features

- counts and weighted impact of unavailable players;
- separate fullback, halves, hooker and middle-forward availability;
- spine combinations and late team-list changes;
- Origin representatives absent, backing up or returning;
- referee rolling rates calculated as of the match date;
- weather available at the prediction timestamp.

### Market separation

Train two distinct versions:

- `nrl_premarket_shadow`: no odds or line inputs;
- `nrl_market_shadow`: genuine timestamped no-vig H2H probability and handicap line.

Missing market inputs remain missing. They are never replaced by ELO or another
model output. The market-aware version abstains when a genuine market is absent.

## Training and validation

### Dataset variants

1. Long-history baseline: 2009 onward using the stable core.
2. Rich-stat challenger: 2022 onward using stable core plus rolling process stats.

The rich model should not be padded with invented zeros for seasons without detailed
statistics. Compare it on identical 2024, 2025 and 2026 evaluation windows.

### Walk-forward protocol

- Train on seasons strictly before the test season.
- Tune on the last training season or nested expanding-time folds.
- Calibrate on data disjoint from base-model fitting.
- Test on the next complete season.
- For 2026, simulate round by round: train only through the prior round and freeze
  one prediction per match before results are known.
- Cluster uncertainty and resampling by round, not by individual game.

Primary historical folds:

- train through 2022, calibrate 2023, test 2024;
- train through 2023, calibrate 2024, test 2025;
- train through 2024, calibrate 2025, replay 2026 round by round.

Do not randomly split games. Do not select weights or thresholds on the same period
used to report final performance.

## XGBoost controls

- shallow trees (`max_depth` around 2–4);
- meaningful `min_child_weight` and regularisation;
- subsampling and column sampling;
- early stopping on a chronologically later validation set;
- optional monotonic constraints for highly reliable relationships such as ELO
  difference and genuine market-implied probability;
- fixed seeds, feature manifest and immutable model metadata.

Benchmark XGBoost against simple baselines: ELO, market, regularised linear/logistic
models and the official rules engine. XGBoost is promoted only if it beats these.

## Deployment contract

Each prediction ledger row must store:

- match and kickoff identifiers;
- prediction timestamp and data cutoff;
- feature/model/schema versions;
- raw margin, calibrated H2H probability and fair prices;
- official rules margin/probability;
- available market line, no-vig probability and bookmaker timestamp;
- data-health and abstention flags;
- later: outcome, closing market, CLV and error metrics.

The shadow process runs after the official price-up but cannot mutate official
prices, rule-tier tables or bet recommendations.

## Reporting

Round output should show:

- rules margin and H2H probability;
- pre-market ML margin and calibrated H2H probability;
- market-aware challenger when available;
- rules–ML and ML–market differences;
- data freshness and abstention reasons.

At season end report:

- Brier, log loss and reliability diagrams;
- margin MAE/RMSE and residual distribution;
- ATS record versus closing handicap;
- H2H flat-stake ROI versus closing price at several frozen edge thresholds;
- CLV using prices actually available when the forecast was made;
- results by season, round cluster, model version and disagreement band.

## Promotion gates

No integration into the official rules model until all are true:

1. At least two historical walk-forward seasons and a prospective 2026 segment.
2. Improvement in Brier/log loss for H2H or MAE/ATS for handicap.
3. Improvement survives round-cluster uncertainty testing.
4. Positive or non-negative CLV across more than one edge threshold.
5. No dependence on one team, one month or a handful of long-priced winners.
6. Feature freshness and prediction coverage meet operational targets.

If promoted, begin with a small fixed convex blend and keep totals separate. Do not
allow a learned meta-model until several hundred frozen, version-consistent shadow
predictions exist.

## Phased implementation

### Phase 0 — repair and reproduce

- rebuild the 2009–2026 feature store in this repository;
- restore versioned training artifacts locally;
- reproduce the existing 2024/2025 baselines;
- add Brier, log loss, calibration and closing-market tests;
- eliminate the live feature-contract problems listed above.

### Phase 1 — independent baseline

- train long-history pre-market margin and H2H candidates;
- deploy them shadow-only for the remaining 2026 rounds;
- log predictions automatically during every normal price-up.

### Phase 2 — rich-stat challenger

- build rolling point-in-time team process features from the 912 JSON files;
- compare core-only versus rich-stat models on identical folds;
- add structured injury, spine and Origin availability.

### Phase 3 — market challenger and season review

- add a strictly genuine market-aware version;
- backtest H2H and handicap versus recorded opening and closing markets;
- decide whether any fixed blend with the rules engine merits a 2027 shadow trial.
