# xG plus player-shadow architecture

Status: proposed architecture only; do not implement or promote yet  
Leagues: EPL first, Championship only after a reliable point-in-time xG source exists

## Decision

The normal production engine remains the only engine used for bets. The combined
xG/player model is a shadow comparison model.

The EPL base engine is already fitted on historical team xG. Therefore post-match
xG must update the underlying team attack/defence state, while the player layer
must estimate only the difference between the available lineup and the lineup
implicitly represented by that team state. It must not add the players' full
attacking numbers on top of team xG.

## Separation of responsibilities

### Layer A — point-in-time xG performance store

After each completed match, append:

- total xG and non-penalty xG for and against;
- shots and shot-quality distribution;
- xG split by game state where available;
- eleven-versus-eleven xG and red-card state;
- penalties, score state and minutes spent leading/trailing;
- opponent, venue, date, source and capture timestamp;
- player starts, minutes, substitutions and individual xG/xA where available.

This match may update prices only for fixtures with a later cutoff. Historical
records are immutable.

### Layer B — normal team-strength engine

Fit the existing time-decayed Dixon–Coles team attack and defence ratings from
opponent-adjusted xG available before the pricing cutoff. Produce:

```text
base_lambda_home
base_lambda_away
```

The first candidate should compare raw xG with non-penalty, red-card-adjusted
xG. Match-state adjustment is a registered challenger, not an assumed upgrade.
The normal production engine is left unchanged during this study.

### Layer C — expected reference lineup

For each team-strength observation, retain the players and minutes that created
it. From recent point-in-time appearances, form an expected reference lineup:

- probability of starting by player;
- expected minutes conditional on starting and from the bench;
- position and role;
- replacement-level player by position;
- uncertainty and source confidence.

This reference is the lineup already implicit in the base team rating. It is
the centring point for the player correction.

### Layer D — player-shadow delta

At an early cutoff, use start probabilities and expected minutes. At the final
cutoff, use the confirmed XI and updated expected minutes. Encode both the
reference lineup and the fixture lineup with the same position-aware player
encoder.

The model receives the difference between those two representations, not the
absolute strength of the named players:

```text
reference-lineup embedding
fixture-lineup embedding
fixture minus reference
opponent position-group context
base lambdas and uncertainty
    -> small bounded correction head
    -> delta_home, delta_away, uncertainty
```

Apply the correction once:

```text
shadow_lambda_home = base_lambda_home * exp(clamp(delta_home, -0.12, +0.12))
shadow_lambda_away = base_lambda_away * exp(clamp(delta_away, -0.12, +0.12))
```

The ±12% cap remains an initial safety rail. It is not permission for routine
12% adjustments.

## Player features

All rolling values are shifted so the current match never contributes to its
own features. Initial player inputs:

- expected minutes and start probability;
- position group and role;
- rolling non-penalty xG/90 and xA/90, heavily shrunk by minutes;
- shots, touches in the box and key passes where available;
- defensive-action and ball-progression summaries;
- goalkeeper shot-stopping residual with strong shrinkage;
- recent minutes, rest, return-from-injury state and substitution pattern;
- team-relative on/off or regularised player contribution, only if it passes a
  separate stability test;
- source confidence and missing-data indicators.

Individual xG/xA describes how a player contributes, but it is not added
directly to team lambda. The learned delta is centred against the reference
lineup, which prevents team xG and player production being counted twice.

## Training target

The player layer learns residual performance after the frozen base engine:

```text
home_target = observed_home_npxG_adjusted - base_lambda_home
away_target = observed_away_npxG_adjusted - base_lambda_away
```

Use an exposure-aware likelihood or robust loss rather than treating a single
match's xG as truth. A secondary multi-task head may predict goals residuals,
but goals must not replace adjusted xG as the primary development target.

The final model is evaluated through the complete Dixon–Coles score matrix, not
only residual loss. Required metrics are scoreline log likelihood, 1X2 RPS,
Brier/log loss, calibration, totals calibration and closing-line value.

## Required snapshots

Every fixture has two independent records:

1. **Early shadow** — fixed weekly cutoff, using only news known then.
2. **Final shadow** — after official teams, without rewriting the early record.

Each record stores:

- model and data versions;
- xG history cutoff and latest included match;
- base lambdas;
- reference lineup;
- fixture lineup probabilities or confirmed starters;
- player delta and cap status;
- final shadow lambdas and all derived market probabilities;
- normal production probabilities alongside, never overwritten.

## Data flow

```text
Completed match
  -> immutable team/player xG record
  -> point-in-time rolling features
  -> time-decayed team xG ratings
  -> normal base lambdas
  -> expected reference lineup
  -> early or confirmed fixture lineup
  -> centred player-shadow delta
  -> shadow lambdas
  -> one Dixon–Coles score matrix
  -> shadow 1X2, O/U and BTTS prices
  -> post-round accuracy, calibration and CLV comparison
```

## Double-counting controls

- Remove or freeze the current T3 results-form adjustment in the xG-shadow
  challenger if it expresses the same recent performance already captured by
  updated xG ratings. Test both versions prospectively.
- Do not add an “unlucky last game” tier after feeding that game's xG into the
  base state.
- Do not add individual xG/xA totals directly to team lambdas.
- Centre lineup impact against the recent reference lineup.
- Train the player correction on residuals after every retained base tier.
- Keep manager, tactical, set-piece and player effects separately logged so
  overlapping adjustments can be audited.

## Evaluation design

Use expanding chronological season-forward splits. Every snapshot and player
row from the same fixture stays in one fold. EPL is the first eligible league
because a historical xG feed exists. Championship remains goals-fed until a
reliable, historically reproducible xG source is secured.

Compare four frozen candidates:

1. normal production engine;
2. refreshed team-xG base without player correction;
3. current player shadow on the existing base;
4. refreshed team-xG base plus centred player shadow.

Report overall results and the key subsets: material absences, confirmed lineup
surprises, promoted teams, low player-data coverage and large shadow deltas.
Bootstrap by match or round, never by player row.

## Promotion gates

The combined model remains comparison-only until it:

1. improves chronological unseen scoreline likelihood and 1X2 scoring;
2. does not worsen calibration or totals materially;
3. improves on the material-lineup-change subset rather than only ordinary
   matches;
4. produces stable, plausible player deltas without frequent cap hits;
5. shows prospective improvement across a substantial live shadow window; and
6. passes a formal promotion decision.

Even after promotion, the shadow does not automatically become the betting
engine. The user has set the current operating rule that only the normal engine
generates bets. Any future change to that rule must be explicit.

## Implementation sequence

1. Audit xG coverage, team aliases, timestamps and source reproducibility.
2. Build the immutable match/player xG store and leakage tests.
3. Materialise point-in-time reference lineups for historical fixtures.
4. Establish the refreshed team-xG-only benchmark.
5. Train a small linear or regularised centred-lineup baseline.
6. Train the bounded position-aware player model only if the baseline proves
   the data contain a repeatable residual signal.
7. Run all four candidates through identical chronological evaluation.
8. Freeze the winner and run it prospectively as early and final shadows.

No production wiring or betting-rule change is authorised by this architecture.
