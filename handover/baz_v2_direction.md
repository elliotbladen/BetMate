# Baz v2 — Local Agent with Dual Data Access
**Updated:** 2026-08-18 (replaces tunnel-based architecture — Cloudflare tunnel deleted)
**Previous:** 2026-07-09 (per-game betting desk taxonomy — still the feature spec)

## Architecture Change (2026-08-18)

**Old model:** Baz ran as a FastAPI server (`baz_server.py` on localhost:8765), exposed to
the internet via Cloudflare Tunnel (`baz.betmate.au`), authenticated with `BAZ_TUNNEL_TOKEN`.
The Vercel chat route called Baz through the tunnel to fetch context before calling Claude.

**New model:** Baz is a **local agent** that pulls from two data sources directly:

1. **BettingEngine (local)** — pricing CSVs, model outputs, matrices, ML shadow,
   line movement predictions, confluence JSON, training data. Read directly from disk.
2. **BetMate (Supabase)** — odds, predictions, team news, movements, history,
   BVI — everything already pushed there by the weekly pipeline.

No tunnel. No token auth. No exposed server. The pricing IP stays local (same security
guarantee as before), and the website data comes via Supabase reads instead of requiring
a live connection to the user's machine.

**What this means for the chat route:** `app/api/chat/route.ts` no longer calls
`BAZ_TUNNEL_URL` / `BAZ_LOCAL_API`. It reads context from Supabase (predictions, odds,
team news are already there) and passes it to Claude directly. The BettingEngine deep
context (tier breakdowns, matrix signals, ML shadow) is available when running locally.

---

## Tear-Down Checklist

- [ ] Delete Cloudflare tunnel `betmate-baz` (ID: `ce4bfb19-82f6-4ffe-af06-e2c65636a323`) from Cloudflare dashboard
- [ ] Remove `BAZ_TUNNEL_TOKEN` from Vercel env vars
- [ ] Remove `BAZ_TUNNEL_URL` from Vercel env vars
- [ ] Remove `~/.cloudflared/config.yml` on work machine
- [ ] Update `app/api/chat/route.ts` — remove tunnel fetch, read from Supabase instead
- [ ] Remove token auth middleware from `baz_server.py` (or retire the file entirely once chat route is rewired)
- [ ] Remove "BetMate Baz Brain" Task Scheduler task on work machine
- [ ] Remove `scripts/start_baz.ps1` (starts server + tunnel)
- [ ] Clean up DNS: remove `baz.betmate.au` CNAME from Cloudflare

---

## The Question Taxonomy (unchanged from v1 — this is still the feature spec)

Baz v2 is done when every row has a tick for both sports.

| # | Question class | Example | Status |
|---|---------------|---------|--------|
| 1 | **Value** | "Who should I bet on here?" | NRL tick, AFL needs market join |
| 2 | **Reasoning** | "Why does the model like the Sharks?" | NRL tick, AFL tier notes empty |
| 3 | **Price / line shopping** | "What's the best price on Storm?" | Needs odds snapshot access |
| 4 | **Movement / timing** | "How's this line moved since Monday?" | Needs movement data access |
| 5 | **History** | "H2H record?" | Supabase has it, needs wiring |
| 6 | **Situational** | "Does the ref matter?" | NRL tick, AFL umpire data missing |
| 7 | **Staking** | "How much should I put on it?" | Needs Kelly/unit policy |
| 8 | **Accountability** | "How's the model been going?" | Working |
| 9 | **Derived markets** | "What about alt line -13.5?" | Phase 3 (needs distribution) |

---

## Build Phases (updated for new architecture)

### Phase 1 — Rewire (remove tunnel, connect to Supabase)
1. Strip tunnel/token infrastructure (see tear-down checklist above)
2. Update chat route to read predictions + odds + team news from Supabase
3. Fix AFL market join — populate EV from odds snapshot data in Supabase
4. Wire matchup history from Supabase (`nrl_match_history` / `afl_match_history`)

### Phase 2 — Coverage (close the gaps in the taxonomy)
1. Odds/line shopping — read per-bookmaker prices from snapshots in Supabase
2. Movement/timing — expose movement data + causal tags
3. Staking guidance — fractional Kelly, advisory only

### Phase 3 — Depth (after Phases 1-2 prove out)
- Alt-line pricing (margin/total distribution)
- Timing engine (when market-event pipeline has a season of data)
- AFL umpire layer if data source materialises

---

## Hard Rules (unchanged)
- **Baz is advisory only — never places bets**
- Pricing IP never leaves the local machine
- Model alignment rule: if rules + ML disagree, Baz says "no bet"
- Sample-size honesty on matrix signals (N<10 = anecdote)
- State known model biases (NRL totals run high, AFL extreme-ELO undercook)

## Out of Scope
Telegram delivery, crypto agent, self-learning/auto-retraining, autonomous betting,
proactive alerts. Baz answers questions; he doesn't push.
