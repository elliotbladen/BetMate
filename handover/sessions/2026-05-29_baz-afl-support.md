# Session Diary — 2026-05-29 — Baz AFL Support + Totals

## What was done

### Problem
Baz only covered NRL. When a user was on the AFL tab and asked Baz a question, the brain context was always NRL (hardcoded `?sport=` missing), and the system prompt told him to say "I'm strictly an NRL numbers man."

### Fix 1 — `baz_server.py` AFL context endpoint

- Added `_latest_afl_pricing_csv()` — globs `results/r*_afl_*.csv`, picks most recent by mtime
- Added `AFL_CONFLUENCE_JSON = BASE_DIR / "outputs" / "afl_t9_confluence_latest.json"`
- Added `_context_afl()` — reads AFL CSV columns (`rules_home_odds`, `rules_away_odds`, `rules_margin`, `rules_total`, `ml_margin`, `ml_total`, `ml_h2h`), builds game summaries including `ml_model` dict, loads AFL confluence
- `context_round` endpoint now dispatches on `?sport=NRL|AFL` query param

AFL R12 verified: 7 games, model + ML data present, confluence loaded.

### Fix 2 — `route.ts` sport routing

- `fetchBrainContext(sport = 'NRL')` — now accepts sport, passes `?sport=${sport}` to baz_server
- Body type updated: `{ messages, oddsContext?, sport? }`
- `sport` extracted from body, passed to `fetchBrainContext(sport ?? 'NRL')`

### Fix 3 — `ChatPanel.tsx` passes sport (PowerShell edit)

Added to fetch body:
```
sport: games[0]?.sport ?? 'NRL',
```

So when a user is on the AFL tab, Baz gets AFL brain context. NRL tab → NRL context as before.

### Fix 4 — Matrix filter hardened (route.ts `buildContextBlock`)

Previous filter had a gap: only checked H2H conflict, not handicap conflict or directional alignment.

New filter (applied in both top-level MATRIX SIGNALS section and per-game Matrix T9 line):
```typescript
const h2hConflicted = h2hClean.length > 1;
const hcapConflicted = hcapClean.length > 1;
const h2hSide = h2hClean.length === 1 ? (h2hClean[0][0].includes('HOME') ? 'HOME' : 'AWAY') : null;
const hcapSide = hcapClean.length === 1 ? (hcapClean[0][0].includes('HOME') ? 'HOME' : 'AWAY') : null;
const aligned = h2hSide !== null && hcapSide !== null && h2hSide === hcapSide;
if (!h2hConflicted && !hcapConflicted && aligned) { ... }
```

Effect on NRL R13: only **Cronulla vs Manly** passes (8-way H2H HOME + 7-way handicap HOME, aligned). Newcastle/Parra filtered (handicap conflicted HOME=4/AWAY=3). Raiders/Cowboys filtered (H2H conflicted HOME=4/AWAY=3).

Effect on AFL R12: only **Carlton vs Geelong** passes (4-way H2H HOME_WIN + 3-way handicap HOME_COVERS, aligned).

### Fix 5 — ML model display for AFL (route.ts `buildContextBlock`)

Added per-game line:
```
ML model: ${g.home} by ${ml.margin} | Total ${ml.total} | Home ${ml.home_odds} / Away ${ml.away_odds}
```
Only shown when `ml_model` is present on the game (AFL only; NRL games don't have this field).

### Fix 6 — System prompt updated for both sports

- Persona: "NRL and AFL analyst" (was "NRL analyst")
- Added AFL guidance: how to read rules vs ML divergence, compare to live market
- WHAT YOU NEVER DO: removed AFL from banned topics; kept EPL/racing/politics
- Off-topic response: now says "NRL and AFL numbers man"

---

## NRL R13 Matrix Signal (post-filter)

| Game | Signal |
|------|--------|
| Cronulla vs Manly | 8-way H2H HOME_WIN + 7-way handicap HOME_COVERS ⚡ |

All other NRL R13 games filtered (conflicted or misaligned).

## AFL R12 Matrix Signal (post-filter)

| Game | Signal |
|------|--------|
| Carlton vs Geelong | 4-way H2H HOME_WIN + 3-way handicap HOME_COVERS ⚡ |

Note: Carlton are the HOME team but big underdogs (rules: Geelong -44, ML: Geelong -2.3). Matrix is saying Carlton covers their line more often than implied.

---

---

## Fix 7 — Totals support wired to Baz (route.ts)

Added to `buildContextBlock`:

**TOTALS SIGNALS section** (new, after MATRIX SIGNALS):
- Filters games where `totals_OVERS` or `totals_UNDERS` ≥3 edges, no conflict (both directions can't both be ≥3)
- Shows model_total and ML total in the label
- Separate from MATRIX SIGNALS — totals signals don't require H2H+handicap to be present

**Per-game Totals T9 line** — `Totals T9: ⚡ N-way totals OVERS/UNDERS` shown in ALL GAMES section when clean totals confluence exists

**System prompt totals guidance** — Baz told to:
- Compare model_total to live market line (Totals (live market): Line X in odds context)
- NRL model bias: runs 5-10pts HIGH → gaps leaning unders are more meaningful
- AFL rules model bias: runs ~6pts LOW → gaps leaning overs are more meaningful
- AFL ML model total: second data point, when rules + ML agree direction = stronger
- TOTALS SIGNAL = matrix confirmation; conflicted = noise

### NRL R13 Totals Signals (current)
| Game | Signal | Model Total |
|------|--------|------------|
| Newcastle vs Parramatta | 3-way OVERS | 58.7 |
| Wests Tigers vs Canterbury | 4-way OVERS | 48.5 |

Note: NRL model runs HIGH — compare to live market line carefully. If market is at 48.5 for Wests/Canterbury and matrix says OVERS at 4-way, the market line may already price it in.

### AFL R12 Totals Signals (current)
| Game | Signal | Model Total | ML Total |
|------|--------|------------|---------|
| Carlton vs Geelong | 3-way OVERS | 186.9 | 172.5 |
| Melbourne vs GWS | 3-way UNDERS | 190.9 | 161.6 |

Note: AFL rules model runs LOW (~6pts). Carlton OVERS: both models high but diverge (rules 186.9 vs ML 172.5). Melbourne UNDERS: rules 190.9 but ML 161.6 — big divergence, ML supports the under more strongly.

---

## Files changed

| File | Change |
|------|--------|
| `BettingEngine/baz_server.py` | `_context_afl()`, `_latest_afl_pricing_csv()`, `AFL_CONFLUENCE_JSON`, `context_round(sport=)` dispatch |
| `app/api/chat/route.ts` | `fetchBrainContext(sport)`, body `sport` extraction, matrix filter hardened, ML model display, totals signals section, totals per-game display, system prompt AFL scope + totals guidance |
| `components/chat/ChatPanel.tsx` | `sport: games[0]?.sport ?? 'NRL'` in fetch body (PowerShell edit) |
| `CLAUDE.md` | Baz section updated, current state updated |

---

## To restart Baz (after any baz_server.py changes)

```powershell
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Start-Process -FilePath "C:\Users\ElliotBladen\Apps\BettingEngine\.venv\Scripts\python.exe" `
  -ArgumentList "C:\Users\ElliotBladen\Apps\BettingEngine\baz_server.py" `
  -WorkingDirectory "C:\Users\ElliotBladen\Apps\BettingEngine" `
  -WindowStyle Hidden
# Then start tunnel:
& C:\Users\ElliotBladen\Apps\scripts\start_baz.ps1
```

Or just:
```powershell
& C:\Users\ElliotBladen\Apps\scripts\start_baz.ps1
```
