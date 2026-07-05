# Session Handover — 2026-06-04
## AFL ML Retrain: Extended Training Window (2022–2024)

---

### What We Did

Retrained the AFL XGBoost ML models to include the full 2024 season in the training window (was 2022–2023 only). Also updated the source XLSX to the latest available file.

---

### Files Changed

| File | Change |
|------|--------|
| `ml/afl/game_log.py` line 43 | XLSX default: `afl (2) (1).xlsx` → `afl (4).xlsx` (covers to 2026-04-26) |
| `ml/afl/game_log.py` lines 400–403 | Split: `season <= 2023 → train` changed to `season <= 2024 → train`. 2025 remains test. Validate split removed (was 2024). |
| `ml/afl/train.py` lines 215–258 | Added `has_val` guard to handle empty validate set without crashing on sklearn metrics. |
| `ml/afl/results/features_afl.csv` | Regenerated — 918 rows, splits: train=639, test=216, deploy=63 |
| `ml/afl/results/models/*.pkl` | All three models retrained and saved |
| `ml/afl/results/metrics.txt` | Updated with new metrics |

---

### Training Split (new)

| Season | Split | Games |
|--------|-------|-------|
| 2022 | train | 207 |
| 2023 | train | 216 |
| 2024 | train | 216 |
| 2025 | test | 216 |
| 2026 (R1–R12) | deploy | 63 |
| **Total train** | | **639** (was 423, +51%) |

---

### Metrics Comparison

| Metric | Old (2022–2023 train) | New (2022–2024 train) | Change |
|--------|----------------------|----------------------|--------|
| Margin MAE (test 2025) | 31.72 pts | **30.45 pts** | ↓ 1.27 ✅ |
| Margin DirAcc (test 2025) | 68.5% | 66.2% | ↓ 2.3% ⚠️ |
| Total MAE (test 2025) | 24.61 pts | **24.31 pts** | ↓ 0.30 ✅ |
| H2H Accuracy (test 2025) | 65.7% | **66.7%** | ↑ 1.0% ✅ |
| H2H LogLoss (test 2025) | 0.830 | **0.673** | ↓ 0.157 ✅ |
| H2H Brier (test 2025) | 0.255 | **0.224** | ↓ 0.031 ✅ |

Overall: genuine improvement across 4 of 6 metrics. Margin direction accuracy slight drop (2.3%) but absolute MAE improved. H2H calibration improved significantly (LogLoss -19%).

---

### Top Features (new models)

**Margin model:** form_margin_diff (9.3%), elo_diff (7.5%), elo_win_prob (7.4%)
**Total model:** home_off_big_win (5.7%), home_travel_km (4.6%), form_win_pct_diff (4.6%), venue_avg_total (4.1%)
**H2H model:** home_off_big_loss (6.6%), elo_diff (6.4%), away_win_streak (4.4%)

---

### Why We Did This

The model had never seen 2024 data during training — a full AFL season of patterns, rule adjustments, and team composition changes sitting unused. Adding 2024 to training gives 51% more data and the model learns from the most recent completed season before the 2025 test set.

The 2025 season remains a clean holdout — accuracy metrics are still independently verifiable.

---

### Option B — ALSO COMPLETE (same session)

Fresh xlsx downloaded Tuesday 2026-06-02 was found at `outputs/afl_weekly_review/historical/latest.xlsx` (816.3KB, covers to ~R12 2026).

- Re-ran `game_log.py --xlsx outputs/afl_weekly_review/historical/latest.xlsx --min-year 2022`
- Total games: **3,459** (was 3,416, +43 games = 2026 R7–R12)
- Deploy set: **106 games** (was 63) — full 2026 R1–R12 now in deploy
- Train/test metrics unchanged (same 2022–2024 train, 2025 test)
- ELO ratings updated through R12 2026
- **XLSX default in game_log.py updated** to `outputs/afl_weekly_review/historical/latest.xlsx` — future runs automatically use the weekly automated download, no manual path needed

### What's NOT Done Yet

- **Re-run AFL R13 round prep** to get shadow predictions using new models + fresh ELO:
  ```powershell
  cd C:\Users\ElliotBladen\Apps\BettingEngine
  $env:PYTHONUTF8="1"; $env:BETMATE_ROOT="C:\Users\ElliotBladen\Apps"
  & ".\.venv\Scripts\python.exe" scripts\prepare_afl_round.py --season 2026 --round 13
  ```
- **End-of-season retrain (Oct 2026)**: Add 2025 to training, make 2026 the test set. Set reminder.

---

### How to Retrain Again (future)

```powershell
cd C:\Users\ElliotBladen\Apps\BettingEngine
# 1. Download fresh afl.xlsx from aussportsbetting, save to Downloads
# 2. Update XLSX filename in game_log.py line 43 if needed
# 3. Regenerate features:
& ".\.venv\Scripts\python.exe" ml\afl\game_log.py --min-year 2022
# 4. Retrain:
& ".\.venv\Scripts\python.exe" ml\afl\train.py --decay 1.5
# 5. Re-run AFL round prep to get fresh shadow predictions:
$env:PYTHONUTF8="1"; $env:BETMATE_ROOT="C:\Users\ElliotBladen\Apps"
& ".\.venv\Scripts\python.exe" scripts\prepare_afl_round.py --season 2026 --round 13
```

---

### Also Done This Session

- **NRL R14 full pricing**: All tiers run. Results in `results/r14_pricing_2026.csv` + `data/pricing/nrl/NRL_PRICING_R14_2026-06-04.csv`. T6 refs at 0 (not yet announced — re-run after Wed). T7 emotional stale (R0). Warriors on bye.
- **AFL R13 matrix confluence**: All 8 games flagged. Top signals: West Coast vs Port (9-way H2H BACK PORT), Adelaide vs Geelong (6-way BACK GEELONG), Hawthorn vs Bulldogs (6-way H2H + 4-way handicap BACK/COVER HAWKS).
- **NRL R14 matrix confluence**: Top signals: Cronulla vs Dragons (4-way H2H + 3-way handicap CRONULLA), Canberra vs Roosters (3-way H2H + handicap aligned — 121.6% matchup row), Brisbane vs Gold Coast (5-way BACK BRONCOS).
- **Totals signals (both sports)**: Sydney vs St Kilda 5-way UNDERS (AFL), Collingwood vs Melbourne 3-way UNDERS (AFL), Cowboys vs Dolphins 3-way OVERS (NRL). Matrix-adjusted Collingwood/Melbourne total: ~163 (ML-based, -3.7 pt adjustment).
