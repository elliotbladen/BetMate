# 2026-07-08 — Work/home machine divergence reconciled + architecture hardening

> Written retrospectively on 2026-07-09 — this diary was referenced from CLAUDE.md but
> never actually written at the end of the Jul 8 session. Reconstructed from commit
> `cefe758`, CLAUDE.md/BettingEngine CLAUDE.md updates, and the working-tree diffs.

## The incident

The user works on this repo from two computers. The home machine's monorepo import
commit (`6192faa` "Import BettingEngine into BetMate monorepo") carried a **stale
BettingEngine copy**, while the work machine's working tree held the live production
state — Jun 18 calibrations, Jul 2 AFL R17 pricing, Jul 3 market-event pipeline,
Jul 7 T10/tier-coverage work, and the 118-bet ledger — all **uncommitted**. Meanwhile
the Jul 5 EPL engine and Jul 5 AFL ML EMA retrain existed **only in git history**
(committed from home, "deleted" in the work tree).

Each side held work the other lacked. A blind `git pull` or `git checkout --` on
either machine would have destroyed one side.

## Reconciliation (commit `cefe758`)

- All 50 "deleted" files restored from HEAD: EPL engine tree
  (`BettingEngine/WorldCupEngine/ml/epl/`), Jul 5 EPL diary, script archives,
  NRL api-round placeholders
- `ml/afl/*` reset to HEAD — the Jul 5 EMA/split-feature retrain code is newer
  than the local copies
- Every other modified file kept from the work machine (the newer side)
- `BettingEngine/CLAUDE.md` hand-merged: local base + HEAD's EPL and AFL-ML sections

## Prevention — TWO-MACHINE RULE (see CLAUDE.md)

- `scripts/git-sync-start.ps1` — run at session start. Refuses to pull over a dirty
  tree, `--ff-only`, never auto-merges divergence.
- `scripts/git-sync-end.ps1 "message"` — run at session end. Commits everything and
  pushes. Never leave a machine with uncommitted work.
- `git config pull.ff only` set on the work machine — **still to do on home machine**.

## Other work this session

- **Baz tunnel auth** (`BettingEngine/baz_server.py` + `app/api/chat/route.ts`):
  the Cloudflare tunnel exposes baz_server to the internet and CORS doesn't stop
  curl/scripts, so every request except `/health` now requires an `X-Baz-Token`
  header matching `BAZ_TUNNEL_TOKEN` (in `Apps/.env.local` locally; **must also be
  set in Vercel env** or the live site's Baz goes offline at next server restart).
  Also added `/status` and `/db/signals` endpoints.
- Root README rewritten to match actual monorepo architecture.

## Outstanding after this session (state as of Jul 8)

- AFL ML `.pkl` models on the work machine were still the pre-EMA Jun 4 pickles
  (pkls don't travel via git) — **regenerated 2026-07-09**, see next diary.
- Diary `2026-07-05_afl-ema-form-split-models.md` exists only on the home computer —
  commit + push it from there.
- `BAZ_TUNNEL_TOKEN` needs setting in Vercel env before the new baz_server code runs.
- Home machine: set `git config pull.ff only`.
