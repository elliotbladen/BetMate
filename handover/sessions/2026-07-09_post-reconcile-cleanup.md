# 2026-07-09 — Post-reconcile cleanup (work machine)

Continuation of the 2026-07-08 reconcile session: "continue fixing everything, don't
fix Baz." Baz code (`baz_server.py`, `app/api/chat/route.ts`) was left exactly as the
Jul 8 session left it — committed as-is under the sync-end protocol, no changes.

## What was fixed

1. **AFL ML pkl models regenerated** with the restored Jul 5 EMA/split-feature code
   (the on-disk pickles were the pre-EMA Jun 4 versions — pkls don't travel via git).
   - `game_log.py` on the Jul 7 xlsx: 999 rows, splits train=639 / test=216 / deploy=144
   - `train.py`: Margin MAE **29.27** / DirAcc 68.5%, Total MAE **24.48**,
     H2H Acc **68.5%** / LogLoss 0.576 (test = 2025)
   - EMA features confirmed live: `opp_adj_margin_diff` is the #1 margin feature (8.8%)
   - Metrics differ slightly from the home machine's diary (28.5 MAE / 71.8% H2H) —
     expected, this xlsx is a newer download. Same code, same splits.

2. **Stale nested `BettingEngine/.git` removed from the tree.** Left over from before
   the monorepo import — any git command run from inside `BettingEngine/` was silently
   operating on the old pre-import repo (wrong history, old remote). Verified first:
   all commits pushed to github.com/elliotbladen/BettingEngine, no unpushed branches,
   one stale May-11 WIP stash. **Moved (not deleted)** to
   `C:\Users\ElliotBladen\Backups\BettingEngine-pre-monorepo.git` — full old history
   + stash preserved there. `git rev-parse --show-toplevel` from inside BettingEngine
   now correctly returns the monorepo root.

3. **Root `.pytest_cache/` gitignored.** The dir was created by an elevated process
   (ACLs unreadable even for listing) and made every git command print
   "could not open directory '.pytest_cache/': Permission denied". Ignoring the dir
   stops git descending into it; warning gone. The dir itself can only be deleted
   from an elevated shell if the user wants it gone.

4. **Missing reconcile diary written** — `2026-07-08_machine-reconcile-architecture.md`
   was referenced from CLAUDE.md but never created. Reconstructed from commit
   `cefe758` and the CLAUDE.md notes.

5. **CLAUDE.md (root + BettingEngine) updated** to mark the pkl retrain done and
   record the nested-.git removal.

6. **`npm run build` verified passing** before push (push auto-deploys to Vercel).
   The pending chat-route change is deploy-safe: it only sends `X-Baz-Token` if
   `BAZ_TUNNEL_TOKEN` is set in the environment.

## Baz direction change (later same day)

User dropped the May 2026 Baz roadmap entirely — alert types (get on early / leave
late / sharp / public / value), Telegram delivery, the crypto-twin agent, the
self-learning tiers, and the 6-step build order. **A different angle is coming but
was not articulated this session.** Deprecation banners added to
`handover/baz_agent_architecture.md` and the CLAUDE.md Product Vision section;
Claude memory files updated. What survives: the built infrastructure (MCP tool-use
loop, tunnel + token auth, Voice/Brain IP split) and the advisory-only principle.
Next Baz session: get the new angle from the user first.

**Update (same day):** new angle defined — **Baz v2: answer ALL bet-related questions
for a game.** Full plan written to `handover/baz_v2_direction.md` (question taxonomy,
gap analysis, 3 phases). Key finding from the gap analysis: AFL `/context/game`
returns zeroed `market`/`ev` and empty `tier_adjustments` — Baz can't do
model-vs-market for AFL at all. That's Phase 1 item 1. No code touched this session
(Baz code changes were explicitly out of scope).

## Still outstanding (not done this session)

- **`BAZ_TUNNEL_TOKEN` must be set in Vercel env** before the local Baz server is
  restarted on the new code, or live-site Baz will 401. (Baz explicitly out of scope
  this session.)
- Home machine: commit + push diary `2026-07-05_afl-ema-form-split-models.md`,
  set `git config pull.ff only`, and regenerate its own pkls after pulling.
- From the Jul 8 WC pricing diary: re-run Argentina/Switzerland script when the Swiss
  squad news drops (Embolo/Manzambi); Kansas City missing from `VENUE_CONTEXT`;
  WorldCupEngine `bracket.py` R32 pairings diverged from reality (prices don't
  depend on it).
