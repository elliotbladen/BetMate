# Session Diary — 2026-06-10
## Research Page Unit Fixes + predictedLine Backfill

---

### What was done this session

#### 1. Stake/Unit Display Fix (MODEL_BETS)

Many recent bets were staked at $25 (0.5 unit, where 1 unit = $50). The `plUnits` field was recording losses as `-1.00u` and wins at full-odds instead of halved values.

**Rounds affected and fixes applied:**

**R13 (ids 36–41) — all $25 stakes:**
- ids 36, 37: Warriors Under wins — corrected to +0.42u, +0.45u (were +0.84u, +0.90u)
- ids 38, 39: Panthers handicap losses — corrected to -0.50u each (were -1.00u)
- id 40: Tigers/Bulldogs Over loss — corrected to -0.50u (was -1.00u)
- id 41: Raiders/Cowboys loss — corrected to -0.50u (was -1.00u)

**R14 (ids 42–48) — all $20-$25 stakes:**
- id 42: Newcastle win — corrected to +0.43u (was +0.85u)
- ids 43–45, 47, 48: losses — corrected to -0.50u each (were -1.00u)
- id 46: Cronulla win — corrected to +0.46u (was +0.91u)

**Running total cascade:** recalculated from id:36 forward. Final running total at id:48 = 2.67u.

---

#### 2. predictedLine Backfill from BettingEngine CSVs

Several rows had wrong or missing `predictedLine` values — they were showing market handicap lines instead of the model's predicted margin/total.

**Corrections applied:**

| id | What was wrong | Fix |
|----|---------------|-----|
| 32 | `3.5` (market line) | `1.4` — R12 CSV: Bulldogs vs Storm `final_margin=1.44` |
| 33 | `1.67` (takenPrice copy) | `1.56` — R12 CSV: Cowboys `fair_home_odds=1.563` |
| 34 | `2.5` (market line) | `4.3` — R12 CSV: Cowboys vs Rabbitohs `final_margin=4.29` |

**Null fills (R13/R14):**

| id | Value filled | Source |
|----|-------------|--------|
| 40 | `48.5` | R13 CSV: Tigers vs Bulldogs `final_total=48.46` |
| 41 | `1.3` | R13 CSV: Raiders vs Cowboys `final_margin=1.34` (Canberra home) |
| 42 | `0.6` | R14 CSV: Storm vs Newcastle `final_margin=0.62` (Storm home) |
| 43 | `2.64` | R14 CSV: Cowboys vs Dolphins `fair_home_odds=2.639` |
| 44 | `39.7` | R14 CSV: Broncos vs Titans `final_total=39.69` |
| 45 | `46.4` | R14 CSV: Tigers vs Panthers `final_total=46.38` |
| 46 | `16.7` | R14 CSV: Cronulla vs Dragons `final_margin=16.68` |
| 47 | `9.6` | R14 CSV: Bulldogs vs Eels `final_margin=9.58` |
| 48 | `9.6` | Same game, same model margin |

**predictedLine convention (clarified this session):**
- Handicap bets: `final_margin` from pricing CSV (home team perspective, positive = home wins)
- Totals bets: `final_total`
- H2H bets: `fair_home_odds` or `fair_away_odds` for the selected team

---

#### 3. Git push to Vercel

Committed and pushed to `github.com/elliotbladen/BetMate` (main) → auto-deployed to betmate.au.
Commit: `5bd7b2a` — "Fill predictedLine for R13/R14 bets + fix R12 wrong values"

---

### Pending / Carry-forward

- **R14 CLV**: NRL R14 + AFL R13 closing lines still needed before running `update_clv_running.py` + `generate_model_accuracy.py`
- **G2 Origin squads**: Camp starts Jun 12 — populate `data/nrl/origin/2026.json` G2 nsw_squad + qld_squad before R15 pricing
- **G3 Origin squads**: Populate before R18 pricing (camp Jul 3)
- **Custom domain betmate.au**: www CNAME fix still pending
- **Refs on Vercel**: Wire `lib/referees.ts` to Supabase key
- **Supabase UNIQUE constraint**: `ALTER TABLE betmate_data_store ADD CONSTRAINT betmate_data_store_key_unique UNIQUE (key);`
- **AFL sigmoid ELO scaling**: Replace linear POINTS_PER_ELO with probability-based sigmoid (next AFL session)
- **AFL set-shot conversion tracker**: Medium-term improvement

---

### Notes on unit sizing convention

1 unit = $50. Most R13/R14 bets were placed at $25 = 0.5 unit. When logging future bets:
- Win P&L = (odds − 1) × stake_units
- Loss P&L = −stake_units
- Running total must be recalculated from the first changed entry downward
