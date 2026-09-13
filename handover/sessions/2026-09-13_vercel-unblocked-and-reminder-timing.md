# 2026-09-13 — Vercel unblocked after days, and the reminder aimed at 24h

Continues `2026-09-12_security-audit-and-remediation.md`. Everything below is on
`main`; nothing left open.

## Headline: betmate.au had not deployed for days, and the cause was not the build

Every Vercel deployment on `main` failed going back past the analytics merge, so
the Next 16 upgrade, the tipping feature and the morning's security fixes were all
merged but **never live**.

```
The Vercel Function "api/ev-signals" is 2.49gb uncompressed
which exceeds the maximum uncompressed size limit of 250mb.
```

⚠️ **THE BUILD ALWAYS SUCCEEDED.** It failed afterwards, at "Deploying outputs".
That is why it read as a build problem for days, why a clean clone of tracked files
built fine locally, and why nothing in the repo looked wrong.

`lib/matrixEV.ts` reads BettingEngine spreadsheets through a path assembled at
runtime, so Next cannot statically analyse the access and falls back — the build log
says it outright: **"Dynamic filesystem access causes tracing of the whole
project"**. The whole project is 2.8 GB of BettingEngine and 18 GB of RacingEngine.

Fixed with `outputFileTracingExcludes` in `next.config.js` (`d0737dc`). Safe because
the code already expects those files to be absent in production — `matrixEV` guards
every read with `existsSync`, the route try/catches to `{ signals: [] }`, and EV
signals are deliberately blank on Vercel so the engine IP stays local.

**Measured: /api/ev-signals traces 421 files / 8.0 MB, against 2.49 GB before.**

⚠️ A claim was made and retracted mid-session: that the check "failed in 0 seconds"
and therefore never started building. That `0` is an empty duration column shown for
*every* external check, passing ones included. It meant nothing.

## This also explains the tipping-reminder 401

`curl` with the correct `CRON_SECRET` had been returning 401 since 11 Sep. It was
neither cause the diary guessed at: **the route was never deployed**, so the OLD
proxy — which has no `/api/cron` in PUBLIC_PATHS — was still answering.

Once deployed it returned `503 CRON_SECRET not configured`, which revealed the
second fault: **`CRON_SECRET` was not in Vercel at all**. Nor was
`SUPABASE_SERVICE_ROLE_KEY`.

⚠️ **That second one was a live regression created earlier the same day.** The
tipping routes were switched to `createAdminClient()` (to allow RLS), and that
client *throws* without the service-role key. Tipping tested fine only because the
old build was still serving. Caught before anyone hit it.

## Reminder retimed to ~24h before first kickoff (`1e259d0`)

Owner wants one nudge about a day out. It was never sending daily —
`tipping_reminders` dedupes per person per gameweek, so the cron is only how often
we CHECK — but it was aimed at ~30h.

⚠️ **Vercel Hobby caps cron at once per day** (more frequent expressions fail to
deploy) with ±59 min precision, so an exact 24h trigger is not available.

Chose the setting by running every (hour, lead) pair against all 38 real kickoffs in
`lib/epl-2026-27-fixtures.json`:

| setting | notice before lock | median |
|---|---|---|
| **15:00 UTC + 30h  (now)** | **20.5h – 29.0h** | **24.0h** |
| 09:00 UTC + 48h (before) | 26.5h – 35.0h | 30.0h |
| any hour + 24h | **2.5h – 11.0h** | — |

⚠️ **The trap: setting the lead to 24 to get "24 hours notice" makes it far
WORSE.** On a daily check the first check under 24h can be minutes before kickoff —
GW6 and GW7 kick off Sat 11:30, so a 09:00 check gives 2.5 hours. **The lead must
exceed the gap between checks, not match the target.** Re-run that comparison if the
fixture shape changes.

First live send: **Thu 17 Sep 15:00 UTC**, 28h before GW5 locks (Fri 18 Sep 19:00).

## Mail path proven end to end

`RESEND_API_KEY` was in no file, no shell history, no keychain — pasted straight
into Vercel and never kept. Vercel and Resend both store secrets write-only, so it
could not be recovered; owner created a new key.

`scripts/send_test_reminder_email.py` sends one message using the real sender and
template, and deliberately does **not** write `tipping_reminders`, so a test cannot
mark a real entrant as already nudged.

**Result: `status: delivered`** to the owner address from `BetMate
<tips@betmate.au>` — confirmed via Resend's API, not just accepted. That is the API
key, the verified domain and DKIM all proven at once.

## ⚠️ `vercel env add --force` REPORTED SUCCESS AND DID NOTHING

Updating `RESEND_API_KEY` with `--force` printed the success banner, but
`vercel env ls` still showed the original timestamp. Secrets cannot be read back, so
inspection could not settle it. Resolved by `vercel env rm` then `vercel env add` —
the timestamp then read "1s ago", which is proof rather than assumption.

**Had the success message been trusted, Vercel would still hold the old key and
would have broken silently the moment it was revoked.**

That is the **fourth** silent no-op in two days, alongside the collector reporting
`success` while idle, `git push` reporting "Everything up-to-date" with the commit
on another branch, and Railway variables sitting staged but unapplied. **This
codebase's characteristic failure is a green light over a dead component.** When
something reports success, the useful question is "what would this look like if it
had done nothing?" — if the answer is "the same", verify by other means.

## State at close

| | |
|---|---|
| betmate.au | ✅ live and current — `/`, `/odds`, `/tipping` all 200 |
| Reminder endpoint | ✅ 401 without secret, 200 with, reports GW5 / 140h / "too early" |
| Vercel env | ✅ `CRON_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`, `RESEND_API_KEY` all present |
| Odds collection | ✅ 5-minute cron, no errors |
| Odds API quota | ~13,900 of 20,000 |

## Branches closed

`feat/market-engine-cloud` and `docs/2026-09-12-branch-handover` — both fully merged
into `main`; Railway now deploys from `main`, so the former is no longer needed.

Left alone: `research/nrl-totals-matrix-v2-hitrate` (3 commits, live worktree),
`review/fitness-signoff` (23 commits, backs PR #14, which the owner deliberately
keeps open), `review/previous-handover-signoff` (1 commit, unmerged).

## Open

1. **Dependabot #26–#30 are MAJOR bumps** — Tailwind 3→4, TypeScript 5→7, ESLint
   9→10, `@types/node` 20→26. Left open deliberately; these break things. Merge one
   at a time with the build watched.
2. **PR #14** fitness/trials — owner keeps open for continued work.
3. **Railway trial ~$5.** Still the single biggest risk to collection.
4. `railway.json` stops being read **2026-12-01**; no `.railway/` dir yet.
5. Security: F-03 `/api/chat` in-memory rate limit, F-07 unpickled models, CSP with
   nonces, `mobile/` never audited. Spend cap and 2FA **deferred by the owner (~1
   year)** — do not re-raise.
6. **Close captures never yet observed on a clean run.** NRL 06:05 and EFL 11:00 UTC
   on 13 Sep are the first real test — look for runs at ~06:02 and ~10:57.
7. **The UI has still never been checked in a browser** since the Next 16 upgrade.
   It is only now actually deployed, so this is newly worth doing.
