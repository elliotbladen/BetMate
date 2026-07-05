# Session: CLAUDE.md Overhaul
**Date:** 2026-05-06
**Goal:** Fix the context-loss problem — Claude starts each session blind and has to hunt through diary entries to understand what's happening.

---

## Problem

Each new conversation, Claude reads CLAUDE.md (auto-loaded) but that file was pure philosophy/architecture — no operational state. To understand what round we're on, what's pending, and what to do next, Claude had to read 3-4 diary entries before doing any work. This caused friction and errors (Claude started down the wrong path twice today).

---

## What Was Built

### `BettingEngine/CLAUDE.md` (rewritten)

Added at the top:
- **HOW TO START A SESSION** — explicit checklist, "do NOT ask what were you working on"
- **CURRENT STATE** section with:
  - Current round, game dates, pending T5/T6 tasks
  - DB state table (which rounds have results)
  - Monday automation pipeline table
  - How to run scripts (exact venv path)
  - BetMate state summary (feeds this engine)

Kept from original:
- 7-tier model summary (condensed to a table)
- Pricing spine explanation
- Decision rules (EV formula, Kelly)
- Coding standards
- Product philosophy

Removed: bloated prose that was duplicated across sections, now replaced with tables.

### `BetMate/CLAUDE.md` (new — didn't exist before)

Created from scratch covering:
- App state (dev server, build status, theme)
- Scheduled tasks and their status
- Scraper output locations (what feeds BettingEngine)
- Injury scraper current source (NRL.com, changed 2026-05-05)
- Odds API budget
- New machine setup (the critical `.env.local` step)
- Running Python scrapers via uv
- Dev server cache-bust procedure

---

## The Rule Going Forward

**At the end of every session:**
1. Update the `CURRENT STATE` section in the relevant CLAUDE.md
2. Then write the handover diary entry

This way, the next session starts with accurate state in the auto-loaded file rather than having to hunt for it.

---

## AFL Architecture Prep (also this session)

Built `handover/AFL_PREP.md` — full pre-build reference doc covering:
- NRL pain points → AFL rules (8 items, don't repeat)
- Confirmed data sources (AFL.com.au injury list updates **Tuesday** not Monday — verified R7/R8/R9)
- 18-team canonical name map + slug map (built before any scraper)
- AFL scoring system (goals×6 + behinds×1, avg total ~160-200, ~4× NRL values)
- Tuesday pipeline: 09:00 results → 10:00 injuries → 17:00 historical → 19:30 pricing
- Build order (12 steps, do not reorder)
- MCP tool signatures to be sport-parameterised from day 1
- What NOT to carry over from NRL (Tier 2 features, constants, Tier 6)

AFL build starts Monday 2026-05-11. Do not build before then.

---

## Dual-DB Resolution (also this session)

Found two database files: `model.db` (0.63 MB, 35 tables, full data) and `betting_engine.db` (0 bytes, empty).
Confirmed `model.db` is canonical — 301 matches, 285 results, 127 injuries, 814 market snapshots.
Nothing in the codebase referenced `betting_engine.db`. Deleted it.
MCP server will query `data/model.db`.

Notable from the row counts:
- `model_runs: 0`, `model_adjustments: 0` — pricing pipeline logs to CSV not DB. Wire up before MCP.
- `afl_team_stats: 0` — needs seeding as part of AFL automation build Monday.
- `bets: 0`, `bankroll_log: 0` — schema exists, not yet used.

## Pending (do Thursday morning before games kick off)

- R10 referees: draw announced Wed — write `data/import/referees_r10_week10.csv` + re-run `prepare_round.py --round 10`
- R10 injuries: re-scrape from BetMate `nrl_injuries.py`
- R11 reprice: after R10 results load next Monday

## AFL Build
Starts Monday 2026-05-11. Open `handover/AFL_PREP.md` first thing.
