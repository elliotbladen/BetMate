# 2026-08-18 — Baz Tunnel Removal + Engagement Overhaul

## Session 1: Tunnel removal + data fix

User tried to use Baz on betmate.au — it responded but said all data was stale for both NRL and AFL. Investigated and found:

- `BAZ_TUNNEL_TOKEN` is not set in `.env.local` on this (home) machine
- Without the token, `baz_server.py` returns 503 on every endpoint except `/health`
- Health check passes, so Baz appears "online" but serves no context
- The chat route gets empty context, so Claude (the Baz voice) says "data is stale"

The pricing CSVs are fine — R25 NRL and R24 AFL both exist in `results/`. The DB has NRL up to R25. AFL has no matches in model.db (AFL pricing runs from CSVs, not DB).

### Decision: Delete Cloudflare Tunnel

User thought the tunnel had already been removed. It hadn't — the architecture docs still described it as live. User confirmed a new direction:

**Baz becomes a local agent with dual data access:**
1. BettingEngine (local) — pricing CSVs, matrices, ML shadow, line movement
2. BetMate (Supabase) — odds, predictions, team news, movements, history

No tunnel, no token auth, no exposed server. Same security guarantee (pricing IP stays local).

Full updated direction doc: `handover/baz_v2_direction.md`

### Tear-down needed (work machine)
- Delete Cloudflare tunnel `betmate-baz` from dashboard
- Remove `BAZ_TUNNEL_TOKEN` + `BAZ_TUNNEL_URL` from Vercel env
- Remove `~/.cloudflared/config.yml`
- Remove "BetMate Baz Brain" Task Scheduler task
- Remove `scripts/start_baz.ps1`
- Clean up `baz.betmate.au` DNS CNAME

### Baz data pipeline fixes
- Removed token auth from `baz_server.py` (tunnel deleted, server is local-only)
- Ran `push_baz_context.py` to push NRL R25 + AFL R24 context to Supabase
- Fixed `nrl_fixture` staleness: was stuck on R19 in Supabase, updated to R25
- Added automatic fixture/predictions authority key sync to `push_baz_context.py` — now keeps `nrl_fixture`/`afl_predictions` in sync when pushing context, preventing future staleness rejections

### IP guardrail fixes
- Baz was refusing to share model predictions (said "fair odds" which triggered sanitiser)
- Removed over-blocking patterns from `LEAKED_IP_PATTERNS`: "fair price/odds/line", "model odds/price"
- Added system prompt instruction: say "the numbers have them at $X" not "fair odds"
- Guardrail now protects HOW the model works (tiers, formulas, ELO numbers) but freely shares WHAT it predicts (scores, margins, model odds)

### Team form fix
- `get_team_form` and `get_head_to_head` tools were only looking at current round context
- Rewired both to read from `nrl_match_history`/`afl_match_history` in Supabase
- Now returns last 6 games with W/L record, scores, opponents, venues

### brainOnline header fix
- `X-Baz-Brain: agent` wasn't recognised as "online" in ChatPanel
- Added `'agent'` to the check — fixes the "Brain offline" amber banner showing on successful responses

---

## Session 2: Engagement overhaul

### Research findings
User asked: "how do really good chatbots keep the user chatting?"

Research from web sources confirmed:
- Quick reply buttons: 3x higher completion rates, 40% more likely to continue
- Optimal chatbot response: 2-3 sentences for standard queries, max 500 characters for "thorough but concise"
- Mobile users scroll past long messages — chat is designed for short bursts
- Sports betting chatbots that work: instant, contextual, conversational — not essays
- Suggested actions should be contextual to what was just discussed, not generic

### What was built

**1. Quick reply buttons (system prompt + UI)**
- System prompt now instructs Baz to end every response with `---SUGGESTIONS---["button1","button2","button3"]`
- `ChatPanel.tsx` parses the delimiter, strips suggestions from displayed text
- Renders 2-3 clickable pill buttons below the latest assistant message
- Clicking a button sends that text as a new user message
- Guard replies (off-topic, IP, weekly scope) also include suggestion buttons
- Sanitiser updated to only check body text, not the suggestions block

**2. Response length reduction**
User flagged that round overview responses were ~350 words — "basically an assignment." Research backed this up.

Changes to system prompt:
- Hard 4-5 sentence limit per response
- Round overviews: top 2-3 standout angles only, NOT all 8-9 games
- Game-specific questions: lead with ONE key angle, let buttons handle drill-down
- "Think TEXT MESSAGE, not email"
- Gambling disclaimer first message only, not every response
- `max_tokens` reduced from 700 to 400

Before/after word counts:
| Question | Before | After | Change |
|----------|--------|-------|--------|
| Round overview | ~350 words | ~123 words | -65% |
| Team form | ~130 words | ~55 words | -58% |
| Ref question | ~65 words | ~38 words | -42% |

**3. Welcome message updated**
Old: Long explanation of what Baz can do
New: "G'day, I'm Baz. Got the full round data loaded up -- injuries, refs, venue reads, the lot. What are you looking at this week?"

**4. Initial suggested questions updated**
Old: "Why is Peter Gough whistle heavy?" / "Explain the EV calculation"
New: "What stands out this NRL round?" / "Best AFL value play this week?" / "Any big injuries this round?"

### Testing
- Ran 20-question test against live endpoint — 100% suggestion button rate
- All responses contextual, all buttons relevant to what was discussed
- Post-shortening test: responses fit on one phone screen

### Commits
1. `493fbf8` — Add Baz engagement features: quick reply buttons + follow-up hooks
2. `36daff7` — Fix brainOnline check to recognise 'agent' header status
3. `94aa565` — Shorten Baz responses: 4-5 sentence max, no full-round dumps

---

## Other work this session
- AFL/NRL drift study: Melbourne shortened 7/20 (35%), Bulldogs 6/20 (30%) in 2026
- Full 18-team "thrives on the drift" analysis: Fremantle (80%), Adelaide (67%), Melbourne (62%) top drift survivors
- Last 4 Melb vs Dogs meetings: Bulldogs won 3 of 4, totals went OVERS 3 of 4
- User's R24 strategy: Saints vs Suns UNDERS as main play. Melbourne vs Bulldogs — wait for line movement, bet early if Melbourne shortens, bet late if they drift
