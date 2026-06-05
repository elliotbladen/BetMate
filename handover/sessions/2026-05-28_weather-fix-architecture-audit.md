# Session Diary — 2026-05-28 (Weather Fix + Architecture Audit)

## What We Did

### 1. Weather Classification Bug — DEW RISK showing instead of SHOWERS

**Problem:** The Cronulla vs Manly (PointsBet Stadium, Friday 8 PM) game card was showing "DEW RISK · 17°" when external forecasts (BOM) showed rain.

**Root cause investigation:**
- `classifyCondition()` in `app/api/weather/route.ts` had SHOWERS threshold at `precipProbability > 30`
- DEW and rain flags were independent blocks — both could fire simultaneously
- Tomorrow.io showed 0% precip for PointsBet Stadium at game time → no SHOWERS
- But humidity 82%, temp 17°C, dewSpread ~2.5 → DEW RISK fired correctly per our data
- Key finding: Tomorrow.io simply disagrees with BOM for this game. Not fixable without changing data source.

**Fixes applied (3 commits pushed to main):**
1. Lowered SHOWERS threshold: `precipProbability > 30` → `precipProbability > 20 || precipIntensity > 0.2`
2. Suppress dew flags when rain already present: `const hasRain = flags.includes('RAIN') || flags.includes('SHOWERS'); const hasDewConditions = !hasRain && ...`
3. Removed double-cache: inner `fetch(url, { next: { revalidate: 1800 } })` changed to `fetch(url, { cache: 'no-store' })`. Route-level `revalidate` dropped from 3600 → 1800. Previously two independent caches could disagree and serve stale data.

**Lesson:** Tomorrow.io ≠ BOM. DEW RISK was technically accurate for our data source. If user wants BOM-accurate rain signals, we'd need to integrate BOM as a fallback.

**Files changed:**
- `app/api/weather/route.ts` — classifyCondition(), revalidate, fetch cache

---

### 2. Architecture Audit — BetMate + BettingEngine

Full audit completed for both systems. Key findings:

**What's good (keep for EPL):**
- Tier model (T1–T8) stacking — auditable, explicit, right approach
- Supabase as sync layer
- Vercel + local engine via Cloudflare tunnel
- FastAPI base (baz_server.py)

**Main bug sources:**
1. Two repos, no real API contract — file path coupling causes most bugs
2. Team name canonicalization in 3 places with drift between them
3. Manual Supabase matrix push (gets forgotten)
4. Double fetch cache pattern (just caused today's weather bug)
5. SQLite under concurrent Task Scheduler jobs (fragile)
6. No ingestion validation — wrong team names or columns fail silently downstream

**EPL Architecture Recommendations:**
- One repo, three packages: `frontend/`, `engine/`, `scrapers/`
- Shared `teams.json` — single canonical team name source read by both TypeScript and Python
- BettingEngine as a proper FastAPI service (extend baz_server.py) — no more file path coupling
- Supabase Postgres for engine DB (not SQLite)
- Auto-push matrices to Supabase as side effect of `/price-round` endpoint
- Pydantic validation at every ingestion boundary
- Single cache layer (no double revalidate)
- Structured JSON logging from day one

---

## State at End of Session

- Weather fix: DEPLOYED ✅ — `app/api/weather/route.ts` now has lower thresholds, dew suppressed when rain present, single cache layer
- Commits: 3 pushed to main (a565408, fe04247, 520049d)
- Architecture audit: complete, saved to handover + memory
- No regressions introduced

## Next Steps

- EPL project: start with monorepo scaffold + shared teams.json
- BetMate: consider BOM fallback if Tomorrow.io accuracy remains poor for Sydney coastal venues
- CLAUDE.md weather section still shows old `revalidate = 3600` — update if it causes confusion
