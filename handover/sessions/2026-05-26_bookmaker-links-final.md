# Session Diary — 2026-05-26 — Bookmaker Links (Final)

## What we did

Wired up clickable bookmaker links across the odds board. Took three attempts to get right.

## The Bug Chain

**Attempt 1:** Edited `components/odds/GameCard.tsx` — completely wrong file. `GameCard` is only imported as a **type** in the main app. The actual odds board is `OddsBoardCard` in `app/odds/page.tsx`, which has its own `BookLogo` (desktop) and `MobilePriceTile` (mobile) components. Both were plain `<div>` — no links at all.

**Attempt 2:** Edited the correct file (`page.tsx`) but PowerShell string interpolation corrupted JSX template literals — backticks and `${...}` expressions were expanded. Fixed by re-splicing the broken lines with single-quoted PS strings.

**Attempt 3:** Sportsbet's `/search?term=...` URL may not be covered by their Universal Links config. Switched to the competition URL (`/betting/rugby-league/nrl`) which iOS Safari will intercept to open the Sportsbet app.

## What's Wired Up

| Component | What changed |
|---|---|
| `BookLogo` (desktop header) | Wrapped in `<a>` using `buildGameUrl` |
| `MobilePriceTile` (mobile tile) | Renders as `<a>` tag using `buildGameUrl` |

## URL Strategy per Bookmaker

| Bookmaker | URL | Notes |
|---|---|---|
| TAB | Match-level slug URL | `tab.com.au/.../matches/Cowboys-v-Rabbitohs` |
| TABtouch | Slug URL (attempted) | Similar pattern to TAB |
| Sportsbet | Competition URL | `sportsbet.com.au/betting/rugby-league/nrl` — Universal Link opens app on iOS Safari |
| Neds | Search URL | `neds.com.au/search?q=Cowboys+Rabbitohs` |
| Ladbrokes | Search URL | `ladbrokes.com.au/search?q=Cowboys+Rabbitohs` |
| Betright, Betr, PointsBet, Unibet, Betfair | Competition URL | These need internal event IDs for game-level links |

## Universal Links Note

Sportsbet app will open automatically on **iOS Safari** when tapping the Sportsbet tile (Universal Links). Does NOT work in Chrome on iOS — Chrome ignores Universal Links for third-party apps. If the user wants Chrome support, we'd need Sportsbet's custom URL scheme (`sportsbet://...`) which isn't publicly documented.

## Key Files Changed

- `lib/affiliate.ts` — `buildGameUrl(bookmaker, sport, homeTeam, awayTeam)` function
- `components/odds/GameCard.tsx` — `homeTeam`/`awayTeam` plumbing (not used in main view, but wired for completeness)
- `app/odds/page.tsx` — `BookLogo` and `MobilePriceTile` now render as `<a>` links

## Encoding Warning

**The Edit tool corrupts JSX attribute values in `.tsx` files** — converts `"` to U+201D curly quotes and garbles em-dashes. Use PowerShell `[System.IO.File]` methods for any edits to `page.tsx` or `GameCard.tsx`. Quick fix if it happens:
```powershell
$f = "path/to/file.tsx"
$c = [System.IO.File]::ReadAllText($f, [System.Text.Encoding]::UTF8)
$c = $c.Replace([string][char]0x201C, '"').Replace([string][char]0x201D, '"')
[System.IO.File]::WriteAllText($f, $c, [System.Text.Encoding]::UTF8)
```

## State After Session

- Bookmaker links: live on Vercel ✅
- Desktop: bookmaker logo header cell is clickable
- Mobile: each price tile is a tap-to-bookmaker link
- Sportsbet on iOS Safari: opens app via Universal Links ✅

## Pending

- MCP layer for Baz (next major work)
- Per-game links for Betright/Betr/PointsBet (need nightly event ID scrape)
- Sportsbet Chrome/Android deep link (need custom URL scheme — not public)
- Custom domain betmate.au SSL
- Supabase UNIQUE constraint
- R12 CLV
- Refs on Vercel
