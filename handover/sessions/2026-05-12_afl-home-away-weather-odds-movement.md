# Session 2026-05-12: AFL Home/Away Value, Weather Fixes, Odds Movement Repair

## Summary

- Pulled latest BetMate from GitHub and restarted local dev server on port 3000.
- Added an AFL Home/Away Value signal beside BVI on `/odds?sport=AFL`.
- Fixed Tomorrow.io weather key setup and tightened dew-risk classification.
- Repaired AFL movement arrows by making opening prices read `latest.csv` and fall back to matchup keys when Odds API event IDs rotate.

## AFL Home/Away Value

Files:
- `app/odds/page.tsx`
- `app/api/afl-home-away-value/route.ts`
- `lib/scraper/afl_home_advantage.py`
- `data/afl/home-away/processed/latest-home-away.json`
- `middleware.ts`

Source:
- `https://www.aussportstipping.com/sports/afl/home_advantage/`

Important detail:
- The site defaults to an all-time range starting `2009-06-27`.
- User wanted the stats from `2025-03-01`.
- Scraper now POSTs date filters with start date `2025-03-01` and end date as today.

Badge rules:
- `Home Value`: home team home win percentage >= `70%`.
- `Away Value`: away team away win percentage >= `65%`.
- The H/A toggle controls whether badges appear. It does not hide games.

Current qualifying teams in regenerated data:
- Home: Hawthorn, Gold Coast, Geelong, Fremantle, Adelaide, GWS.
- Away: Fremantle, Brisbane.

## Weather API

Files:
- `app/api/weather/route.ts`

Issue:
- API was returning `500` because `TOMORROW_API_KEY` was missing from `.env.local`.
- User added the key, dev server was restarted, and weather calls returned `200`.

Fix:
- Dew flags were too naive: any tight temperature/dewpoint spread could trigger `MILD DEW`, even for afternoon games.
- Dew classification now requires an evening/night/early-morning local window, humidity >= `80%`, temperature <= `22C`, and tight dew spread.
- Rain/wind logic unchanged.

Verified:
- Sunday afternoon AFL games no longer show false dew flags.
- Weather sample returned condition/flags successfully from Tomorrow.io.

## Odds Movement Arrows

Files:
- `app/api/odds/opening/route.ts`
- `lib/oddsMovement.ts`

Issue:
- Live AFL odds API was working.
- Opening prices existed, but current AFL event IDs had zero matches.
- Current round data was in `data/odds_snapshots/latest.csv`, while opening API only scanned dated folders under `data/odds_snapshots/YYYY/`.

Fix:
- Opening API now includes `data/odds_snapshots/latest.csv`.
- Opening prices are keyed by both event ID and matchup:
  - `${game_id}:${market}:${bookmaker}:${side}`
  - `${home_team}:::${away_team}:${market}:${bookmaker}:${side}`
- Movement calculation falls back to matchup key if the live event ID does not match stored snapshot IDs.

Verified:
- Opening price count after fix: `1532`.
- Current live/opening matches: `342`.
- Current moved prices: `172`.
- TypeScript check passed with `npx tsc --noEmit`.

## Odds Snapshot Automation Gap

Current local snapshot state:
- `data/odds_snapshots/latest.csv` contains `706` rows dated `2026-05-11`.
- `data/odds_snapshots/2026/` only has `2026-05-04.csv` and `2026-05-05.csv`.
- No local `2026-05-11.csv` or `2026-05-12.csv` archive file exists.

Log says `2026-05-11.csv` was saved to a Windows path:
- `C:\Users\ElliotBladen\Apps\BetMate\data\odds_snapshots\2026\2026-05-11.csv`

Likely explanation:
- Snapshot ran on Windows/another path and only `latest.csv` made it into this repo state, or the dated archive was lost during GitHub history reset.

Next step:
- Add a macOS launchd equivalent for `lib/scraper/odds_snapshot.py`, or manually run the snapshot script and confirm dated archive files are created under this repo.

## Notes

- Dev server was restarted several times; final working URL: `http://localhost:3000/odds?sport=AFL`.
- `.env.local` now needs a valid `TOMORROW_API_KEY`, but the env file itself is not committed.
- There are unrelated untracked NRL data/log folders in the worktree; they were not part of this session's intended commit.
