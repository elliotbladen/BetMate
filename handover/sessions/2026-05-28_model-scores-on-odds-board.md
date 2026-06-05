# Session Diary — 2026-05-28 — Model Predicted Scores on NRL Odds Board

## What was done

### Feature: BettingEngine predicted scores shown on every NRL game card

Each NRL game card on the odds board now shows a line like:
```
Model: SHARKS 28.9 – EAGLES 23.9
```
This appears below the venue name on both desktop and mobile views.

### Files created

| File | Purpose |
|------|---------|
| `data/nrl/predictions/latest.json` | R13 NRL predicted scores (7 games) |
| `app/api/nrl-predictions/route.ts` | Serves the JSON — GET /api/nrl-predictions → `{ predictions: [...] }` |

### Files modified

| File | Change |
|------|--------|
| `middleware.ts` | Added `/api/nrl-predictions` to PUBLIC_PATHS |
| `app/odds/page.tsx` | Added `PredictionsMap` type, `nrlPredictions` state, fetch useEffect, passed `predictionsMap` prop through `OddsBoard` → `OddsBoardCard`, rendered model score line in both mobile + desktop card headers |

### Key gotcha — team name mapping

BettingEngine CSV names differ from Odds API names. The JSON must use **Odds API names** (matching `lib/teams.ts` NRL_TEAMS keys):

| BettingEngine CSV | Odds API (use this in JSON) |
|------|------|
| `Cronulla-Sutherland Sharks` | `Cronulla Sutherland Sharks` |
| `Manly-Warringah Sea Eagles` | `Manly Warringah Sea Eagles` |
| `Canterbury-Bankstown Bulldogs` | `Canterbury Bulldogs` |
| `St. George Illawarra Dragons` | `St George Illawarra Dragons` |

All other NRL team names match exactly between CSV and Odds API.

### JSON structure

```json
[
  {"homeTeam": "Cronulla Sutherland Sharks", "awayTeam": "Manly Warringah Sea Eagles", "predHomeScore": 28.9, "predAwayScore": 23.9},
  ...
]
```

Lookup in UI is keyed by `homeTeam` (unique per round). Scores formatted with `.toFixed(1)` so 23.0 shows as "23.0" not "23".

### Prop flow

```
OddsPageContent
  nrlPredictions (PredictionsMap)  ← fetched from /api/nrl-predictions
    ↓
  OddsBoard (predictionsMap prop)
    ↓
  OddsBoardCard (predHomeScore, predAwayScore)
    → rendered in card header (mobile + desktop)
```

---

## To update each round

1. Generate round pricing via BettingEngine (`run_nrl_pricing.ps1`)
2. Open `data/nrl/predictions/latest.json`
3. Replace all 7 entries with new `predHomeScore` / `predAwayScore` values from the CSV
4. Use **Odds API team names** (not CSV names) — see mapping table above

---

## Pending

- Automate: script that reads `BettingEngine/results/rNN_pricing_2026.csv` → writes `data/nrl/predictions/latest.json` with name translation
- AFL predicted scores (same approach, different JSON file + separate API route)
- Ref name normalisation bug in `prepare_round.py` (Cronulla/Manly + Broncos/Dragons still missing refs in T6)
