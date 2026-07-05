# Session Diary — 2026-05-29: T9 Confluence — Totals Market + Per-Market Thresholds

## What was done

Completed the T9 confluence analyser for both NRL and AFL by:
1. Adding totals-market analysis (the scripts already loaded the totals matrix but didn't surface signals due to threshold mismatch)
2. Adding moon phase + month contextual rows (both were missing from earlier builds)
3. Wiring per-market thresholds throughout both scripts

## The core problem

AFL totals edges are structurally smaller than H2H/handicap edges — typically 3–15% vs 20–70%. Using the global 20% threshold meant zero totals signals were ever shown. The Carlton vs Geelong game had 4 applicable OVERS edges all >= 5% (vs Geelong 9.5%, vs Carlton 9.5%, Thu/Fri 8.4%, Full Moon 10.9%) but none appeared at 20%.

## Solution: per-market thresholds

### AFL (`scripts/afl_matrix_confluence.py`)
```python
MIN_EDGE_BY_MARKET  = {'totals': 5.0}   # h2h/handicap stay at 20%
MIN_COUNT_BY_MARKET = {'totals': 3}     # h2h/handicap stay at 3+
```

### NRL (`scripts/matrix_confluence.py`)
```python
MIN_EDGE_BY_MARKET  = {'totals': 10.0}
MIN_COUNT_BY_MARKET = {'totals': 3}
```

Both `analyse_game()` and `print_report()` now accept `min_edge_by_market` / `min_count_by_market` dicts. A `_meets_count()` helper in `main()` keeps the JSON output consistent with what the report shows.

## AFL R12 totals signals (new)

- **Carlton/Geelong — OVERS (3-way):** vs Geelong 9.5%, vs Carlton 9.5%, Thu/Fri 8.4%
- **Melbourne/GWS — UNDERS (3-way):** vs GWS 7.1%, vs Melbourne 7.1%, Full Moon 6.1%

## NRL R13 totals signals (new)

- **Newcastle/Parramatta — OVERS (3-way):** vs Parramatta 16.4%, vs Newcastle 16.4%, Total Points Away 10.4%
- **Wests Tigers/Bulldogs — OVERS (4-way):** Full Moon 20.9%, Full Moon 15.5%, vs Canterbury 13.4%, vs Wests 13.4%

## Full NRL R13 output summary (updated)

All 7 games flagged (vs 5 previously — storm+roosters and tigers/bulldogs gained new signals from full moon + totals):

| Game | Signals |
|------|---------|
| Cronulla/Manly | ⚡ H2H 8-way BACK HOME + ⚡ HANDICAP 7-way HOME COVERS |
| Newcastle/Parramatta | ⚡ H2H 4-way BACK AWAY + ⚡ HANDICAP 4-way HOME COVERS + ⚡ HANDICAP 3-way AWAY COVERS + ⚡ TOTALS 3-way OVERS |
| Tigers/Bulldogs | ⚡ H2H 7-way BACK AWAY + H2H 4-way BACK HOME (conflicted) + TOTALS 4-way OVERS + HANDICAP 4-way HOME COVERS + HANDICAP 3-way AWAY COVERS (conflicted) |
| Storm/Roosters | ⚡ HANDICAP 3-way AWAY COVERS |
| Broncos/Dragons | ⚡ H2H 3-way BACK HOME + ⚡ HANDICAP 3-way AWAY COVERS (conflicted) |
| Raiders/Cowboys | ⚡ H2H 4-way BACK HOME + H2H 3-way BACK AWAY (conflicted) + ⚡ HANDICAP 4-way AWAY COVERS |
| Panthers/Warriors | ⚡ HANDICAP 4-way AWAY COVERS |

## Files changed

- `scripts/afl_matrix_confluence.py` — per-market thresholds + moon phase + month
- `scripts/matrix_confluence.py` — per-market thresholds + moon phase + month

## Git

Committed to BettingEngine main: `3542904`

## Notes

- Full Moon May 30-31 2026 is adding significant signals this round (within ±1 day from May 29 onwards)
- AFL H2H conflicted signals (H2H points one way, handicap the other) are visible in the output but Baz's matrix filter suppresses them — only clean alignment gets surfaced to users
- The `--market` flag still works: `--market totals` to see only totals, etc.
