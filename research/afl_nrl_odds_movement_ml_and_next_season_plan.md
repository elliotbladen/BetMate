# AFL and NRL Odds Movement: What We Can Learn and How We Should Build Next Season

## Introduction

BetMate finished the 2026 AFL and NRL seasons with something more valuable than a simple profit-and-loss result: it produced model prices, actual bets, closing-line records, team-list information and, late in the season, a dense archive of bookmaker odds snapshots. The snapshot system recorded H2H, handicap and totals prices from multiple bookmakers repeatedly through the betting week. Logs confirm 1,306 successful writes across 36 dates from 18 July to 22 August. On active days, prices were captured every ten to sixty minutes. Earlier rounds also have scattered opening, current and closing-price records, although these are not dense enough to recreate every movement.

This creates a promising research asset. It does not yet create a ready-made profitable machine-learning model. The dense sample covers only about five weeks, largely late in the season. Hundreds of thousands of price rows are repeated observations of a much smaller number of matches. Treating every observation as independent would produce misleading confidence and severe leakage. The correct objective is therefore not to manufacture a new winner-picking model from a large-looking row count. It is to learn how the market behaves, when BetMate should enter, whether model edge becomes closing-line value, and which information causes genuine movement.

The best direction for next season is similar to the NFL architecture now being developed: maintain an independent fundamental pricing model, build a separate market and movement layer, preserve point-in-time evidence, and require every new component to pass chronological out-of-sample gates before it influences staking.

## Part One: What the Existing Data Can Tell Us

### The distinction between outcome prediction and movement prediction

A match model asks who will win, by how much and with what total score. A movement model asks where the market is likely to move between the present snapshot and kickoff. These are related but different questions. A team can be correctly priced to win yet be a poor bet at the current odds. Similarly, a bet can lose on the field while still having been placed at an excellent price. Closing-line value is therefore the first clean test of whether BetMate identified information before the market fully incorporated it.

Our late-season snapshots are best suited to market forecasting. At any point in the week, we can measure the current consensus H2H probability, handicap and total, then compare them with the final pre-game market. Targets can include the change in no-vig win probability, the number of handicap points moved, the number of total points moved, whether the price improved, and whether an early move continued or reversed. This is more statistically efficient than using match results as the immediate target because every match has an observable closing market, while wins and losses remain noisy.

### Reconstructing the life of a market

The snapshots can show how each market developed from opening to close. For every game, we can construct a timeline containing the best available price, bookmaker consensus, dispersion between bookmakers, line changes and time remaining until kickoff. This allows us to answer practical questions that could materially improve results.

We can test whether Monday prices were usually best for favourites or underdogs; whether team-list day created the largest AFL moves; whether NRL markets reacted earlier to spine changes; whether weather affected totals only near kickoff; and whether late money tended to be informative. We can also determine whether a move from −4.5 to −6 was more significant than a price-only change at the same line, and whether totals crossed important numbers before or after weather information became reliable.

The principal output should be an entry-timing table by sport and market. It might show, for example, that AFL handicaps with strong team-strength disagreement should be taken before final teams, while weather-sensitive totals should wait. NRL H2H may require a different policy because team changes to a halfback, fullback or hooker can affect both expected margin and uncertainty. These conclusions must be learned from evidence rather than imposed universally.

### Measuring whether our edge was real

The most important diagnostic is the relationship between BetMate's stated expected value and subsequent market movement. At every recorded decision time, we should calculate the normal model probability, the no-vig market probability, stated EV and eventual CLV. Bets should then be grouped by sport, market, EV band, price band, model confidence, time to kickoff and direction of market movement.

If 10–20% model EV regularly becomes positive CLV, that is evidence the model finds information. If supposed 40–80% EV consistently moves against us, the likely explanation is model overconfidence, stale inputs or bad market matching—not extraordinary value. This is especially relevant to NRL H2H, where the season review found that a simple 10% EV threshold would not, by itself, have solved the problem. The fixed margin standard deviation made extreme H2H probabilities too easy to generate. Odds movement gives us an independent test of that diagnosis.

For AFL, this analysis can reveal whether failures came from the core margin estimate, the conversion from margin to H2H probability, contextual tiers, or entry timing. If the model's expected margins were reasonable but selections consistently lost CLV after teams were announced, the availability layer was inadequate. If the market agreed with the direction but the model exaggerated the size, calibration was the greater problem.

