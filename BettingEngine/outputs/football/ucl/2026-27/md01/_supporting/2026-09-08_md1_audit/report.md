# UCL pricing attempt — 8 September 2026

**Outcome: 0 of 12 matches can be priced properly with all tiers.**

Scope: European 8–9 September; Sydney mornings 9–10 September. Existing Python UCL adapter executed; no model parameters or production gates changed.

The generic CLI fails with `KeyError: rho`. The adapter generated 9 numerical baselines; 3 matches were blocked before pricing because an opponent has no archive history. Numerical output is not full-tier pricing.

History: 1997 rows, latest 2026-05-30 18:00:00+00:00. Optimizer convergence: False. Current domestic form and 2026/27 availability are not consumed. Multiple clubs have split historic aliases; selecting their latest ID does not repair the missing earlier history.

## All-tier audit

| Tier | Result |
|---|---|
| T0 | FAIL: stale current inputs; incomplete full-tier integration; no verified live market captured |
| T1 | historical paper baseline only; no current domestic strength input; archive aliases split |
| T2 | UEFA team news reviewed; player-event file missing; no fitted active player adjustment |
| T3 | adapter uses old UCL form/rest; domestic schedule, rotation, pressing and travel not loaded |
| T4 | league-phase diagnostic only; no live incentive adjustment |
| T5 | not applicable: league phase, not knockout |
| T6 | referee appointment sourced; no referee-rate/weather pricing input consumed by adapter |
| T7 | market diagnostic unavailable: no current timestamped two-sided quote captured |
| T8 | confluence diagnostic; no validated current family signals |

Official team news and all 12 referee appointments were found. Their availability does not mean the Python model uses them. Player shadow remains data-pending and cannot set prices. Separate U/O scripts are historical challenger backtests, not a ready live full-tier pricer. No live market EV was calculated.

## Match coverage

| Match | Sydney date | Baseline result |
|---|---|---|
| AEK Athens v LASK | 2026-09-09 | BLOCKED_MISSING_TEAM_HISTORY |
| Club Brugge v Aston Villa | 2026-09-09 | UNVALIDATED_DIAGNOSTIC_ONLY |
| Borussia Dortmund v Villarreal | 2026-09-09 | UNVALIDATED_DIAGNOSTIC_ONLY |
| Porto v Manchester City | 2026-09-09 | UNVALIDATED_DIAGNOSTIC_ONLY |
| Lille v Real Betis | 2026-09-09 | BLOCKED_MISSING_TEAM_HISTORY |
| Real Madrid v Inter | 2026-09-09 | UNVALIDATED_DIAGNOSTIC_ONLY |
| Barcelona v Feyenoord | 2026-09-10 | UNVALIDATED_DIAGNOSTIC_ONLY |
| Stuttgart v Viking | 2026-09-10 | BLOCKED_MISSING_TEAM_HISTORY |
| Liverpool v Atlético de Madrid | 2026-09-10 | UNVALIDATED_DIAGNOSTIC_ONLY |
| Paris Saint-Germain v Slovan Bratislava | 2026-09-10 | UNVALIDATED_DIAGNOSTIC_ONLY |
| Sporting CP v Galatasaray | 2026-09-10 | UNVALIDATED_DIAGNOSTIC_ONLY |
| Napoli v Arsenal | 2026-09-10 | UNVALIDATED_DIAGNOSTIC_ONLY |

Raw numerical diagnostics and individual tier/history coverage are retained in `audit.json` for debugging; none is a bet-ready quote.

## Required before a proper price-up

1. Implement a compatible UCL live entry point and tier input contract.
2. Reconcile club identities and load domestic strength for teams absent from UCL history.
3. Load timestamped current form/schedule and availability; validate the player model before price influence.
4. Connect approved market-specific models and current bookmaker quotes; keep unpromoted tiers diagnostic.
5. Re-run data-health, tier-coverage and model-validity checks.

## Sources

- [fixtures](https://www.uefa.com/uefachampionsleague/news/02a8-2174c9e9019d-f909a77bd77a-1000--2026-27-champions-league-all-the-league-phase-fixtures/)
- [team_news](https://www.uefa.com/uefachampionsleague/news/02a9-2188cf675017-df8325ec95c3-1000--champions-league-predicted-line-ups-matchday-1-team-news-/)
- [referees](https://www.uefa.com/uefachampionsleague/news/02a9-218880e7a2aa-96adf63aa534-1000--who-is-the-referee-which-officials-are-in-charge-of-the-uefa/)
