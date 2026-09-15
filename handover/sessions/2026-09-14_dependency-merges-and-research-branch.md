# 2026-09-14 — Dependency PR sign-off, research branch merge

Short housekeeping session. Owner asked for everything open to be signed off and
merged **except PR #14** (fitness/trials — they are doing that themselves).

## What landed on main (`32f4915`)

1. **AFL R27 Monday line-movement forecast + pipeline logs** (`4c1aa11`) — routine
   automated output that was sitting uncommitted: availability forecast and
   predictions for R27 Monday stage, launchd/market-intelligence log rotation,
   one refreshed Championship player match feed.
2. **PR #26 — Dependabot minor/patch group** (6 updates).
3. **PR #28 — `@types/node` 20.19.41 -> 26.5.0.**
4. **`research/nrl-totals-matrix-v2-hitrate`** — 3 commits: hit-rate totals
   matrix v2, the 2023-26 matrix built for 2027, local viewer, and the
   2026 line-jump evidence note.

`review/fitness-signoff` was **not** merged — it is byte-identical to
`origin/feat/fitness-trials-engine` (0 commits either way), i.e. it *is* PR #14,
which the owner is handling.

## Three dependency PRs HELD — each breaks tooling, reasons commented on the PRs

⚠️ **All three showed CI SUCCESS.** `.github/workflows/ci.yml:41` sets
`continue-on-error: true` on the eslint step, so a completely dead linter still
reports green. This is the repo's documented characteristic failure — a green
light over a dead component — and it is worth knowing that **the eslint step in
CI currently cannot fail.**

Their Vercel FAILURE checks were a red herring: #27-#30 were all cut from
2026-09-12 main, which predates `d0737dc` (13 Sep, the /api/ev-signals 2.49GB
function-tracing fix). #26 was rebased onto post-fix main and was Vercel-green.
So the Vercel failures were the old tracing bug, not the bumps.

| PR | Bump | tsc | build | lint | Verdict |
|----|------|-----|-------|------|---------|
| #27 | typescript 5.9.3 -> 7.0.2 | clean | green | **exit 2, crash** | HELD |
| #29 | eslint 9.39.5 -> 10.10.0 | clean | green | **exit 2, crash** | HELD |
| #30 | tailwindcss 3.4.19 -> 4.3.3 | — | **exit 1, fails** | — | HELD |

- **#27 (TS 7):** `typescript-eslint does not support TS 7.0`, thrown from
  `eslint-config-next/node_modules/typescript-eslint`. Upstream tracking
  issue typescript-eslint#10940 targets TS >= 7.1. tsc and the build are
  genuinely fine — the only casualty is that eslint can no longer run at all.
- **#29 (ESLint 10):** `TypeError: contextOrFilename.getFilename is not a
  function` in `eslint-plugin-react` (bundled under `eslint-config-next@16.3.4`).
  **Reproduced with TypeScript pinned back to 5.9.3**, so this is ESLint 10 on
  its own, independent of #27. The two bumps break lint for separate reasons.
- **#30 (Tailwind 4):** hard build failure — a version bump with none of the
  Tailwind 3 -> 4 migration. Needs `@tailwindcss/postcss` in `postcss.config.js`,
  `@import "tailwindcss"` in `app/globals.css`, and the theme moved to CSS-first
  `@theme`. **Merging this takes the site down, not just the linter.**

## Verification

Baseline established before touching anything (main, pre-merge): build green.
Each merge was built one at a time, per the CLAUDE.md instruction.

Final state on main:
- `npx tsc --noEmit` — exit 0
- `npm run lint` — exit 1 with **61 problems (30 errors, 31 warnings)**, i.e.
  identical to baseline. The linter *works*; these are the long-standing
  pre-existing findings CI was already tolerating.
- `npm run build` — exit 0
- BettingEngine pytest — **244 passed, 3 failed**, the documented pre-existing
  pyarrow failures (`test_market_intelligence_refresh`, 2x
  `test_nfl_step13_backtest`). Unrelated to this merge.

Installed after merge: `@types/node@26.5.1`, `typescript@5.9.3`,
`eslint@9.39.5`, `tailwindcss@3.4.19`, `@anthropic-ai/sdk@0.125.0`,
`@supabase/ssr@0.12.7`.

Note on #26: it carried two **0.x** bumps where minor can be breaking —
`@anthropic-ai/sdk` 0.88 -> 0.125 and `@supabase/ssr` 0.7 -> 0.12. Call sites
checked: `app/api/chat/route.ts` (standard `messages.create` + `ToolUseBlock`
tool-use loop) and `createServerClient`/`createBrowserClient` in
`lib/authServer.ts`, `lib/supabase.ts`, `app/auth/callback/route.ts`. All
type-check under the new versions, but **the chat tool-use loop and auth flow
were not exercised at runtime** — worth a click-through.

## Next

1. **Ask Baz and the auth flow have not been runtime-tested** against
   `@anthropic-ai/sdk@0.125` / `@supabase/ssr@0.12`. Type-checking passed; that
   is not the same as the agentic loop working.
2. **The UI still has not been checked in a browser** since Next 16 (standing
   item, now with two 0.x dependency bumps on top).
3. Consider flipping `continue-on-error: true` off the eslint CI step once the
   61 findings are cleared — until then CI cannot tell you the linter is dead.
4. #27/#29 re-test when eslint-config-next ships support; #30 needs the real
   Tailwind 4 migration, not a bump.
5. `app/api/chat/route.ts:674` still pins `model: 'claude-sonnet-4-6'` — noted,
   not changed, out of scope for this session.

A local backup tag `backup/merge-chain-*` was left at the discarded merge chain
(the one that briefly included TS 7 and @types/node stacked together). Safe to
delete.
