# Session 2026-05-13 — Baz Architecture Audit + Build Framework

## What happened

Full audit of both BetMate and BettingEngine. No code written — planning session only.
Goal: design the path to Baz, the AI pricing agent.

---

## Audit findings — BettingEngine

### What's working
- 8-tier pricing pipeline firing cleanly (`prepare_round.py`) — T1–T8 all active for NRL
- SQLite DB (`data/model.db`) stable — full audit trail: model_runs → model_adjustments → signals → bets
- XGBoost shadow model running across NRL + AFL, CLV tracking active
- Decision layer built (EV, Kelly, signal labels, vetoes)
- `baz_learning_review.py` script generates JSON performance report
- Tuesday automation pipeline stable (2+ clean cycles)
- MCP server fully architected in `handover/MCP_PREP.md` — not yet built

### Critical gaps
| Gap | Notes |
|-----|-------|
| **Signals table empty** | Triple confluence rule not wired into `prepare_round.py`. `prepare_afl_round.py` same. This is the pin to pull — everything Baz does depends on it. |
| **MCP server not built** | Architecture done, zero code. Build order in MCP_PREP.md. |
| **Baz agent not built** | `baz_learning_review.py` exists but Baz-as-agent is zero. |
| **Migration 009 broken** | `009_injury_unique_constraint.sql` blocks migration runner. Fix before any new tables. |
| **ML predict.py stubs** | Phase 3 not started — all `NotImplementedError`. Shadow running but not yet feeding into pricing. |
| **AFL automation incomplete** | AFL results scraper, AFL injury scraper, AFL Tuesday pipeline — none built. `prepare_afl_round.py` exists but not automated. |

---

## Audit findings — BetMate

### What's working
- Odds board (NRL + AFL), live odds, 10 bookmakers
- Weather overlay (Tomorrow.io)
- AFL BVI filter
- Full scraper suite: injuries, emotional, referees, style stats, round prep, historical, odds snapshot/movement
- Tuesday Task Scheduler pipeline fully automated

### Gaps (relevant to Baz)
| Gap | Notes |
|-----|-------|
| No Baz UI | No chat panel, no agent interface |
| Model prices not surfaced | User has to open the CSV manually to see BettingEngine prices |
| No signal badges on odds cards | No BET/WATCH/PASS overlays |
| AFL injury scraper missing | No AFL.com.au injury list scraper yet |
| AFL results scraper missing | No automated AFL results fetch |

---

## Baz — Confirmed Vision

Baz is an AI agent that **acts as the user's proxy analyst** each week:

1. Pricing pipeline has already run (Tuesday automation)
2. Baz reads model prices + market odds
3. Baz flags games where there is **genuine value**
4. Baz tells the user

**No execution.** Human approves all bets. This stays true for at least the next few months.

### Baz alert types (confirmed in this session)
Beyond pure EV/model price comparison, Baz will flag market intelligence signals:

| Alert type | What it means |
|------------|--------------|
| **Get on early** | Model has edge, line hasn't moved yet — act before sharps close it |
| **Leave late** | Wait for sharp money confirmation before committing |
| **Sharp money** | Line moving in direction counter to public — sharps loading up |
| **Public money** | Recreational money inflating a price — potential fade opportunity |
| **Value flag** | Model price vs market price divergence above threshold |

These require the odds movement data already captured by `odds_movement_tracker.py` in BetMate.
The movement pattern (which direction, how fast, early week vs late) is the signal.

**Telegram delivery** — Baz fires a Telegram message Tuesday evening after the pipeline completes.
This is confirmed but not yet being built (BotFather token needed first).

---

## Build order (agreed)

```
1. AFL automation (1 session)
   → fetch_afl_results.py
   → afl_injuries.py (BetMate)
   → AFL Tuesday Task Scheduler pipeline

2. Wire signals pipeline (both sports)
   → Triple confluence rule → prepare_round.py + prepare_afl_round.py
   → Signals table populating on Tuesday

3. MCP server (BettingEngine/mcp/)
   → tools/round.py  → get_current_round, get_fixture
   → tools/pricing.py → get_pricing, get_signals
   → tools/context.py → get_game_context, get_injuries, get_h2h_history
   → tools/pipeline.py → get_pipeline_status, get_data_quality
   → Read-only, SQLite, sport-parameterised, FastMCP

4. Baz agent (BettingEngine/baz/)
   → Claude API + system prompt
   → MCP tools as senses
   → CLI first, Telegram notification second

5. Market intelligence layer (later)
   → Odds movement analysis → sharp vs public money classification
   → Timing signals (early week vs late week line moves)

6. BetMate UI (later)
   → Signal badges on odds cards
   → Model prices column
   → Baz chat panel
```

**AFL before Baz** — so Baz launches covering both sports from day one rather than NRL-only.

---

## Pending for next session
- [ ] Build AFL results scraper (`fetch_afl_results.py`)
- [ ] Build AFL injury scraper (`afl_injuries.py` in BetMate)
- [ ] Wire AFL Tuesday Task Scheduler pipeline
- [ ] Fix migration 009
- [ ] Wire triple confluence into `prepare_round.py` → signals table
- [ ] Install BVI weekly Task Scheduler task (Monday 08:00)
- [ ] Add MAE tracking to ML shadow report
