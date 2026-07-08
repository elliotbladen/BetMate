# Baz v2 — The Per-Game Betting Desk
**Created:** 2026-07-09 (replaces the May 2026 roadmap — see deprecation banner in `baz_agent_architecture.md`)

## The One-Line Vision

**A user should be able to ask Baz any bet-related question about a game and get a
grounded, honest answer.** Not alerts, not Telegram, not a crypto twin — one job,
done completely: Baz is the betting desk for every game on the board.

Everything that survives from v1: the Voice/Brain IP split (pricing logic never
leaves the machine), the MCP tool-use loop, tunnel + token auth, and the hard rule
that **Baz is advisory only — he never places bets**.

---

## The Question Taxonomy (definition of "all bet-related questions")

This is the spec. Baz v2 is done when every row has a ✅.

| # | Question class | Example | Today | Gap |
|---|---------------|---------|-------|-----|
| 1 | **Value** | "Who should I bet on here?" / "Any value in this game?" | ✅ NRL / ⚠️ AFL | AFL `/context/game` returns market=0, ev=0 — model-vs-market join missing |
| 2 | **Reasoning** | "Why does the model like the Sharks?" / "How do the injuries change it?" | ✅ NRL / ⚠️ AFL | NRL has tier notes + explanation; AFL `tier_adjustments` is empty |
| 3 | **Price / line shopping** | "What's the best price on Storm?" / "Who's got -6.5?" | ❌ | No tool sees the odds board. Data exists (odds snapshots + Supabase) |
| 4 | **Movement / timing** | "How's this line moved since Monday?" / "Bet now or wait?" | ❌ | No tool sees `odds_movements`, deltas, or the causal-tagged events |
| 5 | **History** | "H2H record?" / "How do the Cats go at Marvel?" | ⚠️ | `/api/form` exists for the UI but Baz has no matchup-history tool; `get_historical_game_memory` covers only games WE priced/bet |
| 6 | **Situational** | "Does the ref matter?" / "What's the weather doing to the total?" | ✅ NRL / ⚠️ AFL | NRL refs wired; weather in both; AFL umpire data doesn't exist (known missing layer) |
| 7 | **Staking** | "How much should I put on it?" | ❌ | No Kelly/unit guidance exposed. Model has fair odds + EV — the math is trivial, the policy needs deciding |
| 8 | **Accountability** | "How's the model been going on totals?" / "What did we do on this fixture last time?" | ✅ | `get_performance` + `get_historical_game_memory` |
| 9 | **Derived markets** | "What about the alt line -13.5?" | ❌ (defer) | Needs a margin distribution, not a point estimate. Phase 3 |

---

## Build Phases

### Phase 1 — Coverage (close the ❌/⚠️ rows; this is most of the value)
Server side (`baz_server.py`):
1. **Fix the AFL market join** — populate `market` + `ev` in `_context_game_afl` from the
   latest odds snapshot, and fill `tier_adjustments` from the pricing CSV columns. This is
   the single highest-value fix: half of all games are AFL.
2. **New `/odds/game` endpoint** — per-bookmaker current prices for a game (h2h/line/total),
   best price per side flagged, plus movement timeline: opening (Monday baseline) → now,
   built from `data/odds_snapshots/` + `data/odds_movements/deltas/`. Include any causal
   tags from `data/odds_movements/tagged/` ("moved 4% after Tigers injury news Tue 10:12").
3. **New `/history/matchup` endpoint** — H2H last 6 + each team's venue record from the
   match-history data (same source as the UI History tab, `nrl_match_history` /
   `afl_match_history`).

Frontend (`app/api/chat/route.ts`): register three tools — `get_game_odds`,
`get_line_movement` (can share the `/odds/game` payload), `get_matchup_history`.
**Remember the middleware rule does not apply (chat route is server-side), but every
new baz_server endpoint must respect the `X-Baz-Token` auth.**

### Phase 2 — Judgment (make answers house-rule-compliant, not just data-rich)
Encode the house rules in the system prompt so every recommendation:
- States model line vs market line and **whether rules + ML agree** (the 2026-06-17
  model-alignment rule — if they disagree, Baz must say "no bet" even on strong matrix signals)
- Cites matrix confluence when present, with sample-size honesty (N<10 = anecdote)
- Applies known model biases (NRL totals run 5–10 high; AFL extreme-ELO-gap undercook)
- Gives staking as units off a fixed fractional-Kelly policy (policy to be agreed — default
  suggestion: ¼ Kelly, 1u cap) and always says "advisory only"
- Answers "bet now or wait?" honestly: until the market-event dataset matures, the answer
  is CLV-informed heuristics ("NRL CLV is +5% betting Tue/Wed — early has been fine"), not prediction

### Phase 3 — Depth (after Phases 1–2 prove out)
- **Alt-line pricing**: expose a margin/total distribution (ML residual σ) so Baz can price
  "Storm -13.5" instead of only the fair line
- **Timing engine**: when the market-event pipeline has a season of tagged data (check-in
  2026-07-24), graduate "bet now or wait" from heuristics to evidence
- AFL umpire layer if a data source ever materialises (known missing layer)

---

## Definition of Done / Evaluation

Keep a battery of ~30 real questions (3–4 per taxonomy row, both sports) in
`handover/baz_question_battery.md`. After each phase, run the battery against a live
round and score each answer: **grounded** (used real data), **honest** (stated limits),
**complete** (answered what was asked). Baz v2 ships when every taxonomy row passes
on both sports. No new scope until the battery passes.

## Explicitly Out of Scope (carried over from the v1 teardown)
Telegram delivery, crypto agent, self-learning/auto-retraining, autonomous betting,
proactive alerts. Baz answers questions; he doesn't push.
