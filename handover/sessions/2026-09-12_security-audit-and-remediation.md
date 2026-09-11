# 2026-09-12 — Security audit, and five of seven findings closed

Full report (artifact): https://claude.ai/code/artifact/cc2d1a58-1893-4f40-af02-84ff3f3dc2fd
Branch `security/audit-remediation`, commit `49ce0bc`.

## Scope

`app/`, `lib/`, `proxy.ts`, `supabase/migrations/`, `cloud/`, `scrapers/`,
`scripts/`, `BettingEngine/` at `b33de03`; full git history (405 commits); 27 API
routes; read-only probes of the live site. **Not covered:** the `mobile/`
workspace, the RacingEngine SQLite DB.

## Findings

| | Finding | State |
|---|---|---|
| F-01 | Tips readable before kickoff | ✅ fixed |
| F-02 | Tipping tables queried with the public anon key | ✅ code fixed, ⏳ **migration awaiting apply** |
| F-03 | `/api/chat` rate limit ineffective on serverless | ⏳ open |
| F-04 | `xlsx` ships to production, docs said local-only | ✅ docs corrected |
| F-05 | Server Supabase client failed as success | ✅ fixed |
| F-06 | Cron secret compared non-constant-time | ✅ fixed |
| F-07 | `pickle.load` on model artefacts | ⏳ open (low) |

## F-01 — the one that mattered

`app/api/tipping/tips/route.ts` GET authenticated the caller then took `user_id`
from the query string and returned **that** user's tips, never comparing the two.
Any signed-in entrant could read a rival's selections at any time — including
before kickoff — and tip against them.

**Tips going public once the round LOCKS is an intended feature and is preserved
exactly.** The handler already computed `isGameweekLocked()` but only used it to
guard the default-away backfill; the read is now gated on it too. `POST` was
always correct (uses `user.id`, discards any supplied id) — `GET` had not been
brought along, which is what made it look deliberate.

## F-02 — and the trap inside the fix

`tipping_comps`, `tipping_entries`, `tipping_tips` appear in **no migration** —
created by hand in the dashboard, so their RLS state cannot be established from
the repo. Every one of the sixteen migrated tables carries an explicit
`enable row level security`. Meanwhile the routes queried them with
`NEXT_PUBLIC_SUPABASE_ANON_KEY`, which ships in every browser.

⚠️ **The obvious fix would have taken tipping offline.** `createServerClient()` is
`createClient(url, anonKey)` with **no cookies forwarded**, so it carries no user
identity and `auth.uid()` is NULL in every query it makes. Enabling
`auth.uid() = user_id` policies against that matches nothing: empty leaderboard,
no tips, vanished entries. Caught before writing the migration, not after.

All five call sites now use `createAdminClient()` —
`app/api/tipping/{tips,join,leaderboard,results}/route.ts` and
`lib/tippingResults.ts` — matching `app/api/cron/tipping-reminder`. Route
authenticates, decides, then queries privileged.

**Because the service role bypasses RLS, the route checks stay load bearing.**
The policies are defence in depth: they stop the anon key reaching this data
directly, whatever the routes later get refactored into.

## F-05 — the failure mode that has already cost a day

`createServerClient()` returned a stub answering `[]` to every query and a null
session to every auth check, with `error: null`. A missing key was
indistinguishable from "no rows" — this produced the tipping dry run reporting
"0 people to remind" having queried nothing. It now throws. `getDataStore()`
still degrades to null for public display data but **logs** it.

Same family as the collector's `success`-on-idle fixed this morning, and as
`log_actual_bet.py` eating `week_ending`. Worth naming: **this codebase's
characteristic bug is a silent success, not a crash.**

## Verified clean

No secrets in 405 commits (JWT / `sk-` / `rlwy_` / `re_` / `AKIA` / `ghp_`).
`.gitignore` covers `.env*`; only `.example` files tracked. Service-role key
server-only, `supabaseAdmin` throws. RLS on all sixteen migrated tables,
deny-by-default. `product_events` correctly uses `auth.uid() = user_id`. No
`shell=True` / `eval` / `exec` / `verify=False` / unsafe `yaml.load` in Python.
`/api/tipping/*` correctly absent from `PUBLIC_PATHS`.

## Automation added

`.github/dependabot.yml` (npm + pip + actions, weekly) and
`.github/workflows/ci.yml` (gitleaks, `tsc`, eslint, `npm audit`, `pip-audit`).

