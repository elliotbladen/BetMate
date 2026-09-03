# NFL Step 7 — live market and tier shadow

## Outcome

Step 7 V1 is implemented. It is a market-observation layer around the frozen
Step 6 predictions, not a market-following betting model and not an automated
betting agent.

The collector supports The Odds API's NFL feed and offline JSON imports. Each
successful capture is normalised to one row per game and bookmaker, written to
a timestamped append-only CSV, hashed in a capture manifest and compared with
the unchanged Step 6 prediction card. Empty responses are not archived as
market evidence.

## Quote qualification

A valid quote requires a recognised NFL matchup, unique frozen game mapping,
bookmaker ID, timezone-aware quote update, pre-kickoff timing, decimal odds and
internally consistent spread/total signs. The locked convention is the home
team's handicap: a home favourite is negative.

Schedule-embedded lines, stale fallbacks, invalid team mappings, post-kickoff
updates and malformed price pairs are retained only as rejected diagnostics.
They cannot establish an opener, closing-line value or ROI.

## Tier shadow card

- T0 is the data-health gate and passes only when at least one bookmaker quote
  qualifies for the game.
- T1 is the frozen structural ridge forecast and remains the active paper
  baseline.
- T2 quarterback/personnel remains shadow-unresolved until timestamped starter
  information is captured.
- T3 continuity/injuries remains shadow-unresolved until its timestamped inputs
  are connected.

The output calculates diagnostic model-versus-consensus spread and total edges.
All decisions are `WATCH` or `PASS`; staking remains disabled because no betting
threshold has been authorised and the true-opening audit remains deferred.

## Expired Odds API operation

The user's subscription is expected to be inactive for approximately one week.
The collector reports `upstream_unavailable`, writes no fake capture and leaves
the Step 6 card untouched. Offline exports can be validated with
`validate-file` without archiving them. When the subscription returns, `collect`
can begin prospective capture without regenerating predictions.

## Commands

From `BettingEngine`:

```text
python -m ml.nfl.step7_market_shadow collect
python -m ml.nfl.step7_market_shadow validate-file --input odds-response.json
python -m ml.nfl.step7_market_shadow import-file --input odds-response.json
```

Automated scheduling should begin only after the API key is active and one
manual capture has been reviewed for matchup, timestamp and spread-sign quality.

## Verification

The Step 7 tests cover valid matchup mapping, the home-spread convention,
mismatched spread rejection and post-kickoff rejection. They pass together with
the pre-existing NFL architecture suite: 24 tests total.
