# Baz Pricing Agent Audit

Date: 2026-05-13

## Purpose

Baz should become the operator of the pricing system, not the pricing model itself.
The deterministic pipeline must collect data, price games, log decisions, measure outcomes, and publish reports. Baz sits on top of that system to inspect status, explain recommendations, trigger allowed workflows, and escalate missing or stale data.

## Current Assets

### BetMate

BetMate is currently the data collection and UI layer.

What exists:
- Next.js odds board at `/odds`.
- Odds API endpoint and local snapshot fallback.
- NRL odds snapshots written every 10 minutes.
- NRL fixture scraper and processed fixture files.
- NRL injury scraper and processed injury JSON.
- NRL referee scraper, now using NRL match-centre fallback.
- NRL style stats scraper.
- NRL emotional/news/postgame scout scripts.
- AFL umpire scraper.
- Weather API and local weather CSV output.
- Scheduled Windows tasks for most collection jobs.

Gaps:
- BetMate is not a stable export root for BettingEngine automation. `config/betmate_automation.yaml` still points at a macOS path.
- No single manifest for "current round is complete enough to price".
- Current BetMate files and BettingEngine preflight do not agree on layout. BetMate writes processed files under `data/nrl/...`, while `betmate_auto_price.py --dry-run` expects manifests such as `injuries-suspensions/latest/manifest.json`, `referees/latest/manifest.json`, `emotional-flags/latest/manifest.json`, and `historical-odds/latest/manifest.json`.
- UI imports referee JSON at build/runtime bundle level, so data refresh may require a Next restart or dynamic API path.
- Scrapers are local-machine scheduled tasks, so they do not run while the computer is off.
- Data health is visible in logs, not a first-class dashboard/API.

### BettingEngine

BettingEngine is the pricing and research layer.

What exists:
- SQLite DB at `data/model.db`.
- Main pricing pipeline: `scripts/prepare_round.py`.
- BetMate adapter: `scripts/price_from_betmate.py`.
- Auto runner: `scripts/betmate_auto_price.py`.
- Tier model: T1 baseline, T2 style families, T3 situational, T4 venue, T5 injury, T6 referee, T7 emotional, T8 weather.
- Decision modules for EV, Kelly, vetoes, and signal labels.
- Audit modules for model run and bankroll logging.
- ML models in `ml/models`.
- ML shadow output and DB table `ml_shadow_predictions`.
- CLV and weekly review scripts.
- Scheduled tasks for NRL pricing, results, CLV, historical downloads, and AFL reports.
- Historical matrix outputs for NRL/AFL.

DB state observed:
- `matches`: 301
- `results`: 293
- `market_snapshots`: 814
- `tier2_performance`: 24
- `ml_shadow_predictions`: 16
- `injury_reports`: 227
- `weekly_ref_assignments`: 15
- `model_runs`: 0
- `signals`: 0
- `bets`: 0
- `bankroll_log`: 0

Gaps:
- `prepare_round.py` writes `tier2_performance`, but not canonical `model_runs`, `model_adjustments`, or `signals`.
- `signals` table is empty, so Baz has no official recommendation layer to query.
- `bets` and `bankroll_log` are empty, so staking and self-learning cannot close the loop.
- `ml/predict.py` is still not implemented; ML is available through `ml/run_r9_shadow.py`, not a general inference module.
- Tests for EV and Kelly are placeholders.
- `betmate_auto_price.py` preflight references `preflight_checks`, but the live DB has no `preflight_checks` table.
- The automation config uses stale macOS paths on this Windows machine.
- The MCP prep doc correctly says not to build MCP until signals/bankroll are real.

Fixes applied in this audit:
- Updated `config/betmate_automation.yaml` for this Windows workspace.
- Added migration `023_betmate_agent_audit_tables.sql` for BetMate import/preflight audit tables.
- Added `config/baz_agent.yaml` as Baz's initial operating contract.
- Added `scripts/baz_learning_review.py` to produce the first weekly learning-review artifact.

