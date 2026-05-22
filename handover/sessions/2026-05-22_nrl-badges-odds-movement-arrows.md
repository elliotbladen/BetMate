# Session Diary — 2026-05-22
## NRL BVI/H&A Badges + Odds Movement Arrows on Vercel

---

### What We Did

**1. NRL BVI + Home/Away Value Badges (mirrors AFL)**
- Built `lib/scraper/nrl_bvi.py` — scrapes aussportstipping.com NRL BVI (POST with 1-year rolling window). Fixed team names to match `teams.ts` exactly (no hyphens, no dots). Pushes to Supabase key `nrl_bvi`.
- Built `lib/scraper/nrl_home_advantage.py` — scrapes NRL home/away win% (same source). Pushes to Supabase key `nrl_home_away`.
- Built `app/api/nrl-bvi/route.ts` and `app/api/nrl-home-away-value/route.ts` — Supabase-first with local fallback.
- Added both routes to `middleware.ts` PUBLIC_PATHS.
- Wired both into `app/odds/page.tsx` so NRL tab shows BVI/H/A badges exactly like AFL tab.

**2. BVI/H&A Task Scheduler tasks**
- Created `scripts/run_bvi_home_away.ps1` — shared wrapper that loads `.env.local`, sets `PYTHONUTF8=1`, runs any BVI/H/A scraper via `uv`.
- Created `scripts/install_nrl_bvi_task.ps1` and `scripts/install_nrl_home_away_task.ps1`.
- Updated AFL install scripts to use the same wrapper pattern.
- All 4 tasks installed: AFL BVI (Mon 08:00), AFL H/A (Mon 08:10), NRL BVI (Mon 08:20), NRL H/A (Mon 08:30). First auto-run: 2026-05-25.

**3. Odds movement system rework — Monday baseline via Supabase**

Old system: diff last-2-snapshots from local CSV files → doesn't work on Vercel.

New system:
- `odds_snapshot.py` — on Monday, calls `push_opening_baseline()` which stores all NRL+AFL prices under `nrl_opening_baseline`/`afl_opening_baseline` in Supabase. Key format: `{game_id}:{market}:{bookmaker}:{side}`.
- `odds_movement_tracker.py` (rewritten) — reads `latest.csv`, fetches baselines from Supabase, detects changes ≥ min_pct, pushes movement map to Supabase key `odds_movements`.
- `scripts/seed_test_baseline.py` — one-off tool to seed a specific Monday snapshot as the baseline (for testing or if Monday 09:00 task missed).
- Vercel frontend: `/api/odds/movements` route reads `odds_movements` from Supabase. `page.tsx` falls back to this when local opening prices are empty.

**4. Fixed odds movement arrows not showing on Vercel**

Root cause: `getDataStore` in `lib/supabaseServer.ts` used `.single()`. The movement tracker had been run twice, creating two rows for `odds_movements` key (no UNIQUE constraint on `key` column). `.single()` errors when multiple rows match, returning null → API returns `{}` → no arrows.

Fix: changed to `.limit(1)` which returns first matching row regardless of duplicates.

Pushed as commit `ca76ec6`. Verified live: `https://bet-mate-ten.vercel.app/api/odds/movements` now returns 319 movement entries.

---

### Key Files Changed
| File | Change |
|------|--------|
| `lib/supabaseServer.ts` | `.single()` → `.limit(1)` to handle duplicate rows |
| `lib/scraper/odds_snapshot.py` | Added `push_opening_baseline()` for Monday runs |
| `lib/scraper/odds_movement_tracker.py` | Full rewrite — baseline vs Supabase, no more last-2 diff |
| `scripts/seed_test_baseline.py` | New — seeds any Monday CSV as the week's baseline |
| `lib/scraper/nrl_bvi.py` | New — NRL BVI scraper + Supabase push |
| `lib/scraper/nrl_home_advantage.py` | New — NRL H/A scraper + Supabase push |
| `app/api/nrl-bvi/route.ts` | New — serves nrl_bvi from Supabase |
| `app/api/nrl-home-away-value/route.ts` | New — serves nrl_home_away from Supabase |
| `app/odds/page.tsx` | NRL BVI/H/A wired; Supabase movement fallback added |
| `middleware.ts` | Added nrl-bvi, nrl-home-away-value to PUBLIC_PATHS |
| `scripts/run_bvi_home_away.ps1` | New shared wrapper for BVI/H/A tasks |

---

### Technical Notes

**Supabase duplicate key issue:** The `betmate_data_store` table has no UNIQUE constraint on `key`. Running any scraper twice creates two rows with the same key. `.single()` then errors. Fixed in `getDataStore` with `.limit(1)`. Long-term fix: add UNIQUE constraint in Supabase SQL editor:
```sql
ALTER TABLE betmate_data_store ADD CONSTRAINT betmate_data_store_key_unique UNIQUE (key);
```

**Movement key format:** `{game_id}:{market}:{bookmaker}:{side}` where:
- `market` = `h2h` / `spreads` / `totals`
- `side` = `home` / `away` / `over` / `under`
- `game_id` = Odds API UUID (stable across API calls for same game)

**Baseline resets every Monday:** The Monday 09:00 snapshot task auto-runs `push_opening_baseline()`. Every subsequent tracker run (Tue–Sun snapshots) compares vs Monday's prices. Next Monday, the baseline is overwritten with the new round's opening prices.

**Monday task must run once per week** — if it misses (machine asleep, task failed), run `seed_test_baseline.py` manually pointing at Monday's CSV, or wait until next Monday.

---

### Next Session Priorities
1. Verify movement arrows visible on betmate.au after hard refresh
2. Custom domain — add `www.betmate.au` CNAME to Vercel, update Cloudflare DNS
3. Refs on Vercel — wire `lib/referees.ts` to Supabase so ref badges show
4. Add UNIQUE constraint to `betmate_data_store.key` in Supabase SQL editor
