# Session Diary — 2026-05-27 — History Tab (correct implementation)

## What we did

Replaced the wrong HistoryTab (showed personal LEGACY_BETS) with the correct version showing **team form data**: each team's last 6 results + last 6 H2H meetings.

## What's in the History tab now

### Home team — Last 6
Table: Date | Opponent (nickname) | Score | H/A | W/L badge

### Away team — Last 6
Same format.

### H2H — Last 6
Table: Date | Home (nickname) | Away (nickname) | Score (green if home team from our perspective won, red if lost)

### Loading / empty states
- "Loading form data..." while fetching
- "Could not load form data" on fetch error
- "AFL history coming soon" for AFL games (no data source yet)

## Architecture

**Data flow:**
1. `scripts/push_nrl_history.py` reads `data/nrl/historical/latest.xlsx` (514 matches, 2024+) and pushes to Supabase `betmate_data_store` key `nrl_match_history`
2. `app/api/form/route.ts` reads `nrl_match_history` from Supabase, filters by nickname matching (last word of full team name), returns `{ homeForm, awayForm, h2h }`
3. `HistoryTab` component in `app/odds/page.tsx` fetches `/api/form?home=X&away=Y&sport=S` on mount

**Nickname matching:** `"North Queensland Cowboys"` → `"cowboys"` → `includes("cowboys")` match against Excel team strings (handles "North QLD Cowboys" etc.)

## Files changed

| File | Change |
|------|--------|
| `app/odds/page.tsx` | Replaced wrong HistoryTab; removed unused LEGACY_BETS import |
| `app/api/form/route.ts` | NEW — API route serving team form from Supabase |
| `scripts/push_nrl_history.py` | NEW — one-time/weekly push of NRL history Excel → Supabase |

## Encoding note

All edits to `page.tsx` done via PowerShell `[System.IO.File]::ReadAllText/WriteAllText`. The file has mixed CRLF/LF (HistoryTab area is LF-only). Replacement string used `\n` to match.

## Build status

✅ `npm run build` passes — 17 pages, TypeScript clean, `/api/form` registered as dynamic route.

## Deployed

✅ Pushed to GitHub → Vercel auto-deploy triggered.

## Pending

- AFL historical results: no source yet — shows "coming soon". Could scrape AFL Tables or similar.
- Re-run `push_nrl_history.py` weekly after downloading new `latest.xlsx` (BetMate NRL Historical Results task already does the download — just need to add the push step)
- Add the push step to the Tuesday pipeline (after historical download task)