### Learning bookmaker behaviour

Multiple bookmakers allow us to study market leadership. We can identify which operator moved first, which copied the consensus, how long stale prices remained available, and whether Betfair or a particular fixed-odds bookmaker provided the most informative signal. The relevant unit is not merely the best quoted price. It is the sequence: leader moves, consensus follows, stale book remains open, and price disappears.

A useful classification target is the probability that another bookmaker follows a leader within thirty or sixty minutes. Another is the expected remaining life of the current best price. Even a modest model could improve execution by warning that an edge is likely to vanish. Conversely, if market dispersion is high and the consensus is unstable, waiting may be better than chasing an isolated move.

This analysis must account for line equivalence. A handicap of −6 at $1.90 is not directly comparable with −6.5 at $2.00. Prices should be converted into a common representation, ideally a fitted market probability and expected-margin surface. H2H books must be de-vigged. Totals and handicaps should incorporate both the point and price rather than treating movement in either field alone as the target.

### What machine learning can realistically do now

The current data can support exploratory models for movement direction and closing-line prediction. Strong baselines should come first: consensus movement, time-to-kickoff averages, regularised linear regression and simple bookmaker-leader rules. Only then should boosted trees such as LightGBM or XGBoost be tested. Useful features include current consensus, opening line, distance from opening, bookmaker dispersion, recent velocity, time to kickoff, day of week, market type, favourite strength, model-market disagreement, team-list state, player availability, rest, travel, venue and weather uncertainty.

The data cannot yet support a highly flexible deep-learning system or reliable team-specific movement rules. The true sample size is the number of independent matches, not the number of snapshots. All snapshots from one match must stay in the same train or test partition. Testing must be chronological, and every feature must reflect information available at that timestamp. Closing prices, later team news and later snapshots can be targets, never inputs.

The current sample is also late-season biased. Finals pressure, settled team ratings, injury accumulation and bookmaker liquidity differ from early rounds. Any result should remain shadow-only until tested prospectively across the opening and middle portions of next season.

## Part Two: What We Should Implement Next Season

### Adopt an NFL-style three-engine structure

Next season should use three clearly separated engines. The first is the fundamental game-pricing engine. It estimates expected margin, score distribution, H2H probability, handicap cover probability and totals probability without being silently pulled toward the current bookmaker price. The second is the market engine. It estimates the current efficient consensus, uncertainty, bookmaker leadership and likely closing position. The third is the decision engine. It determines whether there is enough model edge, market confirmation, liquidity and timing advantage to place a bet.

This resembles the NFL direction because player availability, especially at high-value positions, should be represented explicitly and probabilistically rather than through loose manual adjustments. The market remains an independent benchmark. A new feature must improve calibration or error on chronological unseen data before promotion. Shadow challengers run beside production, but they cannot create live bets until formally promoted.

The architecture prevents a common failure: using market odds inside the fundamental model and then claiming an independent edge against the same market. Market-aware blending can exist as a separately labelled forecast, but the pure model price, market consensus and final decision price must all remain visible.

### Build one canonical snapshot warehouse

The first implementation task is to recover the Mac snapshot archive and place it in durable shared storage. The raw files should remain immutable. A canonical table should contain snapshot timestamp, sport, game identifier, teams, kickoff, bookmaker, market, outcome, point, price and source. Team aliases and game identifiers must be resolved once, with unmatched rows quarantined rather than guessed.

From that raw layer, generate a clean market-state table at fixed horizons: opening, Monday morning, team-list minus one hour, team-list plus thirty minutes, 48 hours, 24 hours, six hours, one hour and close. Preserve the original observations so alternative horizons can be reconstructed. Store no-vig H2H probabilities, consensus handicap and total, best available executable price, bookmaker count, dispersion, movement velocity and source freshness.

Collection must resume before Round 1 and continue through finals. API failures after 22 August show that monitoring is essential. The system should alert when a sport returns no fixtures, authorization fails, the latest snapshot is stale, bookmaker coverage collapses or a scheduled capture does not write. A daily health report is more important than a sophisticated model trained on missing data.

