# Session Diary — 2026-05-28 — Baz Matrix + Handicap Context

## What was done

### Problem
Baz was telling users Cronulla was "not a bet" when it's the round's #1 signal. Root cause: Baz only knew H2H EV (which was -4.8% for Cronulla — no signal), had no live market handicap lines, and had zero access to matrix confluence data.

### Fix 1 — Live handicap/totals in Baz context (`components/chat/ChatPanel.tsx`)

`buildOddsContext` now computes and sends live handicap and totals lines with every message:
```
Handicap (live market): Cronulla Sutherland Sharks -2.5pts @ 1.92 | Manly Warringah Sea Eagles +2.5pts @ 1.90
Totals (live market): Line 52.8 | Best Over 1.90 / Best Under 1.90
```
Uses `game.spreadsOdds` and `game.totalsOdds` already on Game objects. New vars computed before template: `spreadEntries`, `bestSpread`, `totalEntries`, `bestOver`, `bestUnder`, `bestTotalPoint`.

**Note:** This file has encoding corruption with the Edit tool — all changes made via PowerShell `$content.Replace()` with CRLF normalization.

### Fix 2 — Matrix confluence wired to Baz

**`BettingEngine/scripts/matrix_confluence.py`** — now always writes `outputs/nrl_t9_confluence_latest.json` after analysis (no flag needed):
```json
{
  "season": 2026, "round": 13, "generated_at": "...",
  "games": [
    {"home": "Cronulla-Sutherland Sharks", "away": "Manly-Warringah Sea Eagles",
     "confluence": {
       "h2h_HOME_WIN": {"count": 7, "edges": [...]},
       "handicap_HOME_COVERS": {"count": 7, "edges": [...]}
     }}
  ]
}
```

**`BettingEngine/baz_server.py`**:
- Added `CONFLUENCE_JSON = BASE_DIR / "outputs" / "nrl_t9_confluence_latest.json"`
- Added `_load_confluence()` → returns `{home_team_lower: confluence_flags}`
- Loads confluence once before the game loop, looks up each game by `home.lower()`
- Added `"confluence": confluence_map.get(home.lower(), {})` to each game summary

**`app/api/chat/route.ts`** — `buildContextBlock`:
- Added top-level `MATRIX SIGNALS (both H2H + handicap aligned)` section — only surfaces games where H2H is clean (exactly 1 direction with 3+ edges) AND handicap also has 3+ edges. Conflicted and single-market games are excluded.
- Per-game `Matrix T9: ⚡` line uses same filter
- `model_summary` updated to say "No H2H signals" (not "No signals")
- System prompt updated: Baz told to only discuss games in MATRIX SIGNALS section; conflicted/single-market = noise

### Fix 3 — System prompt improvements (`app/api/chat/route.ts`)

- `SIGNALS` → `H2H SIGNALS` in context header (clarifies scope)
- Added explicit instruction: compare `model_hcap` to live market handicap, flag 2pt+ gaps
- Added explicit instruction: only discuss matrix signals from the pre-filtered list; conflicted games → "matrices are split"

---

## R13 Matrix Signals (filtered, actionable)

| Game | Matrices | Direction |
|------|----------|-----------|
| Cronulla vs Manly | 7-way H2H + 7-way Handicap | **Cronulla win + cover** |
| Newcastle vs Parramatta | 3-way H2H + 3-way Handicap | **Parramatta covers (+14.5)** |
| Raiders vs Cowboys | 3-way H2H + 3-way Handicap | **Cowboys win + cover** |

Filtered out: Tigers/Bulldogs (H2H conflicted), Broncos/Dragons (handicap only).

---

## To update each round

After pricing + matrix confluence:
```powershell
cd C:\Users\ElliotBladen\Apps\BettingEngine
$env:PYTHONUTF8="1"; $env:BETMATE_ROOT="C:\Users\ElliotBladen\Apps"
& ".\.venv\Scripts\python.exe" scripts\matrix_confluence.py --season 2026 --round 13
# Then restart Baz:
& C:\Users\ElliotBladen\Apps\scripts\start_baz.ps1
```
No Supabase push needed — JSON is local, Baz reads it directly.

---

## Files changed

| File | Change |
|------|--------|
| `components/chat/ChatPanel.tsx` | `buildOddsContext` adds live handicap + totals lines |
| `BettingEngine/scripts/matrix_confluence.py` | Always writes `outputs/nrl_t9_confluence_latest.json` |
| `BettingEngine/baz_server.py` | `_load_confluence()`, `CONFLUENCE_JSON`, confluence per game |
| `app/api/chat/route.ts` | `buildContextBlock` matrix filter + top-level section; system prompt improvements |
