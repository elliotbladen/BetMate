# 2026-09-11 (PM) — Next.js 16 upgrade and automatic tipping reminders

Both merged to `main`: **PR #11** (Next 14 → 16) and **PR #12** (tipping reminder cron).
`main` is now `71a7f24`.

## Next.js 14.2.35 → 16.3.4, React 18 → 19.3

**Why:** 14.2.35 patched the two CVEs Railway blocked on, but the 14.x line still
carried a tail of advisories including **two critical unauthenticated RCEs** only
fixed in 15.5.24+. `npm audit` no longer flags `next` at all. Remaining:
`@anthropic-ai/sdk` (moderate, breaking fix) and `xlsx` (**high, no upstream fix**,
local-only pipeline).

Migration used the official codemods and was small — 3 files for async request
APIs (`cookies()` x2, `params` x1). No `headers()`, no `draftMode()`, no server
actions, no parallel routes.

| change | note |
|---|---|
| `middleware.ts` → `proxy.ts` | ⚠️ **runtime change** — `proxy` is node-only and NOT configurable; middleware defaulted to edge. Supabase SSR works on node; gating verified (public 200, gated 401). |
| `images.domains` → `remotePatterns` | deprecated in 16 |
| `next lint` → `eslint .` | removed in 16; flat config added. The repo had **no eslint config at all** before, so 59 findings appeared at once — all pre-existing quality issues, none upgrade breakage, none fixed. |

### Two latent bugs the upgrade surfaced — neither caused by it

1. **A UTF-8 BOM in `app/globals.css`.** Webpack tolerated it for years; Turbopack
   (default builder in 16) fails to parse it. Only file in the repo with one.

2. **`lib/oddsSnapshotFallback.ts` loaded the entire odds archive per request** —
   `flatMap` over every CSV in `data/odds_snapshots`: **385MB, 41 files, 2.75M rows**,
   each becoming a 12-field object. Dev server OOM'd at 8GB on any `/api/odds/*`
   call. It only ever uses the latest snapshot, so it now reads newest-first and
   stops. **8GB crash → flat 60MB.** Untouched since 2026-07-28 and NOT a production
   issue: `data/` is gitignored so nothing deploys and `snapshotRoots()` is empty on
   Vercel. A local-dev bug the growing archive finally triggered.

Also pinned `turbopack.root` — Turbopack infers the workspace root from the nearest
lockfile and there is a stray `package-lock.json` in `$HOME` from April, so it was
treating `~/` as the root and trying to watch every file under it.

⚠️ **The UI was never visually inspected** — no browser tooling was available this
session. Merged on the owner's explicit instruction. A React 18→19 jump can change
rendering in ways HTTP 200s do not catch. **Worth clicking `/odds` at 375px** (the
`min-w-0` grid bug from May), the Ask Baz drawer, and the Details tabs.

## Tipping reminder cron

Daily Vercel cron at **09:00 UTC**: finds the next unlocked gameweek, and if it locks
within 48h emails every entrant with incomplete tips, recording each send so nobody
is nagged twice per round.

`app/api/cron/tipping-reminder/route.ts` · `lib/supabaseAdmin.ts` ·
`supabase/migrations/20260911_tipping_reminders.sql` (applied) · `vercel.json`

⚠️ **`createServerClient()` fails as success.** `lib/supabaseServer.ts` uses the ANON
key and, when that key is absent, returns a **no-op stub answering `[]` to every
query**. The first dry run reported "0 people to remind" and looked like a clean pass
having queried nothing. That shape is dangerous in an unattended job — hence
`lib/supabaseAdmin.ts`, which throws. It is needed anyway: the job reads `auth.users`
for addresses and writes `tipping_reminders`.

⚠️ `/api/cron` had to go in `PUBLIC_PATHS` or the proxy would 401 the cron before the
route ran. **It is not public** — the route requires `Authorization: Bearer
$CRON_SECRET` and refuses outright if the secret is unset. Verified 401 without it.

Bot entrants are excluded for free: `baz-bot` has no `auth.users` row, so no address.

### Email setup (done)

Resend, sending from betmate.au, **domain verified**. DKIM + SPF + MX confirmed live
from two external resolvers. ⚠️ **The DKIM value silently truncated on first paste —
88 of 218 characters.** Resend fails verification with an unhelpful error when this
happens; check the value ends `...8Wrd1wIDAQAB`. Region is ap-northeast-1 (Tokyo).

`RESEND_API_KEY` and `CRON_SECRET` are set in Vercel. **`RESEND_API_KEY` is NOT in
the local `.env.local`** (empty) — local sends will report "not configured".

## Baz GW4 tips

Submitted, all 10, favourites from the market prices in
`BettingEngine/outputs/football/epl/2026-27/gw04/1_model.json`. 7 home, 3 away, no
draws; the model agreed with the market on all ten. Baz sits on 45 pts from GW1-3.

⚠️ **`scripts/baz_tipping.py` is BROKEN and was not used.** Its
`data/epl/predictions/latest.json` was three rounds stale (GW2), and it matches
predictions to fixtures by **home team only**, never checking the opponent. It would
have tipped 9 of 10 games off the wrong opponent's odds — including Ipswich to win at
Selhurst and Forest at Villa Park. **Fix it before next week:** match on both teams,
and read from the priced gameweek output rather than `latest.json`.

## Open

1. **Verify the deploy** — `curl -H "Authorization: Bearer $CRON_SECRET"
   "https://betmate.au/api/cron/tipping-reminder?dry_run=1"`. This is the only way to
   confirm the Vercel env vars, which cannot be read back. Drop `dry_run` to send.
   **brendanturner has still not been emailed** and GW4 locks Sat 14:00 UTC.
2. **Click through the UI** after the Next 16 deploy.
3. **Railway: repoint at `main`** before deleting `feat/market-engine-cloud`.
4. **Market engine still has `ODDS_COLLECTION_LIVE_ENABLED=false`** — not collecting.
5. **Settle cards bets 2026-0118/0119** once football-data publishes 12-13 Sep.
6. Next 16 lint: 59 pre-existing findings now visible.
