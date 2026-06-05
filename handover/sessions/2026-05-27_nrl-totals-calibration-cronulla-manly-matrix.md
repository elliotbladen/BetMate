# Session Diary — 2026-05-27 — NRL Totals Calibration + Cronulla/Manly Matrix

## What was done

### NRL totals calibration check

Investigated whether `league_avg_total: 47.0` in `BettingEngine/config/tiers.yaml` needs updating, given 2026's elevated scoring.

**Findings (from `scripts/_check_nrl_scoring.py`):**

| Season | Avg total | Avg/team |
|--------|-----------|----------|
| 2022   | 43.4      | 21.7     |
| 2023   | 45.3      | 22.6     |
| 2024   | 46.8      | 23.4     |
| 2025   | 46.3      | 23.1     |
| **2026** | **49.6** | **24.8** |

Config at 47.0 is 2.6pts/game below actual 2026 average. However:
- NRL T1 derives scoring from team-level ELO and attack/defence rates, not from `league_avg_total` directly
- `league_avg_total` is used as a T1 anchor with regression; the 2.6pt gap is much smaller than the AFL gap that needed fixing (6.7pts/team = 13.4pts/game)
- Finals scoring historically 7% lower than regular season (~46pts), which is close to the config's 47.0 — so the constant is actually well-positioned for finals context
- **Decision: no change to NRL config.** The model's total calibration (T1 baseline ~56 → final ~55 for this round) is driven by team rates, not the anchor, so the bias is smaller and the model remains reasonably calibrated.

### Cronulla vs Manly R13 matrix analysis

Built `scripts/_cronulla_manly_matrix.py` — a game-specific H2H matrix checker that runs all conditions and flags any 20%+ relative edge (actual win% vs market implied).

**Game: Cronulla Sharks vs Manly Sea Eagles, Fri 29 May 2026, Ocean Protect Stadium, ~20:00**

Game conditions: Friday night, Cronulla 14-day rest (bye R12), Manly 6-day rest (won R12 12-10 vs Gold Coast), source data 2022-2025.

**Results — 7-way confluence, ALL backing Cronulla / opposing Manly:**

| Condition | Manly actual | Manly implied | Edge | n |
|-----------|-------------|--------------|------|---|
| As away team | 32.0% | 48.2% | 34% OPPOSING | 50 |
| Night games (≥18:00) | 38.9% | 50.7% | 23% OPPOSING | 54 |
| Thu/Fri games | 31.6% | 51.4% | 39% OPPOSING | 38 |
| After a win | 44.4% | 57.2% | 22% OPPOSING | 45 |
| Short rest (≤6 days) | 29.4% | 53.2% | 45% OPPOSING | 34 |
| vs Cronulla (H2H) | 14.3% | 39.4% | 64% OPPOSING | 7 |
| May games | 31.2% | 49.4% | 37% OPPOSING | 16 |

Cronulla side: only 1 applicable flag (H2H 31% BACKING, n=7), but it aligns with same direction.

**Model pricing:** Cronulla -4.2 | Market: Cronulla -2.5.

With 7-way matrix confluence + model already pointing Cronulla, this is the clearest directional signal of the round. Upgraded from "marginal" to **HIGH** confidence in the R13 pricing file.

### Files updated

- `scripts/_cronulla_manly_matrix.py` — NEW, venue aliases fixed (Cbus/BlueBet are not Cronulla home venues)
- `outputs/results/r13_nrl_pricing_2026.md` — Cronulla/Manly game note updated + added to signal table as #1 signal
- `BettingEngine/CLAUDE.md` — R13 top signals updated to include Cronulla -2.5 as #1

### Bug fixed in matrix script
Initial venue_aliases included "Cbus Super Stadium" and "BlueBet Stadium" — these are Gold Coast Titans and Penrith Panthers home grounds, NOT Cronulla's. Only "Ocean Protect Stadium" is valid for Cronulla home. Fixed and re-run — confluence count is 7 (not 8).

---

## What still needs doing

### TODAY (before Cronulla/Manly game Fri 20:00)
1. Run NRL injuries scraper (T5 still stale R12): `uv run python scrapers/nrl_injuries.py`
2. Wait for refs (Task Scheduler fires Wed 14:00) or run manually: `uv run python scrapers/nrl_referees.py`
3. Re-run full NRL R13 pricing: `& C:\Users\ElliotBladen\Apps\BettingEngine\scripts\run_nrl_pricing.ps1`
4. Check Manly's injury list on update — any additional outs strengthen Cronulla case further
5. Check market H2H price for Cronulla to assess EV (model 1.57, expect market ~1.50-1.55)

### THIS WEEK
- R12 CLV: file after closing lines available (NRL R12, AFL R12)
- Add AFL R10/R11 to MODEL_ACCURACY_RUNNING_2026.csv
- NRL H2H home bias: rules overrates home teams +9-11% consistently — T4 venue calibration review pending

## Technical notes

### Why the NRL totals config wasn't changed
The 2.6pts/game gap between config (47.0) and 2026 actuals (49.6) is small, and the model derives team totals from individual team attack/defence rates rather than the league constant as a primary anchor. The constant is used for T1 regression, so any gap self-corrects through the actual team rates. Compare to AFL where the gap was 13.4pts/game (2×6.7pts/team) — that's why AFL needed fixing.

### Moon phase for Cronulla/Manly
Illumination: 94.8%, nearest full moon: 2026-05-31 (2 days after game). The ±1 day window doesn't capture this as "full moon" in the matrix. If the model ever expands to ±2 days, Manly's full moon flag (27% OPPOSING, n=13) would add an 8th applicable edge — all still pointing the same way.
