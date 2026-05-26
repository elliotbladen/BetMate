# Session Diary — 2026-05-26 — Mobile Layout Root Cause Fix

## What we did

Fixed the persistent mobile layout breakage on `betmate.au`. After ~20 attempts across multiple sessions, found and killed the root cause.

## The Bug

Every previous mobile fix (CSS breakpoints, tile layout, mobile card header, Details button clip) was patching elements inside a container that was already **978px wide on a 375px phone screen**.

**Root cause:** CSS Grid items have `min-width: auto` by default, which resolves to `min-content`. The chips bar inside each game card contains long text spans ("MOVE: SHARKS SHORTENING", "BEST PRICE GAP: 1.8%", "REF: GRANT ATKINS · NEUTRAL", etc.) that sum to ~950px. This silently inflated the implicit grid track from the expected 343px to 978px. Every descendant element inherited that width:

- Article: 978px (should be 343px)
- Flex button container: 952px
- Each `flex-1` button: **471px** — with Ask Baz and BVI visible but Details and H/A Value starting at x=508, completely off-screen

The `html, body { overflow-x: hidden }` in globals.css masked the problem visually (page didn't scroll horizontally) but the layout was still broken.

## The Fix

**One line, `app/odds/page.tsx`:**

```jsx
// Before
<div>
  <OddsBoard ... />

// After
<div className="min-w-0">
  <OddsBoard ... />
```

`min-w-0` on the CSS Grid item sets `min-width: 0` instead of `auto`, allowing the grid track to size to available space (343px) rather than the chips' min-content width.

## Verified with Playwright

Ran headless Chromium at 375px viewport, measured actual DOM element sizes:

| Element | Before | After |
|---------|--------|-------|
| Article width | 978px | 343px ✅ |
| Ask Baz button | 471px | 154px ✅ |
| Details button x | 508px (off-screen) | 191px ✅ |
| BVI button | 471px | 155px ✅ |
| H/A Value x | 509px (off-screen) | 192px ✅ |
| Page scrollWidth | 978px | 375px ✅ |

Screenshot confirmed correct visual layout.

## Also shipped this session (commits 9dedcae)

- **BVI / H/A Value toggles on mobile** — added to mobile card header (sm:hidden block), same green/blue styling as desktop. Previously these only existed in the `hidden sm:block` desktop header so phone users could never toggle them.
- **CompletedCard mobile layout** — replaced `min-w-[480px]` desktop-only grid with responsive layout (sm:hidden compact tile row + hidden sm:block full grid). Fixed header truncation for long team names.
- **Deduplicated sport tabs** — sub-header now shows only H2H/Line/Totals on mobile (NRL/AFL hidden with `hidden sm:flex`), since the black nav header already has sport switching.

## State after session

- betmate.au mobile: **working** ✅
- Verified: Ask Baz, Details, BVI, H/A Value all visible and correctly sized on 375px iPhone viewport
- Deployed to Vercel via git push to main

## Pending (unchanged)

- Custom domain `betmate.au`: SSL pending, `www.betmate.au` CNAME needs updating
- Cloudflare Tunnel: waiting on domain
- Supabase UNIQUE constraint on `key` column
- R12 CLV not yet filed
- Refs on Vercel (static JSON removed, need Supabase route)
- AFL totals model bias fix
