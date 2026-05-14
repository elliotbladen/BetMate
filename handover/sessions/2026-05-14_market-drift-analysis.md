# Session 2026-05-14 — Market Drift Analysis

## What was done

### Continued from previous context window
- Odds snapshot fix (PEP 723 inline deps, uv run syntax, $ErrorActionPreference fix) — completed in prior context
- Research page bets + ROI stat card + P&L fix — completed in prior context
- Missing odds fill (algebra on cumPL diffs) — completed in prior context

### New this session

**`scripts/market_hammered_drift.py`** — run successfully
- Reads `data/nrl/historical/latest.xlsx` (3 seasons, 719 games)
- Finds all H2H and handicap cases where a team's odds drifted OUT >= 15% from open to close
- H2H: 172 cases, 28.5% win rate for hammered teams
- Handicap: only 1 case (line itself moves so odds stay near 1.90 — expected)
- By-team breakdown: St George (20x, 15% win), Canterbury (16x, 19%), Wests (15x, 13%) get hammered most and are usually right. Penrith (4x, 75%), Dolphins (8x, 50%), Brisbane (6x, 50%) get hammered but still win.

**`scripts/shortened_team_roi.py`** — new script, run successfully
- Flips the question: if you back the SHORTENED team (opponent was hammered) in every case, what's the ROI?
- 170 bets, 70.6% win rate, avg closing odds 1.427 → **-2.32% ROI overall** (vig eats the thin edge)
- Key findings by odds bucket:
  - 1.50-1.70 close: only 46% win rate, -26.3% ROI — market overconfident here
  - 2.00-2.50 close: 67% win rate, +48.3% ROI — underpriced despite shortening
- By drift size: 40-60% hammering gives -21.8% ROI (panic zone, overreaction); 60%+ gives +14.1% ROI (extreme moves are usually right)
- Teams market backs but wrong: Gold Coast (-58.7% ROI), St George (-36.8% ROI)
- Teams where backing the shortened side is profitable: Dolphins (+41.5%), Canberra (+34.5%), Manly (+16.3%), Newcastle (+16.2%)

## Pending (user sleeping on it)
- **Systematic shortening/lengthening analysis**: full 2×3 matrix (Fav/Dog × Shortened/Flat/Lengthened) with ROI per cell — for H2H and handicap. Data is in xlsx. User wants to think before building.
- BVI weekly Task Scheduler task (Monday 08:00, `afl_bvi.py`) — still pending
- Odds movement alert threshold filter (>= 10% change_pct only)

## Key data location
- `scripts/market_hammered_drift.py` — H2H + handicap drift >= 15%, win/cover rates
- `scripts/shortened_team_roi.py` — ROI of backing shortened side, by odds bucket + drift + team
- Source data: `data/nrl/historical/latest.xlsx` (header=1, row 0 = merged title)
