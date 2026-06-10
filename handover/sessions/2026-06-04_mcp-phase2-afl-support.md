# Session Diary — 2026-06-04 — MCP Phase 2: AFL Support

## What was done

### Problem
Phase 1 (tool-use loop) was NRL-complete but had three AFL gaps:
1. `get_game_context` for AFL returned empty injuries — no data from `latest-injuries.json`
2. `/signals?sport=AFL` `games_summary` showed only rules model lines, not ML model lines
3. `get_game_context` tool had no `sport` param — Claude couldn't explicitly specify AFL when needed
4. System prompt had no chaining instruction — Baz wouldn't auto-drill into game context after seeing matrix signals

---

## Changes

### baz_server.py

**Paths:**
- Added `BETMATE_ROOT = Path(os.environ.get("BETMATE_ROOT", str(BASE_DIR.parent)))` — uses env var if set (wrapper scripts), falls back to `BASE_DIR.parent` (= `Apps/`) when started via `start_baz.ps1`
- Added `AFL_INJURIES_JSON = BETMATE_ROOT / "data/afl/injuries/processed/latest-injuries.json"`

**New helpers:**
- `_load_afl_injuries()` — reads `latest-injuries.json`, returns `{team_name: [{player, status, notes}]}`
- `_team_injury_str(injuries_by_team, team)` — finds team (exact or contains match), returns comma-separated `"Player (status)"` string, capped at 8 players

**`_context_afl()`:**
- Now loads `afl_injuries` and injects `injuries_home`/`injuries_away` per game via `_team_injury_str()`
- Also fixed a bug: was reading `round_number` for both `season` and `round_num` — now correctly reads `season` column for season

**`_context_game_afl()`:**
- Now injects injuries from `latest-injuries.json` into the `injuries` key

**`/signals` endpoint:**
- `games_summary` now includes `ml_hcap` (= `ml_model.margin`) and `ml_total` when present (AFL games only)
- `games_summary` now includes `injuries_home`/`injuries_away` when non-empty (both sports)

### app/api/chat/route.ts

**`get_game_context` tool schema:**
- Added optional `sport` param (`enum: ['NRL', 'AFL']`) so Claude can explicitly specify sport

**`executeTool` — `get_game_context` case:**
- Now uses `input.sport ?? sport` so Claude-specified sport overrides the request-body default

**`formatSignalsResponse`:**
- `games_summary` type extended to include `ml_hcap?`, `ml_total?`, `injuries_home?`, `injuries_away?`
- ML lines rendered as `[ML hcap X, ML total Y]` suffix when present
- Injuries rendered as indented lines under each game when non-empty

**System prompt:**
- Added explicit CHAINING RULE: after `get_round_signals` identifies a matrix signal game, Claude must immediately call `get_game_context` for that game in the same turn

---

## What Baz can now do for AFL

| Before | After |
|--------|-------|
| `get_game_context` AFL: no injury data | Injuries from `latest-injuries.json` injected per team |
| `/signals` games summary: rules lines only | Shows rules + ML model lines side by side |
| Claude guessed sport from request body | Claude can explicitly pass `sport=AFL` to `get_game_context` |
| Baz answered on signals alone | Now chains into `get_game_context` when a signal game is identified |

---

## Files changed

| File | Change |
|------|--------|
| `BettingEngine/baz_server.py` | BETMATE_ROOT path, AFL_INJURIES_JSON, `_load_afl_injuries()`, `_team_injury_str()`, injuries injected into `_context_afl()` + `_context_game_afl()`, ML data + injuries in `/signals` games_summary, season bug fix |
| `app/api/chat/route.ts` | `sport` param on `get_game_context` tool, `gameSport` in executeTool, extended `formatSignalsResponse` types + ML/injury rendering, chaining rule in system prompt |

---

## Pending (Phase 3)

1. True MCP server — convert `baz_server.py` to proper MCP protocol (post-season)
2. AFL weather — not in AFL CSV or this server; would need a separate venue lookup + Tomorrow.io call
3. AFL market H2H — currently zeroed out (no live odds in AFL context); could extract from `oddsContext` in route.ts and match by team name
