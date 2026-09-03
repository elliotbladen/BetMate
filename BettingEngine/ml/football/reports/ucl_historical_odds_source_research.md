# UCL historical closing-odds source research

## Finding

Historical Champions League odds do exist for free, but the free sources usually
do not prove that the value is the final pre-kickoff quote. Football-Data UK
documents closing odds for its covered domestic competitions, not a complete
Champions League archive.

## Viable sources

1. **The Odds API** — Champions League sport key `soccer_uefa_champs_league`;
   its Business plan advertises historical odds snapshots. We should confirm
   season/date coverage and whether the returned final snapshot is timestamped
   before purchase.
2. **Big Balls Sports Data** — advertises historical opening/24-hour/closing
   snapshots and Champions League coverage. Confirm bookmaker, market and
   retention coverage before subscribing.
3. **VividOdds** — advertises bulk historical opening and closing odds back to
   2014 across bookmakers. Confirm that UEFA Champions League is included in the
   selected competition and obtain a sample export.
4. **ParlayAPI** — advertises historical closing-odds endpoints. Coverage is
   plan- and credit-gated; verify UCL dates and soccer market support first.

## Free candidates

- [Kaggle 30K football matches and odds](https://www.kaggle.com/datasets/rayenjlassi/more-than-20k-footballsoccer-match)
  includes Champions League 1X2 odds from 2003–2024. It appears to be a static
  odds/outcome file; no reliable quote timestamp or explicit closing flag is
  documented, so it is suitable for a provisional bookmaker benchmark only.
- [Footiqo Champions League database](https://footiqo.com/database/leagues/europe-champions-league/)
  advertises free historical 1X2, totals and BTTS odds. We must inspect an
  export to determine whether prices are timestamped and genuinely closing.

## Acceptance test before buying

Require a sample containing event ID, teams, kickoff timestamp, bookmaker,
market, selection, line, decimal price and `snapshot_at`. The close must be the
last pre-kickoff quote, not an in-play price or an un-timestamped settled odds
field. We will join only after team/date validation and store the raw response
immutably.

## Recommendation

Start by downloading the Kaggle file and requesting a small Footiqo export. We
can use either as a clearly labelled provisional benchmark, but true CLV claims
require a timestamped archive such as The Odds API. The project already has an
adapter for that normalised schema; do not buy a large archive until coverage,
timestamps and market definitions pass the acceptance test.

## Free-source probe (2026-09-01)

Footiqo's public Champions League page was inspected successfully. It exposes
historical rows with match ID, date, teams, 1X2 odds and totals/BTTS fields, and
states that the odds are sourced from 1xBet. The page labels the section
"Historical Odds" and "closing odds", but the displayed/export schema contains
no `snapshot_at`, bookmaker quote time or explicit pre-kickoff cutoff. Result:
**usable as a static 1xBet benchmark; failed the true-closing-line acceptance
test**.

The Kaggle page confirms a downloadable 1X2 dataset covering Champions League
matches through 2024, but its public data card likewise does not document quote
timestamps or a closing flag. Result: **candidate for provisional benchmarking;
not valid for verified CLV** until the downloaded file proves otherwise.
