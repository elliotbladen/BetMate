# Session Diary — 2026-05-28: T9 Matrix Confluence Analyser

## What was done

Built `scripts/matrix_confluence.py` — a standalone script that scans the NRL fixture and identifies games where 3 or more independent matrix edges ≥20% all point the same direction.

### Background
The Cronulla vs Manly R13 game had been identified manually as a 7-way confluence trade (short rest, Thu/Fri, night game, after win, H2H win%, away win%, vs Cronulla). The goal is to automate this detection across all games every round.

### How it works
1. Loads fixture from `BETMATE_ROOT/data/nrl/fixture/processed/latest-fixture.json`
2. Loads all 3 matrices: NRL H2H (xlsx), NRL Totals (xlsx), NRL Handicap (CSV)
3. Queries SQLite DB for each team's rest days + last result (win/loss)
4. For each game, selects applicable matrix rows:
   - Generic: Win% Home, Win% Away, Cover Rate Home, Cover Rate Away
   - Time/Day: Night (≥18:00), Day (<18:00), Mon/Tue/Wed/Thu/Fri/Sat/Sun
   - Rest: Short Rest (≤6d), Long Rest (≥10d)
   - Form: After a Win, After a Loss
   - Opponent-specific: "vs {team}" rows from each matrix sheet
   - Venue: home stadium row from each matrix sheet
5. Normalises direction from team perspective to market direction (HOME_WIN / AWAY_WIN / HOME_COVERS / AWAY_COVERS / OVERS / UNDERS)
6. Groups edges by normalised direction per market; flags ⚡ where count ≥ min_edges and edge ≥ min_edge_pct

### R13 output summary (verified ✅)
- **Cronulla/Manly: 7-way H2H (BACK HOME) + 7-way HANDICAP (HOME COVERS)** — expected result confirmed
- Newcastle/Parramatta: 3-way H2H (BACK AWAY) + 3-way HANDICAP (AWAY COVERS)
- Wests Tigers/Bulldogs: 5-way H2H (BACK AWAY) + 4-way HANDICAP (HOME COVERS) + 3-way H2H (BACK HOME) — conflicted
- Broncos/Dragons: 3-way HANDICAP (AWAY COVERS)
- Raiders/Cowboys: 3-way H2H (BACK AWAY) + 3-way HANDICAP (AWAY COVERS)
- 5 games with 3+ signals out of 7 this round

### Supported options
- `--season`, `--round` — defaults to next upcoming round
- `--min-edges N` — minimum confluence count (default 3)
- `--min-edge-pct P` — minimum edge % (default 20.0)
- `--push` — pushes result to Supabase key `nrl_t9_confluence_r{round}_{season}`

## Files changed
- `scripts/matrix_confluence.py` — NEW (497 lines)
- `CLAUDE.md` — added T9 Confluence Analyser section to Key Scripts

## Git
- Committed to BettingEngine main: `8506d68`

## Status
- Script works correctly ✅
- **Not yet wired into pricing** — decision-support only. End-of-2026 review will use actual round results to quantify T9 value.
- AFL equivalent not yet built (AFL matrices have different structure)

## Next steps
- Run `--push` version weekly after fixture is loaded to store results in Supabase
- After season ends: correlate T9 flags with outcomes to determine if 3+ confluence predicts covers at statistically significant rate
- If yes (suggest ≥55% win rate over N≥20 qualifying games): wire into T9 pricing tier with a 5–10% cap
