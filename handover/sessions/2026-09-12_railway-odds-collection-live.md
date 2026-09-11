# 2026-09-12 — Railway odds collection is live for all seven codes

**Branch:** `docs/2026-09-11-handover` (PR #13). Collector fix `ddf5a84`.

## Headline

Railway had never executed a single collection cycle since it was deployed. It is
now collecting all seven codes on a `*/5` cron. First real run:

| | |
|---|---|
| worker | `betmate-market-worker-1` |
| window | 21:55:25 → 21:56:11 UTC, exit 0 |
| sports | AFL, EFL, EPL, NBA, NFL, NRL, UCL |
| result | 8,481 quotes, **3,424 genuine price changes**, 42 credits, 0 errors |

Warehouse after the run: 8,770 `odds_quote_state`, 11,523 `odds_quote_changes`,
8,647 `odds_market_checkpoints`. All seven sports `consecutive_failures: 0`.

## Two faults, either of which alone caused total silence

**1. The five service variables were staged but never applied.** Railway holds
variable edits as pending changes; the canvas still read **"Apply 5 changes"** and
the service card showed **"Edited / 5 Changes"**. They were entered via the Raw
Editor on 11 Sep and never deployed, so every container since started with *no
environment at all* and died at the `ODDS_API_KEY is required` guard.

**2. No cron schedule was ever registered.** Settings → Cron Schedule showed
`+ Add Schedule`, i.e. empty. `deploy.cronSchedule` in `railway.json` is
schema-valid — confirmed by pulling Railway's live JSON schema, the key exists at
`/properties/deploy/properties/cronSchedule` — but it had not been applied to the
service. Set to `*/5 * * * *` in the dashboard.

Five minutes is not arbitrary: it is Railway's minimum interval, and
`close_capture_lead_minutes` is 3, so anything coarser starts missing closing
prices — which are the model's target, not a nice-to-have.

## ⚠️ The diagnostic lesson — yesterday's conclusion was unsound

The 11 Sep diary reasoned: *"the collector inserts its run row BEFORE checking
whether any sport is due, so a Railway execution would appear even on a do-nothing
cycle. No row means the container is not executing."*

That does not hold. All three preflight guards returned `2` **before** the first
Supabase write. A container that ran perfectly but was misconfigured and a
container that never started left byte-identical evidence: nothing. The container
*was* executing the whole time.

Fixed in `ddf5a84`:
- a presence banner (`set`/`MISSING`, never values) printed before any guard exits;
- an aborted run recorded in `odds_capture_runs` as `failed` with the reason,
  whenever Supabase credentials are reachable;
- status **`skipped`** instead of `success` when a cycle fetched nothing. At `*/5`
  that is 288 rows a day, and every one claiming `success` made the table useless.
  **`status=eq.success` now means a real capture.** Value was already permitted by
  the migration's CHECK constraint.
- `live_enabled` dropped from `odds_collection_config.json` — nothing reads it, the
  only switch is the env var, so it was a config key lying about system state.

Also corrected mid-session: a first check said `railway.json` was missing from
`main`. It was not. Local `main` is **24 commits behind origin** and checked out in
a worktree at `/private/tmp/betmate-horse-ratings`, so `git show main:` read the
wrong ref. Re-checked against `origin/main`, which is what Railway builds from.

## ⚠️ The quota was four credits from dead

`com.betmate.odds-snapshot-10min` on this Mac was running **every 10 minutes** at
~30 credits a cycle — **~3,300 credits/day**, and only 5 of the 7 codes. The log
shows the quota reaching **4 remaining** on 2026-09-11 before it was refilled; the
refill (14,527) was ~4 days from dry, which would have killed Railway collection
the day after it started working.

Throttled to the twice-daily 09:00/18:00 schedule CLAUDE.md already documents
(~60/day). The plist is version-controlled at
`deploy/launchd/com.betmate.odds-snapshot-csv.plist`. **Do not put it back to 10
minutes.** Budget now: Railway ~14,900/month + CSV ~1,800/month against 20,000.

`scripts/run_odds_collector.sh` exists for manual/emergency cycles only and is
explicitly **not** for a launchd timer — a second scheduler would double-spend
credits and race Railway for the poll state.

## Open

1. **Cron firing is still unconfirmed.** The 21:55 run was triggered by the Deploy,
   not by a schedule. Confirm a run appears on a 5-minute boundary. Nothing is due
   until 23:55 UTC, so those cycles will show `skipped` once `ddf5a84` is on main.
2. **Railway trial: "30 days or $5.00 left".** When it runs out collection stops
   silently and looks exactly like today's fault. Add a payment method.
3. First close captures: **NRL 06:05 UTC, AFL 09:35 UTC 12 Sep**. These are the
   first real test of the close-capture path.
4. `feat/market-engine-cloud` can be deleted once cron is confirmed — Railway now
   deploys from `main`.
5. Vercel tipping-reminder 401 is untouched and still open.
