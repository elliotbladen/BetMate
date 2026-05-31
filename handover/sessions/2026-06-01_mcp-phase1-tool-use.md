# Session Diary — 2026-06-01 — MCP Phase 1: Claude Tool Use

## What was done

### Problem
Baz was running on a single-pass static context dump (~4-6KB system prompt stuffed with all round data upfront). This approach:
- Forces a full context read even when the user asks a general question
- Gives Baz no ability to fetch additional data mid-conversation
- Can't reason about what it needs — always gets everything

### Solution: Claude Tool Use Loop

Replaced the static system prompt + streaming approach with a full agentic tool-use loop:
1. Claude receives a slim system prompt (~600 tokens) + round metadata
2. Claude decides what to fetch based on the user's question
3. Tools execute against baz_server endpoints
4. Claude generates the final response with the fetched data
5. Final text is streamed to the client

### Changes — baz_server.py

Added two new things:

**`_compute_matrix_and_totals(games)` helper:**
- Extracts matrix signals (H2H + handicap clean + aligned)
- Extracts totals signals (clean OVERS or UNDERS confluence)
- Returns both as compact lists for the signals endpoint

**`/meta?sport=NRL|AFL` endpoint:**
- Returns just `{round, season, sport}` — lightweight call to seed the system prompt
- No game data, no CSV parsing beyond the header row
- ~5ms round trip — fast enough to call on every request

**`/signals?sport=NRL|AFL` endpoint (enriched):**
- Was: only H2H EV ≥20% signals
- Now: matrix signals + totals signals + H2H EV signals + games summary (model lines)
- Returns: `{sport, season, round, matrix_signals, totals_signals, h2h_signals, games_summary}`

### Changes — app/api/chat/route.ts

Complete rewrite. Key structural changes:

**Slim system prompt:**
- No data dump — just persona + tool instructions
- Round metadata injected as one line: `"Current round context: NRL R13, Season 2026. Use get_round_signals to fetch this round's signals."`
- oddsContext still appended (live market prices from UI)

**4 tools defined (`BAZ_TOOLS`):**
```typescript
get_round_signals(sport: 'NRL' | 'AFL')  // matrix + totals + H2H signals
get_game_context(home, away)              // full game model/market/injuries/weather
get_team_context(team)                    // last 5 form + current injuries from DB
get_performance(weeks?)                   // CLV P&L / ROI / win rate
```

**Agentic loop (replaces single-pass stream):**
```typescript
// Non-streaming tool-use loop (max 5 iterations)
let response = await client.messages.create({ tools: BAZ_TOOLS, ... });
while (response.stop_reason === 'tool_use' && iterations < 5) {
  const toolResults = await Promise.all(toolUseBlocks.map(executeTool));
  convoMessages.push({ role: 'assistant', content: response.content });
  convoMessages.push({ role: 'user', content: toolResults });
  response = await client.messages.create({ ... });
}
// Stream final text
```

**Tool execution (`executeTool`):**
```
get_round_signals → GET /signals?sport=NRL|AFL
get_game_context  → GET /context/game?home=...&away=...
get_team_context  → GET /context/team?team=...
get_performance   → GET /clv?weeks=...
```

**Response formatters:**
- `formatSignalsResponse` — formats the enriched signals response for Claude
- `formatGameContext` — formats per-game data
- `formatTeamContext` — formats team form + injuries
- `formatClvContext` — formats CLV stats

**Brain status:**
- `fetchRoundMeta()` — calls `/meta` instead of `/context/round`. If null → brain offline.
- `\x00brain:offline\x00` token still sent first so UI can show the amber banner

---

## Live test result

Query: "Any value in NRL this round? What is the main signal?"

Baz response:
- Led with Cronulla Sharks (8-way H2H + 7-way handicap matrix signal)
- Surfaced Newcastle/Parra OVERS (3-way) and Wests/Bulldogs OVERS (4-way)
- Noted NRL totals model bias (runs 5-10pts high)
- Offered to drill into Cronulla vs Manly game context

Correct. Tool use loop fired once (get_round_signals), Claude reasoned over the data and responded.

---

## Architecture state after this session

```
User asks Baz a question
  → route.ts receives {messages, oddsContext, sport}
  → fetchRoundMeta(sport) → /meta → {round, season}   [~5ms]
  → System prompt: slim persona + round info + market prices
  → client.messages.create(tools=BAZ_TOOLS) [Claude API]
    → Claude decides: call get_round_signals
  → executeTool("get_round_signals", {sport}) → /signals?sport=NRL
    → baz_server enriches: matrix + totals + H2H + games_summary
  → Tool result returned to Claude
  → client.messages.create() [Claude API — final response]
  → Text streamed to client
```

### What Baz can now do that it couldn't before

| Before | After |
|--------|-------|
| Got ALL data upfront regardless of question | Fetches only what's needed |
| Couldn't call additional tools mid-conversation | Can call up to 5 tool rounds per response |
| 4-6KB context dump on every message | ~600 token system prompt + tool fetches |
| No game-specific drill-down unless pre-loaded | `get_game_context` fetches any specific game on demand |
| No team-level queries | `get_team_context` fetches form + injuries from DB |

---

## Pending (Phase 2)

1. **`get_game_context` for AFL** — currently routes to NRL CSV only. Add `sport` param and handle AFL columns.
2. **`get_round_signals` multi-call** — if user asks about a signal game, Baz should chain `get_round_signals` → `get_game_context` in one turn. Currently works (max 5 iterations), just needs prompting.
3. **True MCP server** — post-season. Convert baz_server.py to proper MCP protocol so any MCP-compatible client can query it.
4. **Vercel env vars** — `NEXT_PUBLIC_OWNER_EMAIL` and `OWNER_EMAILS` still need adding to Vercel dashboard manually (can't be done via code).
5. **Phase 2 baz_server enrichment** — `/context/game` needs `sport` param for AFL; add `signals` table read from model.db for per-market signals.

---

## Files changed

| File | Change |
|------|--------|
| `BettingEngine/baz_server.py` | Added `_compute_matrix_and_totals()`, `/meta?sport=` endpoint, enriched `/signals?sport=` |
| `app/api/chat/route.ts` | Complete rewrite — tool use loop, slim system prompt, 4 tools, formatters |
