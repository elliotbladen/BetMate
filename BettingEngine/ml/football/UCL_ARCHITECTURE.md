# Champions League model architecture

Status: reworked for data-first backtest, 1 September 2026.

The Champions League must not be treated as a longer EPL season. From 2024/25
it has a 36-team single league phase: each club plays eight different opponents,
four home and four away, with two opponents from each coefficient pot. The top
eight go directly to the round of 16; places 9–24 enter a two-legged play-off;
places 25–36 are eliminated. UEFA confirms these rules and the same-association
draw limits in its 2026/27 draw procedure ([UEFA](https://www.uefa.com/uefachampionsleague/news/02a8-215821715a96-9a3b43fad585-1000--uefa-champions-league-league-phase-draw/)).

## Data reality and design decision

The original design assumed a ready-made UCL database. That was incorrect. The
repository now uses a two-source plan: openfootball's public-domain Champions
League files provide UEFA fixtures, stages and scores from 2011/12 onward;
Football-Data UK provides domestic-league results, statistics and odds for the
cross-league strength layer. Openfootball does not provide bookmaker odds or
consistent xG, so those fields remain optional and explicitly covered as
missing. We will not manufacture them.

The first objective is a reproducible historical backtest, not immediate
tournament forecasting. Match-level forecasts are the primary deliverable;
qualification markets follow only after the league-phase table simulator has
passed validation.

## Why it needs a different model

EPL estimates one domestic competition with a stable schedule and 38 matches.
The Champions League combines cross-country strength, a constrained draw,
unequal opponent schedules, travel, squad rotation and a phase change. A team’s
league-phase position is a state variable that changes incentives and future
qualification probabilities. Knockout pricing must also know the first-leg
aggregate score and which side hosts the second leg.

## Reworked architecture

```text
Openfootball UEFA results + Football-Data UK domestic results/odds + UEFA metadata
                              |
              cross-league club strength state
                              |
       phase-aware score model (Dixon-Coles + hierarchical Elo)
                 /                            \
      league-phase table simulator       knockout aggregate simulator
       36 teams, draw constraints       two legs, ET and penalties
                 \                            /
                 coherent market probabilities
```

### 1. Provenance and identity layer

Archive each raw source with URL, retrieval time, checksum and licence note.
Normalize names through the canonical club registry. Every match receives a
source, stage, season, timezone status and a `format_era` label. Rows with an
unresolved club or ambiguous score are quarantined, never silently dropped.

### 2. Club-strength layer

Maintain a club identity across domestic and UEFA matches. Estimate attack,
defence, goalkeeper and home advantage using xG where available and goals as a
fallback. Add a UEFA five-season coefficient as a prior, not as a free point
boost. Country/league effects are learned with partial pooling so a strong
Dutch or Portuguese side is not compared as if it played an EPL schedule.

### 3. Match pricing layer

Fit a shared Dixon–Coles score distribution plus cross-league hierarchical Elo.
Domestic form is available before the UEFA match; UEFA form is updated only from
completed prior European matches. xG is used when sourced and goals-only fallback
is labelled. Output H2H, Asian handicap and totals from one coherent score matrix.

### 4. League-phase layer

Represent every fixture with coefficient pot, opponent strength, home/away,
travel, rest, domestic rotation and current points/goal difference. Simulate the
remaining schedule rather than treating each match as independent. Use the
actual UEFA draw graph; if an historical draw cannot be reconstructed exactly,
mark its table outcomes research-only.

Outputs: match H2H/AH/totals, expected points, top-eight probability, top-24
probability, elimination probability and expected final position.

### 5. League-phase and knockout state

Use a scoreline distribution for each leg and carry the aggregate score into the
second-leg state. Remove the away-goals rule. A tied two-leg tie goes through
extra time and then penalties; UEFA Article 21 specifies two 15-minute periods
and penalties if still level ([regulations](https://documents.uefa.com/r/Regulations-of-the-UEFA-Champions-League-2026/27/Article-21-Knockout-system-extra-time-and-penalty-shoot-outs-Online?contentId=aBOyMYjtgYYIYwn~YRHF5Q)). The final is a neutral single match with the same extra-time/penalty treatment ([Article 22](https://documents.uefa.com/r/Regulations-of-the-UEFA-Champions-League-2026/27/Article-22-Match-system-final-Online?contentId=p6pndZ3IAsUzrTVR64sVPw)).

### 6. Context and markets

Player availability, rotation and travel are timestamped inputs. “Must win” is
not an emotional points tier; it is represented through the simulated table and
qualification value. Match markets are priced separately from tournament
qualification markets, but all derive from the same score/state distribution.

The tier skeleton deliberately resembles EPL: T0 data health, T1 strength, T2
availability, T3 matchup/schedule, T6 context/weather, T7 market disagreement
and T8 confluence. UCL adds two phase-specific tiers: T4 league-phase incentive
state and T5 knockout aggregate state. This preserves familiar operations while
preventing EPL assumptions from being applied to a European tournament.

## Backtest design (priority)

### Shared EPL/EFL match engine, UCL competition wrapper

The match forecast core will be the same validated engine used by EPL/EFL:
xG-fed, time-decayed Dixon–Coles with low-score correction, blended 70/30 with
Elo, and the existing tier stack. UCL-specific inputs modify the surrounding
state—not the core mathematics: cross-league priors and UEFA coefficients feed
club strength; league-phase table state feeds qualification simulation; and
knockout aggregate state feeds second-leg and final pricing. The player layer
remains the same residual shadow architecture as EPL/EFL.

Run two explicitly labelled tracks:

1. **Modern league-phase track (2024/25–2025/26):** actual 36-team graph,
   eight-match schedules, table qualification and knockout state.
2. **Legacy group-stage track (2011/12–2023/24):** historical group-stage rules,
   useful for club-strength and match-market learning but never mixed with modern
   qualification targets.

Use expanding-window forecasts. Test RPS, Brier/log loss, H2H accuracy, totals
calibration, Asian-handicap performance, opening-to-closing movement and CLV
where an auditable price exists. Football-Data UK odds are market benchmarks;
they are not model features. Missing odds reduce coverage and are reported.
No qualification or ROI claim is valid until the relevant draw, standings and
market records are fully matched.

## Five-step build order

1. **Ingest and archive data:** download openfootball UEFA seasons and the
   domestic Football-Data UK leagues; record checksums and source coverage.
2. **Normalize identities and matches:** map aliases, stages, dates, scores and
   format eras into the frozen UCL contract; quarantine unresolved rows.
3. **Fit the match model:** build domestic-to-UEFA strength states and generate
   expanding-window H2H/AH/totals predictions without market features.
4. **Validate competition state:** reconstruct modern draw graphs, table paths
   and aggregate knockout states; compare simulated outcomes with UEFA records.
5. **Run the complete backtest:** publish row-level forecasts, calibration,
   CLV/market benchmarks and a frozen prospective shadow card. Staking remains
   disabled until the evidence gates pass.

The EPL engine can supply score-distribution utilities and data contracts, but its
league table, domestic home advantage and tier constants must not be copied.
