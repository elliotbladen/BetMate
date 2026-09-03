# NFL Step 8J — T8 market-disagreement audit

## Decision

Keep T8 as a promising after-open WATCH diagnostic. It cannot alter the pure
pregame model, create a bet or enable staking.

The walk-forward test covered 1,343 games across 2020–2024 and used no 2025
vault predictions. When the ridge model differed from the listed opener by at
least three points, its direction matched the subsequent closing spread move in
65.8% of 412 games where the line moved. The tree reached 62.5% over 381 games.
For totals, three-point disagreements matched the closing direction in 62.6% of
390 moving-line games.

The fitted T8 spread movement model reduced RMSE from 2.180 to 2.141 points but
worsened MAE from 1.478 to 1.490, so it is not a spread adjustment. The totals
diagnostic modestly improved both MAE (1.735 to 1.715) and RMSE (2.274 to 2.202).

## Live operation

The existing quote collector now emits model disagreement, model agreement and
bookmaker line dispersion. Signals are labelled WATCH_SMALL, WATCH_MEDIUM,
WATCH_LARGE or WATCH_UNSTABLE_MARKET. Every label has betting action `none`.

Historical opening-line provenance remains incomplete and historical bookmaker
dispersion is unavailable. Promotion requires audited true openers plus frozen,
timestamped prospective captures after the Odds API subscription resumes.
