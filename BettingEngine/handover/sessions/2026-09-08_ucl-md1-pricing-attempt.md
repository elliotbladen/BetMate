# UCL MD1 pricing attempt — 2026-09-08

User requested the next couple of days of Champions League prices using Python,
all tiers, and an honest report of whether anything could be priced properly.

Scope: 12 UEFA fixtures on European September 8–9, Sydney mornings September 9–10.
UEFA fixture, team-news and referee pages were checked; links are in the report.

## Executed and observed

- `.venv/bin/python ml/football/price_match.py --league ucl --home 'Real Madrid' --away Inter --date 2026-09-08`
  fails with `KeyError: 'rho'`: generic league entry point is incompatible with UCL config.
- Executed `outputs/football/ucl/2026-09-08_md1_audit/run_audit.py`, a frozen
  diagnostic wrapper around the existing `ucl_shared_engine.py` functions.
- Loaded 1,997 historical matches; latest is May 30, 2026. xG sources: 342
  SofaScore, 36 FotMob, 1,619 goals fallbacks.
- Fit returned `converged=False`. Nine matches nevertheless yield finite,
  normalized numerical outputs; those are invalid for live pricing.
- Blocked AEK–LASK, Lille–Real Betis and Stuttgart–Viking before inference:
  LASK, Real Betis and Viking lack archive team history. No league-average
  fallback used for these opponents.
- Identified split historical club IDs (including Madrid, Inter, City, PSG,
  Feyenoord, Sporting, Galatasaray and Atletico). Latest IDs were used for the
  diagnostic run; this does not fix fragmented strength histories.
- The adapter only passes UCL historical form/rest to shared tiers. It does not
  load current domestic form/schedule, player events, referee rates or weather.
- UEFA publishes current team news and all 12 referee appointments. Availability
  on a website does not mean the model consumes them. No current market quotes
  were captured because upstream model validity already fails; no EV calculated.
- UCL player-event file is absent. Corner/O-U scripts remain historical challenger
  backtests, not a completed live market-specific full-tier runner.

## Outcome

Zero proper full-tier prices; no recommendations or placements. Raw diagnostics
are retained for debugging only. No production code/config or models changed.

Artifacts: `outputs/football/ucl/2026-09-08_md1_audit/report.md`, `audit.json`,
and `run_audit.py`. JSON includes cutoff, data/code hashes, fixture identities,
all-tier reasons, source links and raw diagnostic probabilities.

Next engineering work: compatible live UCL entry point, identity reconciliation,
domestic strengths for missing teams, current tier data and approved separate
market models. Require convergence and data-health checks before reporting any
price as usable. User has not requested a full engine rebuild in this session.
