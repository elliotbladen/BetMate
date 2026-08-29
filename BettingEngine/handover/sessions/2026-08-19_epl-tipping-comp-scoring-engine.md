# 2026-08-19 — EPL Tipping Comp: Scoring Engine + Stress Test

## What happened

### Tipping Comp Fixes (from earlier in session)
The tipping comp was broken end-to-end on production. Fixed a chain of 6 blocking issues:

1. **Supabase tables didn't exist** — user ran CREATE TABLE SQL for `tipping_comps`, `tipping_entries`, `tipping_tips` + disabled RLS
2. **Middleware blocking `/tipping` page** — added to PUBLIC_PATHS
3. **Middleware blocking API routes** — added `/api/tipping/join`, `/api/tipping/tips`, `/api/tipping/leaderboard`
4. **Vercel deploys failing** — `useSearchParams()` in login page without Suspense boundary was breaking all builds. Wrapped in `<Suspense>`
5. **Join state lost on refresh** — added localStorage persistence for invite code + display name, auto-rejoins on page load via upsert
6. **Login redirect loop on /tipping** — was missing from PUBLIC_PATHS

### Features Built (earlier in session)
- **Auto-fill away tips**: If a user hasn't tipped before the first kickoff, GET `/api/tipping/tips` auto-fills all untipped games as "away" via upsert
- **Clickable leaderboard picks**: After first kickoff, clicking a tipper's name shows their picks for the gameweek (UserPicksPanel component)

### Stress Test (this part of session)
Did deep research on tipping comp best practices (footytips.com.au, ESPN, SuperCoach EPL, Sportmonks, Tippr). Identified critical gaps:

### Scoring Engine Built
Created `app/api/tipping/results/route.ts` — `POST /api/tipping/results`:
- Accepts `{ gameweek, results: [{ game_id, home_score, away_score }] }`
- Scores ALL tips for that gameweek across all comps using `scoreResult()` from `lib/tipping.ts`
- Updates `tipping_tips.result` and `tipping_tips.points` per tip
- Recalculates `tipping_entries.total_points` from all scored tips (full recalc, not increment — safer)
- Added to middleware PUBLIC_PATHS

### Leaderboard Gameweek Filter
- `/api/tipping/leaderboard` now accepts optional `?gameweek=N` param to filter tip stats per GW
- Frontend passes `gameweek` to leaderboard API call
- Added `gameweek` to useEffect dependency array so leaderboard refreshes on GW change

### Build
Passing on both local and Vercel.

## How to score GW1 results (after games finish Aug 21-24)

```bash
curl -X POST https://betmate.au/api/tipping/results \
  -H "Content-Type: application/json" \
  -d '{
    "gameweek": 1,
    "results": [
      { "game_id": "epl-2627-gw1-1", "home_score": 3, "away_score": 0 },
      { "game_id": "epl-2627-gw1-2", "home_score": 1, "away_score": 2 },
      ...
    ]
  }'
```

Can also be done via browser console or a simple script. Game IDs are `epl-2627-gw1-1` through `epl-2627-gw1-10`.

## What's still needed

### Before GW2 (late August)
- **Add GW2 fixtures** to `lib/tipping.ts` — same pattern as `EPL_GW1_FIXTURES`, update `getFixtures()` in both `tips/route.ts` and `results/route.ts`
- **Score GW1** — run the results endpoint after all 10 games finish (Mon Aug 25)

### Nice-to-have (not blocking)
| Feature | Notes |
|---------|-------|
| Margin tiebreaker | Pick total goals for one game per GW to break ties |
| Per-game lockout | Currently all games lock at first kickoff; could lock each game individually at its own kickoff |
| Share/invite link | One-tap join via URL instead of typing code |
| Historical GW tabs | View past GW tips/results |
| Missed-round penalty | Industry standard: dock points if you miss a full round (our auto-away is gentler) |
| Push notifications | Reminder before lockout |
| Admin UI | Currently results must be submitted via API call; could build an admin page |

## Files changed
- `app/api/tipping/results/route.ts` — NEW (scoring engine)
- `app/api/tipping/leaderboard/route.ts` — gameweek filter
- `app/tipping/page.tsx` — pass gameweek to leaderboard API, dependency array fix
- `middleware.ts` — added `/api/tipping/results` to PUBLIC_PATHS
