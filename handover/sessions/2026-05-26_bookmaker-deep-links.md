# Session Diary — 2026-05-26 — Bookmaker Deep Links

## What we did

Wired up bookmaker cards to link to the specific game page (or closest possible equivalent) on each bookmaker's site.

## Problem

Clicking a bookmaker card previously went to the sport's competition landing page (e.g. `sportsbet.com.au/betting/rugby-league/nrl`). User wanted it to go to the actual game.

## Research Finding

Most Australian bookmakers use internal numeric event IDs in their game URLs — you can't construct them from team names alone without their affiliate API or a nightly scrape. The one exception is TAB, which uses full team name slugs.

## Implementation

**`lib/affiliate.ts`** — Added `buildGameUrl(bookmaker, sport, homeTeam, awayTeam)`:

| Bookmaker | Strategy | Example URL |
|---|---|---|
| TAB | Match-level slug URL | `tab.com.au/…/matches/North-Queensland-Cowboys-v-South-Sydney-Rabbitohs` |
| TABtouch | Slug URL (attempted) | `tabtouch.com.au/sports/rugby-league/…/cowboys-vs-rabbitohs` |
| Sportsbet | Search URL (short team name) | `sportsbet.com.au/search?term=Cowboys%20Rabbitohs` |
| Neds | Search URL | `neds.com.au/search?q=Cowboys%20Rabbitohs` |
| Ladbrokes | Search URL | `ladbrokes.com.au/search?q=Cowboys%20Rabbitohs` |
| Betright, Betr, PointsBet, Unibet, Betfair | Competition URL | Sport-level page (need event IDs for deeper) |

**`components/odds/GameCard.tsx`** — Wired `homeTeam`/`awayTeam` through the component tree:
- `BmCard` props: added `homeTeam`, `awayTeam`; replaced `getAffiliateUrl` call with `buildGameUrl`
- `OddsRow`, `SpreadsRow`, `TotalsRow`: added `homeTeam`/`awayTeam` props
- `GameCard`: passes `game.homeTeam`/`game.awayTeam` to all row components

## Encoding Bug Encountered

The Edit tool converts ASCII `"` to curly quotes (U+201D) and garbles em-dashes when writing new content. This caused TypeScript errors on the lines I edited. Fixed by scanning the file with PowerShell and replacing all U+201C/U+201D with straight ASCII `"`.

**Going forward:** Any edit to lines containing `side="home"`, `side="away"`, `market="h2h"` etc. in GameCard.tsx should use PowerShell string replacement, not the Edit tool — same issue as ChatPanel.tsx.

## State After Session

- Bookmaker links: game-specific for TAB, search for Sportsbet/Neds/Ladbrokes, competition for others ✅
- TypeScript: clean ✅
- Deployed to Vercel via git push ✅

## Pending (unchanged)

- Per-game links for Betright/Betr/PointsBet: need nightly event ID scrape or affiliate API
- MCP layer for Baz
- Custom domain betmate.au SSL
- Supabase UNIQUE constraint
- R12 CLV
- Refs on Vercel
