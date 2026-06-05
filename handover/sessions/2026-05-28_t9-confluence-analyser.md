# Session Diary — 2026-05-28: T9 Matrix Confluence Analyser

## Context
Earlier this session covered the weather classification bug (DEW RISK vs SHOWERS for Cronulla/Manly) and an architecture audit. This diary covers the T9 confluence work.

## What was requested
User wanted a script that automatically detects games where 3 or more independent matrix edges of ≥20% all point the same direction — exactly the kind of analysis that identified Cronulla as the #1 signal this round.

## What was built

### `BettingEngine/scripts/matrix_confluence.py`
New 497-line script. For each game in the NRL fixture:

1. **Loads context from DB:** rest days + last result (win/loss) per team
2. **Selects applicable matrix rows** across all 3 matrices:
   - Generic win rates: Win% Home, Win% Away, Cover Rate Home/Away
   - Time of day: Night (≥18:00), Day (<18:00)
   - Day of week: Mon–Sun
   - Rest bucket: Short Rest (≤6d) or Long Rest (≥10d)
   - Recent form: After a Win / After a Loss
   - Opponent-specific: "vs {team}" rows from each matrix sheet
   - Venue rows from each matrix sheet
3. **Normalises direction** from each team's perspective to a unified market direction (HOME_WIN / AWAY_WIN / HOME_COVERS / AWAY_COVERS / OVERS / UNDERS)
4. **Groups and counts** — flags ⚡ where N≥3 edges all point same direction

### Verified R13 output
```
Cronulla/Manly:        ⚡ H2H 7-way (BACK HOME) + ⚡ HANDICAP 7-way (HOME COVERS)
Newcastle/Parramatta:  ⚡ H2H 3-way (BACK AWAY) + ⚡ HANDICAP 3-way (AWAY COVERS)
Tigers/Bulldogs:       ⚡ H2H 5-way (BACK AWAY) + ⚡ HANDICAP 4-way (HOME COVERS) — conflicted
Broncos/Dragons:       ⚡ HANDICAP 3-way (AWAY COVERS)
Raiders/Cowboys:       ⚡ H2H 3-way (BACK AWAY) + ⚡ HANDICAP 3-way (AWAY COVERS)
```

## Important: this is decision-support only
The script flags signals for manual review. T9 is not wired into pricing yet. After the 2026 season we'll check: do 3+ confluence games cover at ≥55% over N≥20 games? If yes, incorporate with 5–10% cap.

## Files changed
- `BettingEngine/scripts/matrix_confluence.py` — NEW (committed `8506d68`)
- `BettingEngine/CLAUDE.md` — added T9 section to Key Scripts
- `Apps/CLAUDE.md` — added T9 confluence results to NRL R13 section + Key Files table

## How to run weekly
After Tuesday fixture loads:
```powershell
cd C:\Users\ElliotBladen\Apps\BettingEngine
$env:PYTHONUTF8="1"; $env:BETMATE_ROOT="C:\Users\ElliotBladen\Apps"
& ".\.venv\Scripts\python.exe" scripts\matrix_confluence.py --season 2026 --round 14
```
Add `--push` to store to Supabase (`nrl_t9_confluence_r14_2026`).