Two deliberate calibrations: **audit gates on `critical`, not `high`**, because
`xlsx` has two HIGH advisories with **no upstream fix** and would fail every run
forever; and **eslint is `continue-on-error`** until the 59 pre-existing findings
are cleared. A gate that always fails gets ignored, and then it is not a gate.

Security headers in `next.config.js`. **No CSP** — Next injects inline scripts, so
a useful one needs nonces threaded through the app and a wrong one breaks the
site silently. Its own piece of work.

## Owner actions required

1. **Run the verification query** (in `20260912_tipping_rls.sql`) — tells you
   whether RLS was on these three tables all along.
2. **Apply that migration**, then exercise the tipping flow end to end.
3. **Set a monthly spend cap on the Anthropic key** — the single highest-value
   free control outstanding, because F-03 is unfixed and `/api/chat` is public.
4. **Enable 2FA** on GitHub, Supabase, Vercel, Railway, Resend.
5. **Turn on branch protection** for `main` once CI has run green once.

## Still open

- **F-03**: `/api/chat` rate limit is an in-memory `Map` on serverless — per
  instance, reset by cold starts, and the route is unauthenticated and calls a
  paid API. Needs a Supabase-backed counter.
- **F-07**: model `.pkl` files unpickled without checksums. Fine while they are
  locally generated; the risk arrives when one arrives from elsewhere.
- **CSP** with nonces.
- **`mobile/`** workspace never audited.

---

# Outcome — merged as PR #18 (`db172fb`)

All three CI jobs green on `591bf58`: secret scan, type-check/lint/audit, Python audit.

## CI earned its place within the hour

`pip-audit` failed on its **first ever run**: `cloud/requirements.txt` pinned
`requests==2.32.5`, carrying **PYSEC-2026-2275** (fixed in 2.33.0). That is the
dependency the Railway collector runs on, and it was not something the npm-side
audit would ever have surfaced. Bumped to `2.33.1` — the version this machine
already had installed and that every collector cycle on 12 Sep executed against.

Gitleaks independently confirmed no secrets in history, which is stronger evidence
than the regex sweep done by hand earlier in the session.

## ⚠️ VERCEL HAS NOT DEPLOYED FOR DAYS — betmate.au IS STALE

Every Vercel deployment on `main` has **failed**, going back past the analytics
merge. Railway deploys fine; Vercel does not.

**This explains the tipping-reminder 401.** `curl` with the correct `CRON_SECRET`
still returns 401 because the route was never deployed — the OLD gate is live on
betmate.au and `/api/cron` is not in its allowlist. The 11 Sep diary's hypothesis
(1) was right, and the cause is a failing build. It also means the Next 16 upgrade
and the tipping feature are not live.

Ruled out by testing, not by guessing:
- **Not the code.** A clone of tracked files only — no `data/`, no `.env.local`,
  exactly what Vercel receives — builds clean.
- **Not `vercel.json`.** One daily cron, which Hobby permits.

⚠️ A claim was made mid-session and retracted: that the check "failed in 0 seconds"
and therefore never started building. That `0` is an empty duration column shown
for *every* external check, including ones that pass. It means nothing.

**Only the Vercel build log will say.** Needs `npm i -g vercel && vercel login`.

## ⚠️ Process failure worth keeping

The working directory switched branches mid-session, from
`security/audit-remediation` to `research/nrl-totals-matrix-v2-hitrate` (local-only,
two commits of NRL totals work, not this session's). The `requests` commit landed
on that branch. **`git push` then reported "Everything up-to-date"** — true, because
the security branch genuinely was; the commit simply was not on it.

Caught only because `gh` showed no new CI run. Recovered by cherry-picking onto
`security/audit-remediation` and moving the research branch back to `20386db`; both
its commits are intact and the checkout was restored.

**Rule: verify a push against `origin/<branch>`, never against push output.** Same
family as everything else today — an operation reporting success while doing nothing.

## Owner actions still outstanding

1. **Run the verification query** in `supabase/migrations/20260912_tipping_rls.sql`,
   then apply the migration and exercise the tipping flow. This is the one item the
   owner has not deferred and it is unresolved.
2. Anthropic spend cap and 2FA — **owner has explicitly deferred these (~1 year)**;
   this is a beta. Do not re-raise.
3. Vercel deploy failure — see above.

## Left open by design

- **F-03** `/api/chat` in-memory rate limit on serverless.
- **F-07** unpickled model artefacts without checksums.
- CSP with nonces. The `mobile/` workspace was never audited.
