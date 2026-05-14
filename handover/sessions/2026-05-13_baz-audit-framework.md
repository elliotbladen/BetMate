# Session 2026-05-13 — Baz Architecture Audit + Build Framework

## What happened

Planning session only. Full audit of both BetMate and BettingEngine.
No code written. See `BettingEngine/handover/sessions/2026-05-13_baz-audit-framework.md`
for full detail — this entry covers BetMate-specific findings.

---

## BetMate gaps identified (relevant to Baz)

| Gap | Priority |
|-----|---------|
| AFL injury scraper (`afl_injuries.py`) | High — needed before AFL enters Baz pipeline |
| AFL results scraper (in BettingEngine) | High — same |
| AFL Tuesday pipeline (Task Scheduler) | High — same |
| Model prices not on odds board | Medium — user currently reads `r11_pricing_2026.csv` manually |
| No signal badges on game cards | Medium — BET/WATCH/PASS overlays coming with Baz UI phase |
| BVI weekly Task Scheduler task | Low — still manual |
| Odds movement alert threshold filter (≥10%) | Low |

---

## Baz vision confirmed

Baz is an AI agent that replaces the user's manual weekly analysis:
- Reads model prices (BettingEngine pipeline output)
- Reads live market odds (The Odds API via BetMate snapshots)
- Flags value games + market intelligence signals (sharp money, public money, timing)
- Delivers via Telegram Tuesday evening
- No execution — human approves all bets

BetMate's role in Baz:
- Odds snapshot data feeds the EV comparison
- Odds movement data (`data/odds_movements/`) feeds the sharp/public money signals
- Eventually: Baz chat panel + signal badges surface in the UI

---

## Build order (BetMate tasks)

1. AFL injury scraper (`lib/scraper/afl_injuries.py`) — scrapes AFL.com.au injury list
2. Wire into Tuesday Task Scheduler (10:00, after AFL results)
3. BVI weekly Task Scheduler (Monday 08:00, `afl_bvi.py`)
4. Signal badges on odds board (post-MCP + Baz build)
5. Model prices column on odds board (post-MCP)
6. Baz chat panel (last — after agent is stable)

---

## Pending for next session
- [ ] AFL injury scraper
- [ ] AFL Task Scheduler pipeline
- [ ] BVI weekly task
- [ ] Odds movement threshold filter (≥10% change_pct)
