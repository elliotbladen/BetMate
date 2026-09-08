# System context review — 2026-09-08

## Scope

User requested familiarisation with Markdown and handover files. Reviewed core
instructions, project diary, architecture/decision documents, recent sport-specific
handovers and selected latest pricing artifacts. This was a documentation review,
not a runtime, data freshness or model validation audit.

## Current reading map

- Canonical SQLite database: `data/model.db`. BetMate supplies source data and
  hosts the web/Supabase integration; this directory contains the Python engine.
- NRL: rules remain official; independent margin-derived H2H/handicap ML stays
  shadow-only. See `docs/nrl_ml_shadow_architecture.md` and August 12 handovers.
- AFL: August 24 review favours ML H2H/handicap and rules totals. The newer saved
  finals-week-2 card explicitly uses a frozen 75% ML / 25% rules margin blend,
  rules totals and Monte Carlo uncertainty. This artifact does not establish
  that every production entry point uses the same policy.
- NRL/AFL halftime: August 15 v3 handovers supersede old fixed-regression notes.
  Preserve the current scoreboard; predict remaining scoring. Deep process
  coefficients still require prospective calibration.
- EPL/EFL: shared league-configured football engine. Normal engine qualifies
  candidates; player shadow cannot create or rescue bets or increase stakes.
  See the August 31 handover, including its September 3 audit updates.
- UCL: September 3 handover supersedes the earlier single-market architecture.
  Separate 1X2 and O/U layers share a foundation. Corners remain a challenger;
  player shadow has no timestamped events in the documented snapshot. The
  September 8 Real Madrid–Inter artifact fails live data-health promotion.
- NFL: framework and consolidated backtest are built; paper/shadow only,
  staking disabled. Latest readiness records identify market, QB, roster,
  injury and weather gates; their live status was not rechecked here.
- Racing: separate engine; its project tracker is authoritative. Steward effects
  require chronological testing across the next three starts.
- 2027 NRL/AFL rebuild: follow `docs/2027_nrl_afl_tier_rebuild_plan.md` with
  sport-specific learned effects, timestamped inputs and prospective gates.

## Working constraints

Human controls placement. Preserve append-only histories and model provenance.
Report genuine tier coverage and missing inputs for every NRL/AFL price-up;
the documented minimum is 75% populated tiers in scope. Distinguish theoretical
EV, genuine CLV, hypothetical portfolios and actual placed bets.

Several overview sections retain obsolete dates, paths and backlog items.
Consult newer specific records and inspect implementation before changing policy.
Existing worktree changes were observed and left intact. No models, pricing,
data pipelines or bets were changed; no tests were needed for this review.
