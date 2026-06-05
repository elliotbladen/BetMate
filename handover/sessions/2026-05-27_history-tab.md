# Session Diary — 2026-05-27 — History Tab

## What we did

Built out the **History tab** in the game card detail drawer (`app/odds/page.tsx`).
It was previously a placeholder with static text — now it shows real bet history.

## What's in the History tab

### Stats row (3 chips)
- **Bets** — total bets on either team in this sport
- **W / L** — win/loss record on those bets
- **H2H** — how many of those bets were on this specific matchup

### Bet table (up to 15 rows)
| Col | Content |
|-----|---------|
| Date | MM-DD from the stored YYYY-MM-DD |
| Match | Match name (truncated with tooltip) |
| Market | Market type (truncated) |
| Odds | Decimal odds taken |
| Res | W / L / P badge |

Rows sorted most-recent-first.

### Empty state
If no bets found for these teams (e.g. a sport with no history), shows a "No bet history" message.

### Footer
"Last N bets involving these teams. Full history on Research page."

## How the team matching works

`HistoryTab` receives `homeTeam` and `awayTeam` as full Odds API names (e.g. "North Queensland Cowboys").

The `keywords()` helper:
1. Replaces hyphens with spaces (handles "Cronulla-Sutherland" → ["Cronulla", "Sutherland"])
2. Splits on whitespace, filters words ≥ 3 chars
3. Adds manual aliases for known edge cases:
   - "Greater Western Sydney" → also adds "GWS"
   - "Rabbitohs" → also adds "Souths"
   - "North Melbourne" / "Kangaroos" → also adds "North"
   - "Collingwood" → also adds "Pies"

Bets are filtered: `b.sport === sport` (NRL/AFL guard) + ANY keyword from either team appears in the match string.

## Files changed

| File | Change |
|------|--------|
| `app/odds/page.tsx` | Added `import { LEGACY_BETS }`, added `HistoryTab` function, replaced placeholder |

## Encoding note

All edits made via PowerShell `[System.IO.File]::ReadAllText/WriteAllText` to avoid curly-quote corruption. The file uses CRLF line endings — the placeholder replacement required CRLF-aware string matching.

## Build status

✅ `npm run build` passes — TypeScript clean, all 16 static pages generated.

## Pending / future improvements

- Add MODEL_BETS to the History tab (NRL model bets — separate section or toggle)
- Show the cumulative P&L trend for bets on these teams
- Wire up actual H2H results (win/loss record) from historical data when that's available as JSON
- GWS matching: "GWS" keyword added manually but Odds API name check is "Greater Western Sydney" — confirm once AFL games are live in R13+
