# Session 2026-05-15 — Baz Agent Build

## What was done

Built Baz as a local AI agent: brain stays on your machine (BettingEngine), voice goes online (Anthropic API). Model IP never leaves localhost.

### BettingEngine/baz_server.py (NEW)
FastAPI server on `localhost:8765`. Five endpoints:
- `GET /health` — liveness check
- `GET /context/round` — full round context: all 8 games, signals ≥20% EV, CLV summary
- `GET /context/game?home=X&away=Y` — focused game context with model vs market odds, tier notes
- `GET /context/team?team=X` — team form, ELO context, current injuries from DB
- `GET /signals` — signals-only view
- `GET /clv?weeks=N` — CLV summary for last N rounds

Reads from `results/r11_pricing_2026.csv` (always picks latest by mtime). CSV was Windows-1252 encoded — fixed with `encoding="cp1252"`.

FastAPI + uvicorn installed into `.venv` (had to bootstrap pip first via `ensurepip` — the bare venv had no pip).

### app/api/chat/route.ts (MODIFIED)
- Added `fetchBrainContext()` — fetches `/context/round` with 1.5s AbortController timeout
- Added `buildContextBlock()` — converts JSON context to plain-English block injected into Baz's system prompt
- Brain offline: falls back to base prompt + `[BRAIN OFFLINE]` note, no crash
- Prepends `\x00brain:online\x00` or `\x00brain:offline\x00` token to every streamed response so the UI can show the banner
- Sets `X-Baz-Brain` response header for completeness

### .env.local (MODIFIED)
Added `BAZ_LOCAL_API=http://127.0.0.1:8765`

### components/chat/ChatPanel.tsx (MODIFIED)
- Added `brainOnline` state (`boolean | null`)
- Stream parser strips the `\x00brain:...\x00` header token from the first chunk
- Amber banner: "Brain offline — Baz running on general NRL knowledge only" shown when brain is offline

**GOTCHA:** ChatPanel.tsx has a pre-existing double-encoding bug with box-drawing characters in JSX comments. The Edit tool inserts curly/smart quotes (U+201D) instead of ASCII quotes in className attributes, which TypeScript rejects. Fixed via PowerShell (`Replace([char]0x201C, '"')` etc.) but that was too aggressive (broke string content). Solution: used targeted PowerShell string replacement with CRLF-aware anchors. Future sessions: do NOT use the Edit tool on ChatPanel.tsx — use PowerShell manipulation only.

## Test results
- Server started, `/context/round` returned Round 11, 8 games, 0 signals above threshold ✅
- `/context/game?home=Storm&away=Eels` returned Eels vs Storm with correct model odds (3.61/1.383) ✅
- TypeScript build passes ✅

## What's next
- Start the brain before big game days: `cd BettingEngine && .\.venv\Scripts\python.exe baz_server.py`
- Consider Task Scheduler task to start baz_server Tuesday morning
- BVI weekly task still pending (install afl_bvi.py Monday 08:00)
- Signals are showing 0 because the EV% calculation uses market book odds from the pricing CSV (`h2h_home_105`) — these may not reflect current live market. The EV threshold comparison is correct but context-dependent on when pricing was run vs current market.