Confirmed blocker:
- `scripts/betmate_auto_price.py --dry-run` now reaches preflight, but fails because BetMate export manifests do not exist yet. The next engineering step is either to generate those manifests from BetMate or update the preflight to read the current processed-file layout.

## Baz Target Architecture

```text
Scheduled jobs / cloud worker
  -> BetMate collectors
  -> BettingEngine preflight
  -> BettingEngine pricing
  -> model_runs + signals + ml_shadow_predictions
  -> results + CLV + calibration reports
  -> Baz reads status and explains actions through MCP
```

Baz is allowed to:
- Check data quality.
- Run approved refresh/price/report commands.
- Explain prices, signals, and missing data.
- Compare rules model vs ML shadow.
- Produce post-round learning notes.
- Recommend "bet", "watch", or "pass" when signals pass guardrails.

Baz is not allowed to:
- Place bets automatically.
- Modify bankroll without explicit user action.
- Treat ML as production until the promotion gates pass.
- Overwrite good latest data with empty scrapes.
- Recommend from stale odds or incomplete fixtures.

## Self-Learning Loop

Self-learning should mean measured calibration, not uncontrolled model mutation.

Every week Baz should run this loop:

1. Ingest results and closing lines.
2. Update actual outcomes for `tier2_performance` and `ml_shadow_predictions`.
3. Calculate:
   - margin MAE
   - total MAE
   - H2H accuracy
   - CLV by market
   - ROI by market
   - signal performance by tier/confluence
   - rules vs ML agreement performance
4. Write a learning report.
5. Propose parameter changes, but do not apply them automatically.
6. Promote changes only when backtests pass gates.

Promotion gates:
- New calibration beats current model on rolling holdout.
- No single tier adjustment dominates performance.
- Positive or improving CLV over a meaningful sample.
- Fewer data-quality vetoes than the current setup.
- Human approval before config/model replacement.

## Build Order

### Phase 1: Stabilise The Deterministic Pipeline

Do first:
- Fix `config/betmate_automation.yaml` to point at `C:\Users\ElliotBladen\Apps`.
- Add `preflight_checks` migration or remove that write path.
- Align BetMate export manifests with BettingEngine preflight.
- Make `prepare_round.py` persist `model_runs`, `model_adjustments`, and `signals`.
- Add real EV/Kelly tests.
- Make `betmate_auto_price.py --dry-run` pass on Windows.

Done when:
- One command can price the current NRL round end to end.
- The DB contains model runs and signals for every game.

### Phase 2: Agent Operating Contract

Add Baz as an operator over approved commands:
- `refresh_data`
- `run_preflight`
- `price_round`
- `run_ml_shadow`
- `publish_report`
- `run_learning_review`

Done when:
- Each command has structured JSON output.
- Failures are explicit and machine-readable.

### Phase 3: MCP

Build MCP after `signals` and `bankroll_log` are real.

Initial tools:
- `get_current_round`
- `get_data_quality`
- `get_pricing`
- `get_signals`
- `get_game_context`
- `get_pipeline_status`
- `get_recent_performance`

Done when:
- Baz can answer "what should I look at this week?" without filesystem access.

### Phase 4: Self-Learning

Build a weekly learning report and parameter proposal process.

Done when:
- Baz can say which tiers improved predictions, which hurt, and what should be trialled next.

## Immediate Next Engineering Tasks

1. Fix Windows paths in `config/betmate_automation.yaml`.
2. Add `preflight_checks` table migration.
3. Wire `prepare_round.py` to audit/model_logger.
4. Write real EV/Kelly tests.
5. Generalise `ml/run_r9_shadow.py` into `ml/predict.py`.
6. Expand `scripts/baz_learning_review.py` into a full weekly calibration and proposal report.
7. Move critical scheduled jobs to always-on compute.
