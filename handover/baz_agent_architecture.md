# Baz Agent Architecture
**Created:** 2026-05-15

---

## The Core Idea

Baz has two parts:

1. **Voice** — lives on BetMate. The Anthropic Claude API. The personality, the chat UI, the language.
2. **Brain** — lives in BettingEngine. The 7-tier model, signals, ELO, injuries, CLV. All local. Never online.

The key insight: the **model itself never leaves the machine**. Only the *outputs* — plain-English summaries of what the model found — travel to Anthropic's API. If someone intercepted the API call they'd see "Dolphins have a 23% edge on H2H at 2.10" — not the model weights, not the config, not the tier logic.

---

## Security Model

```
What stays LOCAL (BettingEngine):
  ├── data/model.db           — all historical data, ELO, results
  ├── pricing/ tier1-8        — the model logic
  ├── config/tiers.yaml       — all weights and thresholds (the IP)
  ├── results/rN_pricing.csv  — raw signal outputs
  └── data/bets/              — your actual bet history

What goes ONLINE (Anthropic API):
  └── A plain-English context summary:
      "Round 11. Dolphins vs Wests. Model: Dolphins -8.5 (fair).
       Market: -6.5. EV: 18%. Injury flag: Tigers spine disrupted.
       Referee: Cummins (high penalty bucket)."
      → Claude turns this into Baz's response
```

Nobody can steal what never leaves your machine.

---

## Architecture Diagram

```
                        USER
                          │
                          │ asks Baz a question
                          ▼
              ┌─── BetMate (Next.js) ───────────────┐
              │                                      │
              │  ChatPanel.tsx                       │
              │    └→ POST /api/chat                 │
              │                                      │
              │  app/api/chat/route.ts               │
              │    │                                  │
              │    ├─1─ Fetch context from            │
              │    │    localhost:8765/context        │
              │    │    (BettingEngine local server)  │
              │    │                                  │
              │    ├─2─ Build enriched prompt:        │
              │    │    SYSTEM + round_context        │
              │    │    + signals + injuries + CLV    │
              │    │                                  │
              │    └─3─ Call Anthropic Claude API ────┼──→ Claude generates
              │                                      │         response
              └──────────────────────────────────────┘
                          │
                          │ (localhost only, never internet)
                          ▼
              ┌─── BettingEngine (Python) ───────────┐
              │                                      │
              │  baz_server.py (FastAPI)             │
              │  Listens: localhost:8765             │
              │  NOT exposed to internet             │
              │                                      │
              │  Endpoints:                          │
              │  GET /context/round                  │
              │    └→ current signals, key games,    │
              │       top EV opportunities           │
              │                                      │
              │  GET /context/game?home=X&away=Y     │
              │    └→ model price, EV, tier flags    │
              │       injuries, referee, weather     │
              │                                      │
              │  GET /context/team?team=X            │
              │    └→ ELO, recent form, injury status│
              │       home/away record, style        │
              │                                      │
              │  GET /signals                        │
              │    └→ current round signals ≥20% EV  │
              │                                      │
              │  GET /clv                            │
              │    └→ recent CLV performance summary │
              │                                      │
              │  Reads from:                         │
              │  ├── data/model.db                   │
              │  ├── results/rN_pricing.csv           │
              │  └── data/bets/actual_bets_2026.csv  │
              └──────────────────────────────────────┘
```

---

## What Baz Knows (Context Injection)

When a user asks Baz anything, before calling Claude, BetMate fetches from the local server:

```json
{
  "round": 11,
  "sport": "NRL",
  "generated_at": "2026-05-15T18:30:00",
  "signals": [
    {
      "home": "Melbourne Storm",
      "away": "Wests Tigers",
      "market": "H2H",
      "model_odds": 1.22,
      "market_odds": 1.30,
      "ev_pct": 22.4,
      "kelly_stake": 0.8,
      "tier_flags": ["Tigers spine disrupted (T5)", "Cummins ref - high penalties (T6)"]
    }
  ],
  "key_injuries": [
    { "team": "Wests Tigers", "player": "Luki Fui Fui", "role": "hooker", "tier": 1, "status": "out" }
  ],
  "model_summary": "3 signals above threshold. Storm, Roosters, Dolphins flagged.",
  "clv_last_4_weeks": { "profit": 4.2, "roi": 0.14, "win_rate": 0.61 }
}
```

This gets injected into Baz's system prompt as context. Claude then answers in Baz's voice using real model data.

---

## Graceful Degradation

If BettingEngine server isn't running (e.g. it's Saturday and you haven't started it):

```
BetMate tries localhost:8765 → times out after 1 second
    ↓
Falls back to: base Baz prompt (no model context)
    ↓
Baz still works — just answers from general NRL/AFL knowledge
    ↓
UI shows: "Brain offline — Baz running on general knowledge only"
```

No crashes. No errors shown to the user. Baz degrades gracefully.

---

## Starting Baz's Brain

```powershell
# Start the local context server (run before using Baz on big game days)
& C:\Users\ElliotBladen\Apps\BettingEngine\.venv\Scripts\python.exe baz_server.py

# Or as a background task
Start-Process -NoNewWindow python "C:\Users\ElliotBladen\Apps\BettingEngine\baz_server.py"
```

Alternatively: add a Task Scheduler task that starts it Tuesday morning and keeps it running all week.

---

## Files Changed / Created

**BettingEngine (new):**
- `baz_server.py` — FastAPI local context server

**BetMate (modified):**
- `app/api/chat/route.ts` — fetches local context before calling Claude
- `.env.local` — add `BAZ_LOCAL_API=http://localhost:8765`

---

## Future: MCP Server

When ready to go further, replace the FastAPI server with an MCP (Model Context Protocol) server. MCP is Anthropic's standard for giving Claude tools to call directly — instead of injecting context into the prompt, Claude can call `get_signals()`, `get_team_form()`, `query_db()` as tools mid-conversation.

This gives Baz genuine agency: he can ask for more data mid-conversation, not just use whatever was pre-loaded.

Architecture for MCP is already planned in `handover/MCP_PREP.md`.
