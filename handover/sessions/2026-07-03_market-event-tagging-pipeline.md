# 2026-07-03 — Market Event Causal-Tagging Pipeline + Model-vs-Market Backtesting

## Context

This session started as an AFL R17 pricing job (see previous diary, 2026-07-02) but the conversation shifted into a deep model-vs-market accuracy investigation after questioning why Richmond/Carlton and Essendon/St Kilda were showing the model 9-12pts short of market. That investigation is the more important part of this session — it changed how we should think about "the model disagrees with market" going forward.

## Part 1 — Model-vs-market backtesting (the real finding)

Tried to fix the AFL "extreme ELO gap undercook" with a textbook sigmoid/probit rescale (industry-standard approach, confirmed via web research). **Backtested it properly and it failed** — within AFL's actual ELO range (0-450), a probit curve barely differs from linear; applying it just raised the global slope, fixing the extreme-gap games while re-breaking three moderate-gap games the June 10 calibration fix had already corrected. Did not ship it.

Then tested whether the market is actually beating the model at these disagreement points, using increasingly rigorous methodology:
1. Naive `elo_diff × 0.09` proxy vs market, 2022-2025 historical (227 games): market wins 61%.
2. Small 2026-only sample (Essendon/Richmond specifically, n=2): looked like model won — this was noise (confirmed once tested at scale in #1).
3. **Real production model** (`rules_margin` from `afl_shadow_predictions`, full T1-T7 stack) vs market, R12-R16: model wins 50%, market has lower avg error (23.8 vs 25.8), model carries a real +8.2pt overcook bias.
4. ATS/cover backtest (the metric that actually determines if a bet wins): overall 52.8% (noise), but the exact "rules+ML agree, big divergence from market" pattern — the one flagged this round — went **4-8 (33.3%)** this season. That's a losing pattern, not an edge.
5. User pushed back correctly twice: dismissing R13 (stale model) narrowed it to R14-16 where the model is at genuine parity (11-10 closer, near-identical avg error). Then asked for NRL: last 5 rounds showed a 60% ATS cover rate (21-14) — a real, if unproven (n=35), positive signal specific to NRL.

**Bottom line for future sessions:** don't treat "model disagrees hard with market, rules+ML agree with each other" as a signal to trust the model over market. The data says the opposite for AFL specifically. NRL's 60% cover rate is worth continued tracking but isn't proven at scale yet — re-run this same ATS backtest periodically as more rounds complete.

## Part 2 — Market event causal-tagging pipeline (what got built)

The conversation's natural next step: instead of trying to out-predict the market on final score, predict **line movement** — which way a number will drift, so you can time entries. This needs a labelled dataset of "line moved X, here's what news caused it" before any predictive model is possible. Built the instrumentation:

1. **`scripts/build_market_event_log.py`** — scans dated injury/emotional archives (both sports) into a unified timestamped event log. Also wired in team-news, which previously had no history (patched `scripts/update_team_news_injuries.py` to archive dated copies, not just overwrite `latest.json`).
2. **`scripts/compute_snapshot_deltas.py`** — computes every consecutive snapshot-to-snapshot delta (not just vs-Monday-baseline like the existing movement tracker) from the raw `data/odds_snapshots/{season}/*.csv` archive.
3. **`scripts/tag_odds_movements.py`** — joins deltas against the event log by sport+team+time-window. Filtered exchange lay bad-ticks (>300% "moves" that are just no-liquidity placeholder prices, not real signal).

First backfill run: 5154 significant moves (≥3% change) this season, only ~10% get a driver tag. That's expected — we only scrape injuries/emotional/team-news, not weather/public-money/sharp-money, and our historical 3x/day snapshot cadence leaves wide (multi-hour) windows early in the season. The point of this pipeline is to shrink that 90% "unexplained" bucket over future weeks, not to explain it in one backfill pass.

**7 new reactive Task Scheduler entries** fire an odds snapshot ~10min after each causal-driver scraper (NRL/AFL injuries, team news, emotional flags, referees, weekend injuries) so future weeks get tight before/after windows instead of relying on the flat 09:00/12:00/17:40 cadence. Plus a weekly "BetMate Market Event Pipeline" task (Thu 08:00) that rebuilds the whole chain automatically.

All additive — nothing existing was modified except the team-news archiving patch (backward compatible, `latest.json` behavior unchanged).

## Honest scope note

This is instrumentation, not a finished predictive engine, and I said so directly rather than overselling it. Told the user explicitly: expect to need a full season of properly-tagged data, not just "wait until the off-season and it'll be ready." AFL+NRL combined is only ~350-400 games/year across multiple distinct movement mechanisms (news, weather, pure money flow) — that's a thin sample to disentangle even with good tagging.

## Files changed
- New: `scripts/build_market_event_log.py`, `scripts/compute_snapshot_deltas.py`, `scripts/tag_odds_movements.py`, `scripts/run_market_event_pipeline.ps1`
- Modified: `scripts/update_team_news_injuries.py` (added dated archive write)
- New Task Scheduler entries: 7 reactive snapshot tasks + 1 weekly pipeline rebuild task
- New data: `data/market_events/2026_events.csv`, `data/odds_movements/deltas/2026_deltas.csv`, `data/odds_movements/tagged/2026_tagged.csv`

## Next steps
- Let the reactive snapshots + weekly rebuild run for a few weeks, then check whether the "unexplained" percentage is shrinking or the windows are tightening.
- Consider adding weather-update and market-consensus (public %) as additional event types once a source is identified.
- Re-run the AFL/NRL ATS backtest periodically — NRL's 60% cover rate needs a bigger sample before acting on it.
