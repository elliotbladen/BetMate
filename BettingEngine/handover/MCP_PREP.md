# MCP Server — Build Preparation
**Written:** 2026-05-11
**Status:** Architecture only — do not build until AFL automation is complete and NRL Tuesday pipeline is stable.

---

## What the MCP server is

The MCP server is a read-only query interface that sits in front of the BettingEngine DB.
It exposes live data as callable tools so that Baz (the BetMate AI agent) can answer
questions without needing direct DB access or file system knowledge.

Think of it as Baz's senses. Without it, Baz is blind to what the model knows.

---

## Who uses it — Baz first, everything else second

**Baz** is the primary consumer. Design every tool signature around what Baz needs to say
"wait", "bet", or "pass" — and to explain why, in plain language a punter understands.

Secondary consumers (later):
- BetMate UI (surface model context alongside odds)
- Manual session queries (you asking questions mid-session)

Do NOT build generic CRUD tooling. Build exactly what Baz needs to do its job.

---

## Baz's workflow — what it actually does

When a user asks "what should I look at this week?" Baz needs to:

1. Know what round it is and what games are on
2. Pull the model's prices for each game
3. Check which games have signals (triple confluence rule)
4. Pull context for each signal game — injuries, referee, weather, emotional flags
5. Confirm the data is fresh enough to trust
6. Summarise in plain language: edge, confidence, recommended stake, and the key reason

That is five or six tool calls. Design tools that map cleanly to those steps.

---

## Tool specification

All tools are **read-only**. Baz never writes to the DB. Human stays in control.
Every tool takes a `sport` parameter. Build sport-parameterised from day 1.

### Round and fixture

```python
get_current_round(sport: str)
# → { round: 11, season: 2026, dates: "May 15-17", venue: "Suncorp Stadium (Magic Round)",
#     games: [{ match_id, home_team, away_team, commence_time, venue }] }

get_fixture(round: int, sport: str, season: int = 2026)
# → same as above but for any round
```

### Pricing and signals

```python
get_pricing(round: int, sport: str, season: int = 2026)
# → list of { match_id, home_team, away_team,
#     model_home_score, model_away_score, model_margin, model_total,
#     fair_h2h_home, fair_h2h_away, fair_handicap_line, fair_total_line,
#     market_h2h_home, market_h2h_away, market_handicap, market_total,
#     ev_h2h, ev_handicap, ev_total, model_run_id, priced_at }

get_signals(round: int, sport: str, season: int = 2026)
# → list of { match_id, home_team, away_team,
#     h2h_ev, handicap_ev, totals_ev,
#     confluence_tier,   # "gold" | "silver" | "partial" | "none"
#     ml_confirmed,      # True/False/None
#     signal_label,      # "recommend_strong" | "recommend_medium" | "watch" | "pass" | "no_bet"
#     recommended_stake_pct,
#     recommended_side,
#     veto_flags }        # list of any active vetoes
```

### Game context (what Baz uses to explain a signal)

```python
get_game_context(match_id: int)
# → {
#     injuries: { home: [player, status, impact], away: [...] },
#     referee:  { name, penalty_rate, set_restart_rate, scoring_env_index },
#     weather:  { temperature, wind_speed, precip_prob, condition, flags },
#     emotional: { home_tier, away_tier, flags: [list of triggered signals] }
#   }

get_injuries(team: str, sport: str)
# → list of { player, position, injury, return_round, impact_tier }

get_h2h_history(home_team: str, away_team: str, sport: str, n: int = 10)
# → { h2h_win_pct_home, avg_margin, matrix_ev_h2h, matrix_ev_handicap, matrix_ev_totals,
#     venue_stats: { home_pct_at_venue, handicap_cover_pct } }
```

### Pipeline and data quality

```python
get_pipeline_status(sport: str)
# → { last_run: datetime, round_priced: int, status: "ok"|"warning"|"stale",
#     warnings: [list of step warnings from last prepare_round run],
#     data_age_hours: float }

get_data_quality(round: int, sport: str)
# → { injuries_loaded: bool, referees_loaded: bool, weather_fetched: bool,
#     results_loaded_prev_round: bool, style_stats_age_days: int,
#     missing_fields: [list], overall: "ok"|"warning"|"incomplete" }

get_pending_tasks(sport: str = None)
# → list of { task, description, blocking_pricing: bool }
# e.g. [{ task: "load_r10_results", description: "R10 results not in DB", blocking_pricing: True }]
```