### Rebuild AFL around a coherent margin distribution

AFL needs the larger rebuild. The primary model should predict margin with an empirically estimated residual distribution. H2H and handicap prices must be derived from the same distribution so they cannot contradict each other. Totals can retain the strongest existing rules component initially, but it should be assessed independently.

Availability should follow the NFL principle of player value and uncertainty. Rather than adding many subjective tiers, estimate the expected impact of missing players by role, quality, replacement level and probability of playing. Final teams should update the distribution, not merely shift the mean. Missing elite players can increase uncertainty as well as change expected margin.

The market layer should then predict expected closing handicap and H2H movement. AFL betting rules can distinguish between model conviction and timing. A strong model edge that is also expected to shorten may be placed early. A model edge dependent on uncertain teams should wait. If the market moves sharply against BetMate after confirmed teams, the bet should require revalidation rather than automatic averaging down.

### Retain the NRL core but repair H2H calibration

NRL does not require the same half rebuild. Its standard pre-match markets were profitable overall before poor staking and peripheral bets diluted the result. The priority is to fix H2H conversion, discipline selection and control exposure.

Expected margin should remain central, but the residual scale must be learned by season phase, favourite strength and relevant squad state rather than frozen at 12 points. The model should produce calibrated win probabilities with reliability plots and Brier/log-loss tests. Key-position availability—halfback, five-eighth, fullback and hooker—should follow the NFL quarterback idea: represent named-starter probabilities, replacement value, combinations and uncertainty explicitly. It should not become an oversized subjective adjustment.

The NRL movement model can test whether team-list and key-player information predicts closing changes beyond the current market. A Monday edge involving an uncertain spine should not receive the same decision status as one supported by confirmed teams. The decision engine should enforce the agreed rules: singles only, no speculative multis, minimum EV, capped stakes, no chasing and limits on correlated positions from the same game.

### Train and evaluate correctly

Development should proceed through registered experiments. Phase one is descriptive: reconstruct market timelines and publish entry-window, bookmaker-leadership and EV-to-CLV reports. Phase two trains simple closing-line baselines. Phase three tests boosted models. Phase four runs the best frozen challenger prospectively in shadow. Only after sufficient rounds should it influence timing, and only later should it influence whether a bet qualifies.

Evaluation must occur at the match level. Use expanding chronological folds: train through one date, validate on the next block, then roll forward. Report mean absolute error for closing handicap and total, log loss or Brier score for movement direction, calibration by predicted probability, and performance by time horizon. Compare every model with simple alternatives such as no movement, current consensus and historical average movement.

ROI should be last, not first. The promotion order should be data integrity, forecast accuracy, calibration, CLV and finally profit under realistic prices and limits. Hyperparameters and feature choices must be frozen before the final holdout. AFL and NRL need separate models because their team announcements, scoring scales, liquidity and information cycles differ.

### Convert research into betting rules

The final product should be a short decision card for every candidate. It should display the fundamental price, current no-vig market, EV, predicted close, expected CLV, team-list state, uncertainty, best bookmaker, recommended entry window and maximum stake. The player or experimental shadow should remain on a separate comparison panel.

A sensible initial policy is to require positive normal-engine EV and no major data-quality warning. Higher stakes should require both model edge and positive expected CLV. If model EV is high but predicted CLV is negative, the system should flag possible overconfidence and reduce or reject the bet. Market agreement is not proof the wager will win, but persistent negative CLV is strong evidence that the process needs repair.

## Conclusion

The late-season snapshot archive can materially improve BetMate, provided it is treated as a market microstructure dataset rather than inflated into thousands of independent games. Its immediate value is learning when prices move, which bookmakers lead, whether stated EV becomes CLV and when BetMate should enter. Its longer-term value comes from a full-season prospective archive beginning before Round 1.

Next season should adopt the strongest elements of the NFL approach: a coherent fundamental distribution, explicit player availability, strict separation between model and market, point-in-time features, chronological validation, shadow promotion gates and disciplined execution. AFL should rebuild its margin and H2H spine. NRL should retain its useful core while recalibrating H2H and enforcing sensible staking. The objective is not simply to pick more winners. It is to produce prices that are calibrated, beat the closing market for identifiable reasons and translate that advantage into controlled, repeatable betting decisions.
