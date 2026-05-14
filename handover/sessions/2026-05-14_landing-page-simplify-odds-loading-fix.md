# Session 2026-05-14 — Landing page simplify + odds loading fix

## What was done

### 1. Fixed "No NRL games available" on /odds
- **Root cause:** `loading` state in `app/odds/page.tsx` initialised to `false`.
  On every first render (before `useEffect` fires), `loading=false` + `games=[]` matched the empty-state branch and showed "No NRL games available". With the initial 1-2 second JS compile overhead in dev, this was visible for several seconds.
- **Fix:** Changed `useState(false)` → `useState(true)` for `loading`.
- **Also fixed:** Added `setLoading(true)` to the sport-switch reset `useEffect` so switching between NRL/AFL tabs also shows the spinner immediately rather than flashing the empty state.
- **File:** `app/odds/page.tsx`

### 2. Simplified the landing page
- **Before:** 5 sections — hero with 6 proof chips + 2 CTAs, "What it does" pillars, "Daily habit" workflow, "Free account" feature cards, disclaimer strip.
- **After:** Hero (headline + one-liner + one CTA + LiveOddsPreview) + disclaimer strip. Everything else deleted.
- Hero now fills full viewport height (`min-h-[calc(100dvh-60px)]`) so it feels intentional.
- Sub-copy cut to: "The best-price comparison tool for Australian punters. Free to use."
- **File:** `app/page.tsx`

### 3. Created mockup file
- `public/mockup.html` — standalone HTML mockup showing two layout options (split vs centred). Used for design review before implementing. Can be deleted.

## State at end of session
- Dev server running on port 3000
- Both fixes live and working
- Landing page approved by user

## Pending
- (Unchanged from previous) BVI weekly Task Scheduler task still not installed
- (Unchanged) Odds movement alert threshold filter (>=10%) still pending
