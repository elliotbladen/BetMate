# Session Handover — 2026-06-04
## NRL R14 Pricing + AFL R13 Matrices + AFL ML Retrain

---

### What Was Done This Session

#### 1. AFL R13 Matrix Confluence
- Ran `scripts/afl_matrix_confluence.py --season 2026 --round 13`
- Had to create fixture file first (`outputs/afl_round_prep/r13_2026/fixture_r13_2026.csv`) from hardcoded FIXTURE dict in `prepare_afl_round.py`
- **All 8 games flagged.** Top signals:
  - **West Coast vs Port Adelaide** — 9-way H2H BACK PORT + 6-way HANDICAP PORT COVERS (strongest signal of round)
  - **Adelaide vs Geelong** — 6-way H2H BACK GEELONG + 4-way HANDICAP (100% Crows vs Geelong matchup row)
  - **Hawthorn vs Bulldogs** — 6-way H2H + 4-way HANDICAP HAWKS (91.6% Hawks vs Bulldogs matchup row)
  - **Collingwood vs Melbourne** — 4-way H2H BACK COLLINGWOOD + 3-way TOTALS UNDERS
  - **North Melb vs Fremantle** — 5-way H2H BACK FREMANTLE (all Kangaroos' own rows pointing against them after a win)
- Confluence JSON saved to `outputs/afl_t9_confluence_latest.json`

#### 2. NRL R14 Full Pricing
- Ran `scripts/run_nrl_pricing.ps1` — auto-detected R14 (8 games, Warriors on BYE)
- All tiers ran. Key gaps:
  - **T6 refs: 0/8 loaded** — refs not yet announced (Wed). Re-run after scrape.
  - **T7 emotional: STALE** — latest emotional data is R0. Run `uv run python scrapers/nrl_emotional.py --round 14` then re-price.
  - **Weather: all clear** — NRL venues defaulted to clear (no lat/lng matched)
- Results saved: `results/r14_pricing_2026.csv` + `data/pricing/nrl/NRL_PRICING_R14_2026-06-04.csv`
- convert_pricing_files.py updated (R14 added to nrl_copies list)

**R14 Model Lines:**
| Game | Margin | Total |
|------|--------|-------|
| Manly vs Souths | Manly -3.3 | 51.5 |
| Melbourne vs Newcastle | Storm -0.6 | 53.4 |
| Canberra vs Roosters | Roosters -3.7 | 48.1 |
| Cowboys vs Dolphins | Dolphins -3.7 | 49.1 |
| Brisbane vs Gold Coast | Broncos -0.3 | 39.7 |
| Wests vs Panthers | Panthers -17.0 | 46.4 |
| Cronulla vs Dragons | Sharks -16.7 | 53.3 |
| Bulldogs vs Parramatta | Bulldogs -9.6 | 50.8 |

#### 3. NRL R14 Matrix Confluence
- Top 4-star signals: Brisbane vs Gold Coast (5-way BACK BRONCOS), Cowboys vs Dolphins (4-way BACK COWBOYS + 3-way OVERS), Wests vs Panthers (4-way BACK PENRITH), Cronulla vs Dragons (4-way H2H + 3-way HANDICAP CRONULLA)
- Canberra vs Roosters: 3-star ALIGNED — H2H + handicap both BACK RAIDERS, 121.6% matchup row
- Conflicted: Manly vs Souths, Melbourne vs Newcastle (H2H and handicap point different directions)

#### 4. Totals Signals (Both Sports)
Only 3 legitimate signals at the 3-way confluence threshold across both sports:
1. **Sydney vs St Kilda (AFL)** — 5-way UNDERS (strongest). Model: rules 194.6, ML 165.6 (-29pt gap)
2. **Collingwood vs Melbourne (AFL)** — 3-way UNDERS. Matrix-adjusted line: ~163 (ML-based, -3.7pt T9 adjustment). Rules 181.8, ML 166.8.
3. **Cowboys vs Dolphins (NRL)** — 3-way OVERS. Model total: 49.1.

#### 5. AFL ML Model Retrain (MAIN TASK)
Extended the training window from 2022–2023 to **2022–2024**.

**Files changed:**
- `BettingEngine/ml/afl/game_log.py`:
  - Line 43: XLSX default `afl (2) (1).xlsx` → `afl (4).xlsx`
  - Lines 400–402: Split logic changed — `season <= 2024` → 'train', `season == 2025` → 'test', else 'deploy'. Validate split removed.
- `BettingEngine/ml/afl/train.py`:
  - Lines 215–258: Added `has_val = len(X_val) > 0` guard — train.py no longer crashes when validate set is empty.

**Retrain results:**
- Train: 639 games (2022–2024), Test: 216 games (2025), Deploy: 63 (2026 R1–R12)
- Margin MAE: **30.45** (was 31.72) ↓
- Total MAE: **24.31** (was 24.61) ↓
- H2H Accuracy: **66.7%** (was 65.7%) ↑
- H2H LogLoss: **0.673** (was 0.830) — big improvement in calibration

Models saved to `BettingEngine/ml/afl/results/models/`.

---

### What Still Needs Doing

1. **Run NRL emotional scraper for R14** then re-price:
   ```powershell
   cd C:\Users\ElliotBladen\Apps
   & C:\Users\ElliotBladen\.local\bin\uv.exe run python scrapers/nrl_emotional.py --round 14
   & C:\Users\ElliotBladen\Apps\BettingEngine\scripts\run_nrl_pricing.ps1
   ```
2. **Re-run NRL pricing after Wednesday refs** (announced ~14:00 Wed)
3. **Re-run AFL R13 round prep** to get shadow predictions using new ML models:
   ```powershell
   cd C:\Users\ElliotBladen\Apps\BettingEngine
   $env:PYTHONUTF8="1"; $env:BETMATE_ROOT="C:\Users\ElliotBladen\Apps"
   & ".\.venv\Scripts\python.exe" scripts\prepare_afl_round.py --season 2026 --round 13
   ```
4. **Download fresh afl.xlsx** from aussportsbetting (R7–R12 2026 data now available). Re-run:
   ```powershell
   & ".\.venv\Scripts\python.exe" ml\afl\game_log.py --min-year 2022
   & ".\.venv\Scripts\python.exe" ml\afl\train.py --decay 1.5
   ```
   No split changes needed — 2024 is already in train.
5. **NRL R13 CLV** — not yet filed. Run after closing lines available.
6. **AFL R12 CLV** — not yet filed.

---

### Key Model Notes for This Round

- **Essendon vs Carlton** — biggest ML divergence of AFL R13: H2H probability gap +47.5% (ML much more bullish on Essendon than rules). Worth flagging manually.
- **Collingwood/Melbourne UNDERS** — three signals aligned: rules model (181.8), ML model (166.8), matrix (3-way UNDERS). Matrix-adjusted line ~163. If market is 170+, strong UNDERS value.
- **Sydney/St Kilda UNDERS** — 5-way matrix + ML 29pts below rules. Strongest totals signal of the round.
- **West Coast vs Port** — 9-way matrix H2H signal backs Port away. West Coast historically collapse in this fixture + June + Optus day game. Rules model also has Port winning.