### Performance and bankroll

```python
get_recent_performance(rounds: int = 5, sport: str = None)
# → { clv_h2h_avg, clv_handicap_avg, clv_totals_avg,
#     bets_placed, strike_rate, roi, pnl_total,
#     model_margin_error_avg, model_total_error_avg }

get_bankroll()
# → { current_balance, starting_balance, peak_balance,
#     available_for_staking, open_bets_exposure }

get_pending_bets()
# → list of { match_id, market, selection, odds, stake, placed_at, status }
```

---

## What Baz should NOT be able to do via MCP

- Write to the DB (no bet logging, no result entry, no signal creation)
- Trigger pipeline runs (that's Task Scheduler's job)
- Access raw file system paths (abstract everything through tools)
- Access .env.local or API keys

---

## Baz's language layer — separate from the MCP tools

The MCP tools return structured data. Baz's job is to turn that into plain language.

Example of what Baz should produce from a `get_signals` + `get_game_context` call:

```
Storm vs Panthers — Gold signal, Handicap
Model: Storm -5.5. Market: Storm -3.5. EV: +26% on Storm -3.5.
Key context: Panthers missing two spine players (Moses, Cleary doubtful).
Referee Sutton — high restart rate, favours higher-scoring games.
Weather: fine, 18°, no wind.
ML agrees: ML also tips Storm to cover.
Recommended: Storm -3.5 @ 1.91, 1.2% bankroll (quarter Kelly).

Baz read: BET
```

The MCP tools supply all the data. Baz writes the words. Keep these two layers clean.

---

## Implementation notes

### Stack
- Python, FastMCP or plain MCP SDK
- Reads from `data/model.db` (SQLite) — read-only connection
- No ORM needed — raw SQL is fine, queries are simple selects
- One file per tool group: `tools/round.py`, `tools/pricing.py`, `tools/context.py`, `tools/pipeline.py`, `tools/performance.py`

### Sport parameterisation
Every DB table that is sport-specific has a `sport` column (`NRL` / `AFL`).
Every tool passes `sport` through to the query. No NRL-hardcoded logic anywhere.

### Freshness
Every response that comes from the DB includes a `retrieved_at` timestamp.
If data is older than a configurable threshold, the tool returns a `stale: true` flag.
Baz should check `get_data_quality()` before making any recommendation.

### Error handling
If a tool can't return data (missing round, empty table), return a structured error:
`{ error: "no_pricing_found", round: 11, sport: "NRL", message: "Run prepare_round.py first" }`
Never raise an unhandled exception — Baz needs to gracefully tell the user what's missing.

---

## Build order

Do not skip steps. Each depends on the previous.

1. `tools/round.py` — `get_current_round`, `get_fixture`
2. `tools/pricing.py` — `get_pricing`, `get_signals`
3. `tools/context.py` — `get_game_context`, `get_injuries`, `get_h2h_history`
4. `tools/pipeline.py` — `get_pipeline_status`, `get_data_quality`, `get_pending_tasks`
5. `tools/performance.py` — `get_recent_performance`, `get_bankroll`, `get_pending_bets`
6. Wire into BetMate as Baz's data source
7. Write Baz's system prompt using these tools as its senses

---

## Pre-build checklist

Before starting, confirm:
- [ ] NRL Tuesday pipeline has run at least 2 full clean cycles
- [ ] AFL automation is complete and Tuesday pipeline is stable
- [ ] `signals` table is being written to by `prepare_round.py` (triple confluence rule built)
- [ ] `bets` and `bankroll_log` tables have real data
- [ ] `model.db` schema is stable — no planned migrations that would break queries
- [ ] Migration 009 (`injury_unique_constraint`) is fixed

---

## What makes a good MCP tool for Baz

- Returns everything Baz needs in one call (don't make Baz do joins)
- Includes human-readable labels alongside IDs
- Always includes `last_updated` or `retrieved_at`
- Returns a `stale` flag when data is older than expected
- Fails with a clear structured error, never silently
- Is sport-parameterised even if AFL isn't live yet
