# 2026-09-11 — Market engine moved to the cloud, and a ledger bug caught

**Merged:** PR #8 → `main` (`2eadea5`). Branch `feat/market-engine-cloud` **kept alive on purpose** — Railway still deploys from it.

## The headline

The cloud collector was written 3 September and never switched on. Meanwhile the
laptop job meant to snapshot every 10 minutes was managing **~8 cycles a day** —
2,037 credits in 11 days against the ~129,600/month a real 10-minute run costs.
The Mac sleeps, snapshots vanish, and `com.betmate.prevent-sleep` existed purely
to fight that. The archive has large irregular holes as a result.

## Decisions made

**Cadence: flat 2-hourly + one close capture per kickoff cluster.** ~14,900
credits/month, 26% inside the existing $30/20k plan, no upgrade.

Evidence, from the repo's own archive — 60% of h2h movement happens more than a
day out as slow drift; the final two hours are 16.7x more intense per hour but
only 8.8% of the total. The close capture exists because the model's TARGET is
the closing price and 25% of movement lands in the final six hours.

⚠️ **Never drive the close capture off the cadence ladder** — with staggered
kickoffs the nearest-kickoff rolls forward all evening and the sport never leaves
tight mode. Measured: **86,046 credits/month**. `next_due_at()` does it for ~1,900.

**Paid calls gated on the FREE `/events` check, not the API's `active` flag.**
`/events` and `/sports` cost 0 credits (measured). UCL proved why within the hour:
the API said `active=false` while matchday 1 had been played the day before and 17
October fixtures were live. The flag is an opinion; fixtures on the board are a fact.

**Hourly was considered and rejected.** It buys nothing: the lead-lag ordering is
stable when downsampled (hourly rho=+0.84, 2-hourly rho=+0.74), so 2-hourly already
answers "who moves first". Minute-scale reaction needs minute data and no
affordable cadence reaches it — use burst mode (1 sport/region/market = 1 credit)
for targeted studies instead.

## Found by accident, mattered a lot

**Next.js 14.2.3 on the live site.** Railway's dependency scanner blocked the
deploy over two HIGH CVEs — nothing to do with our Python container. npm rates the
pre-upgrade state critical, including an **authorization bypass**, and
`middleware.ts` is what gates the API routes. Upgraded to 14.2.35, build passes.
**Not fully clear** — the 14.x tail has two critical unauthenticated RCEs fixed
only in 15.5.24+. Windows RCE doesn't apply (Vercel is Linux); Image Optimization
RCE is limited by `images.domains` and no `next/image` imports, but `/_next/image`
is a framework route regardless. **Next 14 -> 15/16 scheduled for this afternoon.**

**`log_actual_bet.py` was eating the bet ledger.** `FIELDNAMES` was missing
`week_ending`, and the script rewrites the ENTIRE file with `csv.DictWriter` on
every save — so logging one bet silently deleted that column from all 118
historical rows and shifted every field left. Read by **nine** scripts including
`update_clv_running.py`, so CLV would have gone quietly wrong with no error.
Caught by byte-comparing an untouched historical row against `git show HEAD:`
before committing. **Do this on any script that rewrites rather than appends.**

## Railway build: three failures

1. No root config → Railway built the Next.js site. Fixed with root `railway.json`.
2. My `.dockerignore` used `!cloud/` — the trailing slash restores the directory
   entry but not its contents, so `COPY cloud/requirements.txt` found nothing.
   Needs `*`, `!cloud`, `!cloud/**`. Context also dropped to 284K.
3. The security scanner. Only findable from the build log — three inferences from
   the repo layout got nowhere.

## State

| | |
|---|---|
| Supabase migration | ✅ 7 tables + health function verified live |
| Collector dry run | ✅ 321 events, 7,518 quotes, 36 credits, 0 errors |
| Railway build | ⚠️ retry after the Next.js merge |
| `ODDS_COLLECTION_LIVE_ENABLED` | ❌ **false** — deliberate |
| Laptop launchd jobs | ❌ still running |

**Go-live:** force one run with the flag false → `cloud/collection_health.py` +
quota headers → flip true → confirm rows in `odds_quote_changes` and
`odds_market_checkpoints` → unload `com.betmate.odds-snapshot-10min` and
`com.betmate.prevent-sleep`.

## Branches

Closed `research/efl-totals-vault-test` and `research/efl-totals-signal` — both
were already fully in main via PR #8; all eight research artefacts verified present
first. **Racing branches and worktrees left alone — Codex is working on those.**

## Open

1. Next 14 → 15/16 (this afternoon).
2. `xlsx` — two HIGH advisories, no upstream fix, local-only use.
3. Settle 2026-0118 / 2026-0119 once football-data publishes 12-13 Sep (`HY`/`AY`).
4. Join results into the market warehouse — unlocks CLV/backtesting.
5. Betfair volume — the Odds API gives prices, not money.
6. **Do not resell Odds API data** — terms forbid raw redistribution. Derived
   signals are fine.
