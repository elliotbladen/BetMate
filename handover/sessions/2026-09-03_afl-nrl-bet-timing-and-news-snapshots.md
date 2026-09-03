# AFL/NRL bet timing and news snapshots

Date: 3 September 2026

## Agreed objective

Use the historical AFL and NRL odds snapshots to develop separate market-timing systems that answer whether an approved BetMate selection should be placed early, placed late, split across entry points, or left without a timing recommendation.

The timing layer does not predict the match winner and does not replace the fundamental production model. Its primary target is future price movement and expected closing-line value.

## Proposed outputs

- `BET NOW`: material probability that the current price will shorten or the current best price will disappear.
- `WAIT`: material probability that waiting will produce a better executable price.
- `SPLIT STAKE`: meaningful but uncertain timing advantage; place part now and retain part for a later checkpoint.
- `NO TIMING EDGE`: expected movement is too small or uncertain.

The output should include the probability of shortening/drifting, expected closing price or line, expected CLV, current best price, confidence and recommended entry window.

## Existing-data audit

The project documentation records 1,306 successful odds-snapshot writes across 36 collection dates, with dense collection from approximately 18 July through 22 August 2026. Active collection intervals ranged from roughly 10 to 60 minutes. Earlier rounds contain scattered opening, current and closing records but generally do not contain dense enough snapshots to reconstruct every market path.

The snapshot schema supports match ID, bookmaker/source, captured timestamp, market type, selection, line, decimal odds, and opening/closing flags. Match records supply kickoff time. Historical model prices, bets and CLV reports are also available.

The raw dense Mac/database archive still needs to be recovered or exported into the shared workspace and converted into a canonical training table.

This is sufficient for a pilot timing backtest and descriptive research, but not yet enough independent matches for a high-confidence production ML system. Multiple observations of the same match must never be treated as independent training examples.

## Backtest design

Reconstruct each match and selection from opening to close, including fixed decision horizons such as 48 hours, 24 hours, team-list time, six hours, one hour and close. At every horizon simulate betting immediately, waiting until the next horizon and waiting until close.

Primary evaluation:

- price captured versus close;
- no-vig probability CLV;
- handicap/total line-adjusted CLV;
- probability waiting improved the executable price;
- probability the current best price disappeared;
- calibration of predicted shortening/drifting probabilities.

Actual ROI is secondary because match outcomes add substantial noise to a timing test.

Testing must be chronological and grouped by match. Every snapshot belonging to one match must remain in the same train, validation or test period. No later snapshot, closing price, final team information or post-match fact may appear as an input at an earlier simulated decision time.

Compare ML with simple baselines: always bet immediately, always wait, favourites early, underdogs late, before team lists and after team lists. Start with interpretable rules and regularised models, then test gradient-boosted trees. AFL and NRL require separate models.

## News and information archive

Odds snapshots show when the market moved. Timestamped news snapshots are required to understand why it moved and whether the market has fully incorporated new information.

Collect:

- official squads, team announcements and final teams;
- injuries, suspensions, fitness tests and late withdrawals;
- training participation and expected return dates;
- coach press conferences and material player comments;
- predicted line-ups and replacement/role changes;
- AFL extended squads, emergencies and final teams;
- NRL Tuesday teams, 24-hour updates and final 60-minute teams;
- travel, venue changes, short turnarounds and rest;
- point-in-time weather forecasts;
- match reports and post-match injury/tactical information for future matches.

Each raw item should preserve at least:

```text
published_at
captured_at
sport
match_id
team
player
source
source_type
status
confidence
expected_impact
raw_text
source_url
```

Both `published_at` and `captured_at` must be retained. Point-in-time backtests may use only information available at the simulated decision timestamp.

## Source hierarchy

- Level A: official club/league sources and named coach or player statements.
- Level B: established journalists and reliable injury services.
- Level C: reputable predicted teams and analysis.
- Level D: rumours and unverified social discussion.

Only Levels A and B should directly create strong production availability features. Levels C and D may be stored and evaluated in shadow without automatically changing production prices.

## News-derived timing features

- time since the relevant news was published and captured;
- importance and position of unavailable players;
- expected replacement quality;
- whether news confirms or contradicts prior expectations;
- source level and independent confirmation count;
- market movement before and after the event;
- bookmaker reaction speed and dispersion;
- whether a leading bookmaker moved before the broader market;
- uncertainty remaining before final teams.

Match reports are inputs for subsequent matches only. Their timestamps must prevent leakage into the completed match.

## Forward architecture

Maintain three separated layers:

1. Fundamental AFL/NRL pricing engine.
2. Market and movement forecasting engine.
3. Decision and execution engine.

The normal production model remains the owner of betting probabilities. The timing model begins in shadow mode and can recommend execution timing only after chronological validation and prospective promotion gates. It must not manufacture a bet that failed the normal model's EV and staking rules.

## Next implementation sequence

1. Recover/export the raw Mac/database odds archive.
2. Audit match coverage, snapshot density, bookmaker coverage, timestamps and genuine closing records.
3. Build an immutable canonical odds-snapshot table and fixed-horizon market states.
4. Start the news, team, weather, press-conference and match-report archive with source levels and point-in-time timestamps.
5. Produce descriptive timing and market-reaction reports.
6. Backtest simple entry rules.
7. Train separate AFL and NRL movement models with match-grouped chronological validation.
8. Run the best frozen challenger prospectively in shadow next season.
9. Promote only after adequate calibration and sustained positive CLV.

## EPL/EFL/NFL extension

The equivalent EPL, EFL Championship and NFL collection/timing architecture is saved in `handover/sessions/2026-09-03_epl-efl-nfl_market_timing_collection_architecture.md`. It shares the immutable point-in-time foundation but preserves separate sport-specific markets, information cycles, models and promotion gates.
