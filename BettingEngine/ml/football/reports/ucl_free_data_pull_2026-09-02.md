# Free UCL data pull

SofaScore's public event endpoints supplied a second free data layer for the 342 mapped modern-era matches. The pull contains match-level expected goals plus possession, big chances, shots on target, corners, passing, fouls and cards. All 342 mapped events returned statistics; no rows were silently imputed.

Files:

- `data/ucl/xg/ucl_sofascore_match_xg.csv` — shotmap xG events.
- `data/ucl/xg/ucl_sofascore_match_stats.csv` — match statistics.

This gives us enough free information to rebuild and calibrate the totals model, subject to the existing 90.5% fixture mapping coverage. The remaining 36 matches stay goals-fallback/quarantined until a second fixture source resolves them.
