# Session Diary — 2026-05-26 — Mobile Web UX Fix (betmate.au on Phone)

## What we did

Improved the mobile browser experience of the existing Next.js web app at `betmate.au`.

**Context:** After building the React Native scaffold (see `2026-05-26_mobile-app-scaffold.md`), user clarified the immediate priority is the website working well on phone browsers — the RN app is parked for later.

### Problem
The odds board used a CSS grid with `min-w-[1100px]` — on a phone this forced horizontal scroll of the entire page, making bookmaker prices effectively unusable.

### Fix — `app/odds/page.tsx`

1. **Added `MobilePriceTile` component** — compact 72px-wide tile showing:
   - Bookmaker favicon (Google S2 favicons API, 64px)
   - Bookmaker abbr in mono caps
   - Point/spread value (for Handicap + Totals markets)
   - Price in large mono bold (net price via `netPrice()` for Betfair commission)
   - Best-price highlight: teal border + bg when this tile is the best available
   - Movement arrow: pinned top-right when a price movement exists

2. **Conditional render in `OddsBoardCard`** — leverages existing `isMobile` state (window.innerWidth < 640):
   - `isMobile === true` → tile row per side (Home/Over, Away/Under) with `overflow-x-auto no-scrollbar` horizontal scroll
   - `isMobile === false` → original CSS grid unchanged

3. **`tsconfig.json`** — added `"mobile"` to `exclude` array to stop the RN project's React Native types bleeding into the Next.js TypeScript check.

### Commits pushed
- "Mobile: 5 bookmakers on phone, compact grid, full-width buttons" (earlier in session — responsive header + grid)
- "Fix mobile layout: compact header, touch-friendly info popups, overflow fix" (overflow/touch fixes)
- "Mobile: tile-based odds layout for phone screens" (the MobilePriceTile component + conditional render)

All deployed to Vercel via GitHub auto-deploy.

### To verify
Open `betmate.au` on a phone. Each game card should show:
- Compact header row (teams, score, time)
- Horizontal-scrollable tiles for each bookmaker (Home row + Away row)
- Best price highlighted in teal
- Movement arrows shown on tiles where price moved

## Pending / next session
- User to confirm visual result looks good on their phone (screenshot)
- React Native app (`mobile/`) parked — future: test on real device, add "Ask Baz" → Baz screen pass-through, EAS Build for TestFlight
- Custom domain `betmate.au`: SSL pending, `www.betmate.au` CNAME needs updating in Cloudflare + Vercel domain added
- Cloudflare Tunnel: waiting on domain before wiring EV arrows on Vercel
- Supabase UNIQUE constraint: `ALTER TABLE betmate_data_store ADD CONSTRAINT betmate_data_store_key_unique UNIQUE (key);`
- R12 CLV not yet filed
- AFL totals model bias fix (systematic underprice by 8–25pts)
