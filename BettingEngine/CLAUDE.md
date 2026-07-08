# BettingEngine — Claude Context

---

## HOW TO START A SESSION

1. Read **Current State** below — this tells you what's happening right now
2. Check `handover/sessions/` for the latest diary if you need more detail
3. Do NOT ask "what were you working on?" — the answer is here

---

## CURRENT STATE
**Last updated:** 2026-07-08 (Work/home machine git divergence reconciled — see handover `2026-07-08_machine-reconcile-architecture.md`. Work machine had the live data + Jul 7 NRL work; home machine's monorepo import carried a stale BettingEngine copy EXCEPT the Jul 5 EPL engine build and Jul 5 AFL ML retrain, which only existed in git history. Both sides merged: working tree kept for everything, HEAD restored for `ml/afl/*` + EPL tree. ⚠️ AFL ML .pkl models are NOT in git — re-run `ml/afl/game_log.py` + `ml/afl/train.py` on this machine before next AFL ML shadow run. ⚠️ Diary `2026-07-05_afl-ema-form-split-models.md` was never committed — it exists only on the home computer; commit + push it from there.)
**Update this section at the end of every session, before writing the handover diary.**

### EPL Engine — FULL BUILD COMPLETE 2026-07-05 (built on home machine)
Full session diary: `handover/sessions/2026-07-05_epl-engine-build.md`
Architecture doc: `WorldCupEngine/ml/epl/ARCHITECTURE.md`

**Production pricer working:**
```bash
python3 WorldCupEngine/ml/epl/price_match.py \
  --home "Arsenal" --away "Man City" --ref "A Taylor" \
  --injuries-home "ST" --injuries-away "AM" \
  --mkt-home 2.40 --mkt-draw 3.50 --mkt-away 3.00 --mkt-over25 1.85
```

**Backtest results (3-season walkforward, 2021/22–2023/24):**
- RPS: **0.1335** (academic benchmark = 0.1925 — we beat it by 30%)
- Brier: 0.1910, LogLoss: 0.5654, H2H Acc: 54.2%

**Tier stack (all wired into price_match.py):**
- T2 PPDA: pressing matchup ±0.15 xG
- T3 Form + rest days (fatigue ×0.94 if ≤4 days)
- T5 Injuries: position weights (ST=−9% att, GK=−6% def etc) via `--injuries-home "ST,AM"`
- T6 Referee: historical goals/game deviation ±0.15 xG
- T7 Set-piece: corners won/conceded, 0.35 weight, ±0.08 xG cap
- Isotonic calibration: over25 only, expanding window, 1,139 rows

**Data refresh for August GW1:**
1. `python3 WorldCupEngine/ml/epl/fetch/fetch_results.py`
2. `python3 WorldCupEngine/ml/epl/fetch/fetch_understat_xg.py`
3. `python3 WorldCupEngine/ml/epl/fetch/fetch_style_stats.py`
4. `python3 WorldCupEngine/ml/epl/backtest/walk_forward.py`

**CatBoost (T8): tested, rejected** — 1,517 training rows too few (overfits). Revisit when 10+ seasons available (~4,000 rows).

### AFL ML Model — SPLIT FEATURE SETS + EMA FORM 2026-07-05 (built on home machine)
Full session diary: `2026-07-05_afl-ema-form-split-models.md` — **⚠️ NOT YET COMMITTED, lives on home computer only**

**Three models now have separate feature sets:**

| Model | Features | Key additions |
|-------|----------|---------------|
| H2H Classifier | 22 (original set) | No EMA — hurts binary accuracy |
| Margin Regressor | 30 (+ EMA) | `opp_adj_margin_diff` is #1 feature (9.2%) |
| Total Regressor | 30 (+ EMA) | Same as margin |

**EMA features added to margin/total models:**
- `home_ema_win_pct`, `home_ema_margin`, `home_opp_adj_margin`
- `away_ema_win_pct`, `away_ema_margin`, `away_opp_adj_margin`
- `ema_margin_diff`, `opp_adj_margin_diff`
- Window: 8 games, EMA decay: 0.75 per step back
- Opposition-adjusted: `margin × (opponent_elo / 1500)`

**Final retrained model metrics (2025 test, 216 games):**
- H2H Accuracy: **71.8%** (was 72.2% before EMA, recovered from 70.4% dip), LogLoss: 0.573, Brier: 0.194
- Margin MAE: **28.5 pts** (was 29.7 pts — 1.2pt improvement, MoSHBODS territory)
- Total MAE: 24.1 pts

**Industry benchmark:** H2H 71.8% = upper end of bookmaker market accuracy. Margin 28.5 pts = top-tier public model level.

**Betting signal confirmed (2025 backtest, 216 games):**
- H2H: Conf ≥65% → 102 bets, **84.3% strike, +11.2% ROI**
- H2H: **Conf ≥65% + EV≥0% + Odds≥1.50** → 26 bets, **+23.3% ROI** ← primary signal
- H2H: Conf ≥70% + EV≥0% + Odds≥1.50 → 12 bets, **+24.0% ROI**
- Handicap: ML edge ≥12 pts → 104 bets, **55.8% strike**
- Totals: ML edge ≥15 pts → 62 bets, **62.9% strike**

**Betting rule (updated — primary signal is now confidence-based not EV-only):**
> Conf ≥65% + EV ≥0% + Odds ≥1.50 = bet trigger (~26 bets/season)
> Models agree ≤10% = full stake. Models disagree = half stake.
> EV calculation: OddsPortal opening odds only. Never Betfair prices.

**Previous rule (EV≥+15% trigger) still valid as secondary filter** — use whichever produces more bets in practice. The confidence filter is a cleaner signal from the calibrated model.

**Rules model NOT yet integrated into ML pipeline** — kept separate. Revisit blending after another season of live validation.

**Deployment note:** the `.pkl` model files are not tracked in git — after pulling ML code changes on either machine, regenerate locally before the next ML shadow run:
```powershell
cd C:\Users\ElliotBladen\Apps\BettingEngine
& ".\.venv\Scripts\python.exe" ml\afl\game_log.py --xlsx outputs\afl_weekly_review\historical\latest.xlsx
& ".\.venv\Scripts\python.exe" ml\afl\train.py
```
✅ **Work machine regenerated 2026-07-09** with the EMA/split-feature code + Jul 7 xlsx (999 games, deploy=144). Test-2025 metrics on this xlsx: Margin MAE 29.27 / DirAcc 68.5%, Total MAE 24.48, H2H Acc 68.5% LogLoss 0.576. (Slightly different from the home machine's diary numbers — expected, newer xlsx snapshot.)

### AFL 2026 — Round 17 (Jul 2–5) — FULLY RE-PRICED 2026-07-02
- ELO rebuilt on latest historical xlsx before pricing (990-game deploy window, 135 games in 2026 season)
- `results/r17_afl_2026.csv` (9 rows) + full writeup `outputs/results/r17_afl_pricing_2026.md`
- **Manual T5 fix:** Footywire injury scrape was down (503) — used the 2026-06-30 curated injury file as base, but a fresh emotional-flags scrape caught Jordan Dawson (Adelaide's captain, elite midfielder) missing entirely — out for personal reasons (bereavement), not a medical injury so Footywire wouldn't have it anyway. Added manually to `outputs/afl_round_prep/r17_2026/injuries_r17_2026.json`. Moved Eagles/Crows T5 handicap from +6.0 to -2.0.
- Top signals: **Adelaide -32.5** @ Eagles (6-way H2H + 5-way handicap T9 matrix, rules+ML agree direction) | **Hawthorn -14.5** @ Demons (rules+ML both clear market by 9pt+)
- **Power vs Kangaroos flagged AVOID** — only game this round where rules and ML disagree on winner (rules: coin flip, ML: Kangaroos), despite an 8-way H2H matrix stack (two 100% historical splits) backing Power. Clean example of the model-alignment betting rule overriding a strong matrix signal.
- **Richmond/Carlton and Essendon/St Kilda both show the known extreme-ELO-gap undercook** — rules and ML agree with each other but sit 9-12pts short of market. T2 style-matchup layer hit its ±4.0 cap on 5/9 games this round. Reinforces the backlogged sigmoid ELO→margin rescale as the real fix, not a per-round patch.
- Predictions pushed live to betmate.au via `scripts/push_afl_predictions.py` (main repo).

### AFL Halftime Model — CALIBRATED 2026-06-19
- BASELINE_ACCURACY updated: 0.52 → **0.529** (fitted on 875-game dataset; per-year: 0.534/0.523/0.532/0.528/0.531)
- H2 total lookup table confirmed accurate against data (within 0.5 pts per band — no changes needed)
- Accuracy trend (ACCURACY_TREND_WEIGHT=1.0) has near-zero historical predictive power (corr=-0.04) but retained per user preference
- I50/clearance/clanger weights remain research-estimated (0.4/0.3/0.5) — historical dataset lacks per-quarter team stats; re-calibrate when 50+ live observations available
- FootyWire live stats scraping working (afl_ht_live.py → enrich_with_live_stats → inside 50s, clearances, clangers)
- betmate.au/api/afl-predictions used as primary pre-game pricing source; CSV fallback

### NRL Halftime Model — RECALIBRATED 2026-06-14
- Sign convention bug fixed: `pg_hcap = -_safe_float(pregame.get("fair_hcap_line", 0))`
- Constants updated: REGRESSION_FACTOR=0.55, POINTS_PER_ERROR_DIFF=1.4, RESTART_NET_PTS=0.72, RESTART_H2_DEFLATION=0.36, CONVERSION_ADJ_CAP=2.0
- Restart calc: `(home-away) * RESTART_NET_PTS * RESTART_H2_DEFLATION` (was `* 4.5 * 0.80`)
- Validated on Warriors 6 vs Sharks 8 (R15 2026) — output sensible, model working

### AFL Halftime Pipeline — BUILT 2026-06-14
- `scripts/fetch_afl_ht_scores.py` — scrapes afltables.com Q1-Q4 scores; 875/885 matched (98.9%)
- `scripts/afl_ht_h2h_matrix.py` — AFL HT matrix, same structure as NRL; output `outputs/afl_ht_h2h_matrix.xlsx`
- `scripts/afl_ht_live.py` — polls Squiggle API every 30s for halftime; fires `halfTime_price_afl.py`
- `scripts/halfTime_price_afl.py` — AFL Bayesian HT model (REGRESSION_FACTOR=0.45)
- Dataset: `data/inplay/afl/halftime/processed/halftime_dataset.csv` (885 rows, 875 with HT scores)
- In-play booking: Betfair pool only legal option in AU for AFL HT; no fixed-odds in-play operators

### World Cup 2026 Engine — BUILT 2026-06-14
- `WorldCupEngine/` — complete engine: Dixon-Coles + ELO, 6 tiers, Monte Carlo simulation
- **CRITICAL NEXT STEP**: Download ELO data from Kaggle → `WorldCupEngine/data/elo/international_elo_history.csv`
- See `WorldCupEngine/data/elo/DOWNLOAD_ELO_DATA.txt` for instructions
- Groups in `data/fixtures/wc2026_groups.yaml` — verify against official FIFA draw
- Commands: `python scripts/price_game.py --home France --away Argentina --stage gw1`
- Monte Carlo: `python scripts/run_simulation.py --sims 100000` → advancement market signals

### NRL 2026 — Round 14 (Jun 5–8) — PRELIMINARY
- Priced 2026-06-04 — `results/r14_pricing_2026.csv` + `data/pricing/nrl/NRL_PRICING_R14_2026-06-04.csv`
- **T6 refs NOT loaded (0/8)** — re-run `run_nrl_pricing.ps1` after Wednesday 14:00 refs scrape
- **T7 emotional STALE (R0 data)** — run `uv run python scrapers/nrl_emotional.py --round 14` first
- Warriors on BYE this round
- Top matrix signals: Cronulla vs Dragons (4-way H2H + 3-way handicap CRONULLA), Canberra vs Roosters (121.6% matchup row — huge), Brisbane vs Gold Coast (5-way BACK BRONCOS), Wests vs Panthers (4-way BACK PENRITH)
- Totals: Cowboys/Dolphins 3-way OVERS (model 49.1)

### AFL 2026 — Round 13 (Jun 5–8) — PRICED
- Priced 2026-06-04 — `results/r13_pricing_2026.csv` (8 rows)
- **ML models RETRAINED 2026-06-04** — see below
- Top matrix signals: West Coast vs Port (9-way H2H BACK PORT + 6-way handicap PORT COVERS), Adelaide vs Geelong (6-way H2H BACK GEELONG + 4-way handicap), Hawthorn vs Bulldogs (6-way H2H + 4-way handicap HAWKS)
- Totals: Sydney/St Kilda 5-way UNDERS, Collingwood/Melbourne 3-way UNDERS (matrix-adjusted line ~163 ML-based)
- Key ML divergences: Essendon vs Carlton (H2H +47.5% ML vs rules — biggest divergence of round), Kangaroos vs Fremantle (margin +16pt gap), Suns vs Lions (margin +10pt, total -24pt gap)

### AFL ML Models — RETRAINED 2026-06-04
- **Training window extended: 2022–2024** (was 2022–2023). 2025 remains test holdout.
- Train games: **639** (was 423, +51%)
- New metrics vs old (test on 2025, n=216):

| Metric | Old | New | Change |
|--------|-----|-----|--------|
| Margin MAE | 31.72 pts | **30.45 pts** | ↓ 1.3 ✅ |
| Total MAE | 24.61 pts | **24.31 pts** | ↓ 0.3 ✅ |
| H2H Accuracy | 65.7% | **66.7%** | ↑ 1.0% ✅ |
| H2H LogLoss | 0.830 | **0.673** | ↓ 0.157 ✅ |

- Files changed: `ml/afl/game_log.py` (XLSX → `afl (4).xlsx`, split extended to 2024), `ml/afl/train.py` (empty-val guard added)
- **Next**: Download fresh afl.xlsx when R7–R12 2026 data is on aussportsbetting, re-run game_log.py + train.py (no split changes needed). End-of-season retrain: add 2025 to train, make 2026 test.

### NRL 2026 — Round 13 (May 29–31) — COMPLETE
- Results: Cronulla 28–22 Manly ✅, Newcastle 28–22 Parramatta, Wests 22–16 Canterbury, Storm 18–4 Roosters, Dragons 30–26 Broncos (upset), Raiders 26–12 Cowboys, Panthers 20–18 Warriors
- Pricing files: `results/r13_pricing_2026.csv` + `outputs/results/r13_nrl_pricing_2026.md`

### AFL 2026 — Round 12 (May 28–31) — COMPLETE
- Priced 2026-05-27 — `results/r12_afl_2026.csv` (7 rows)
- Analysis: `outputs/results/r12_afl_pricing_2026.md`

### NRL 2026 — Round 12 (May 21–24) — COMPLETE

| Task | Status |
|------|--------|
| R12 fixture inserted | ✅ |
| R12 pricing | ✅ `data/pricing/nrl/NRL_PRICING_R12_2026-05-25.csv` |
| R12 bets logged | ✅ `data/bets/weekly/2026-05-25_AFL-R11_NRL-R12.csv` |
| R12 CLV | ⏳ Opening/closing lines not yet available |

### Data Folder Structure — REORGANISED 2026-05-25

All output data now lives in `data/` with consistent naming. Old scattered files in
`results/` and `outputs/` remain as source copies — canonical versions are in `data/`.

```
data/
├── bets/
│   ├── actual_bets_2026.csv           master ledger (44 bets as of R12)
│   └── weekly/                        YYYY-MM-DD_AFL-RXX_NRL-RXX.csv
├── clv/
│   ├── nrl/                           NRL_CLV_R{rr}_{date}[_suffix].csv
│   ├── afl/                           AFL_CLV_R{rr}_{date}[_suffix].csv
│   └── running/
│       ├── actual_bets_clv_2026.csv   per-bet CLV data
│       ├── model_clv_supplement_nrl_2026.csv  R8/R9 game-level CLV (no actual bets)
│       ├── NRL_CLV_running_2026.csv   NRL running total (R8–R11, +7.94% avg)
│       └── AFL_CLV_running_2026.csv   AFL running total (R8–R9, +0.72% avg)
├── model_accuracy/
│   ├── nrl/                           NRL_MODEL_ACCURACY_R{rr}_{date}.csv
│   ├── afl/                           AFL_MODEL_ACCURACY_R{rr}_{date}.csv
│   └── MODEL_ACCURACY_RUNNING_2026.csv
└── pricing/
    ├── nrl/                           NRL_PRICING_R{rr}_{date}[_suffix].csv
    └── afl/                           AFL_PRICING_R{rr}_{date}[_suffix].csv
```

**Naming convention:** `{SPORT}_{TYPE}_R{rr:02d}_{YYYY-MM-DD}[_suffix].csv`
- CLV suffixes: `_ml_comparison`, `_ml_shadow`, `_rules_vs_ml`, `_manual`
- PRICING suffixes: `_ml_shadow`, `_tier_breakdown`, `_t1t2t3t4`

**BETMATE_ROOT fix applied 2026-05-19:** Use `scripts/run_nrl_pricing.ps1` wrapper (sets env vars, runs pricing + export). Do NOT run `prepare_round.py` directly without BETMATE_ROOT set — it will find the wrong BetMate root (`Apps\BetMate` old repo).

**Tuesday's pipeline (2026-05-12) — all tasks now fire on Tuesday:**
1. 09:00 — `fetch_nrl_results.py` (auto — R10 results → DB)
2. 10:00 — BetMate `nrl_injuries.py` (auto)
3. 17:00 — BetMate NRL Historical Results (auto — fixed uv path)
4. 18:00 — BetMate NRL Style Stats (auto — fixed uv path)
5. 18:05 — BetMate NRL Round Prep (auto — fixed uv path)
6. 19:03 — `prepare_round.py --round 0 --season 2026` (auto)

**R10 results loaded manually 2026-05-12** (fetch task had failed). R11 results fetch is next Monday.

Note: `prepare_round.py` now runs matrix regeneration as **step 8** automatically.
Use `--skip-matrices` if historical xlsx hasn't been updated yet.

### DB
- Canonical DB: `data/model.db` ✅ (confirmed 2026-05-06)
- `betting_engine.db` deleted — was empty, never used

### NRL 2026 — Round 11 (Magic Round, May 15–17)
- Priced at `results/r11_pricing_2026.csv`
- Needs reprice after R10 actuals load next Monday

### DB State
| Round | Dates | Results |
|-------|-------|---------|
| 0 | Feb 28 | ✅ In DB |
| 1–9 | Mar 5 – May 3 | ✅ In DB |
| 10 | May 7–11 | ⏳ This week |
| 11 | May 15–17 | ⏳ Magic Round |

- `NRL_API_ROUND_OFFSET = 0` — DB rounds now match NRL API exactly (fixed 2026-05-05)
- Venue: `Queensland Country Bank Stadium` (Townsville) — lat/lng present ✅

### Tuesday Automation Pipeline (shifted from Monday 2026-05-11)
| Time | Script | What it does |
|------|--------|--------------|
| 09:00 | `scripts/fetch_nrl_results.py` | Scrapes last round scores, loads to DB |
| 10:00 | BetMate `lib/scraper/nrl_injuries.py` | Scrapes NRL.com casualty ward |
| 17:00 | BetMate `nrl_historical_results.py` | Downloads aussportsbetting xlsx |
| 18:00 | BetMate `nrl_style_stats.py` | Scrapes team style stats |
| 18:05 | BetMate `nrl_round_prep.py` | Fixture + injuries + referees |
| 19:03 | `scripts/prepare_round.py` | Prices upcoming round (T1–T8) |

Historical odds (aussportsbetting) are not ready until Tuesday — this is why pipeline moved to Tuesday.

### How to Run Scripts
```powershell
# Always use the venv:
& C:\Users\ElliotBladen\Apps\BettingEngine\.venv\Scripts\python.exe scripts\prepare_round.py --round 10 --season 2026

# Dry run first:
& .\.venv\Scripts\python.exe scripts\prepare_round.py --round 10 --season 2026 --dry-run
```

### BetMate State (feeds this engine)
- Odds snapshot: every 10 min, Task Scheduler task "BetMate Odds Snapshot 10min" — running ✅
- Injuries output: `BetMate/data/nrl/injuries/processed/latest-injuries.json`
- Style stats output: `BetMate/data/nrl/style-stats/processed/latest-style-stats.csv`

---

## HANDOVER RULE
Write a diary entry to `handover/sessions/YYYY-MM-DD_description.md` at the end of EVERY session.
No exceptions. This is how context survives between conversations.

---

## PROJECT ARCHITECTURE

This is a sports pricing engine for NRL pre-match markets (V1).
Decision-support only — human approves all bets. Not autonomous.

### 7-Tier Pricing Model
| Tier | Layer | What it does |
|------|-------|--------------|
| T1 | Baseline | ELO, team strength, attack/defence, home advantage, recent form |
| T2 | Style matchup | Team style interactions, coach H2H, team-vs-team EV history |
| T3 | Momentum | Bye, turnaround, off big win/loss, bounce-back angles |
| T4 | Venue | Fortress venues, home/away strength, travel effects |
| T5 | Injuries | Key player outs, spine disruption, replacement quality |
| T6 | Referees | Penalty tendency, set restarts, scoring environment |
| T7 | Environment | Weather, lunar phase (experimental, bounded, never dominant) |

### Pricing Spine
Model estimates home/away expected points → derives margin + total → applies T2–T7 adjustments → derives H2H probabilities → compares to bookmaker market → calculates EV + Kelly stake.

### Key Scripts
| Script | Purpose |
|--------|---------|
| `scripts/prepare_round.py` | Main pricing pipeline (runs all tiers) |
| `scripts/fetch_nrl_results.py` | Automated results scraper (Monday 9AM) |
| `scripts/load_results.py` | Loads results CSV into DB |
| `scripts/load_injury_round.py` | Loads injury JSON into DB |
| `pricing/tier*.py` | Individual tier logic |
| `scripts/matrix_confluence.py` | T9 confluence analyser — flags games with 3+ matrix edges ≥20% pointing same direction |

### T9 Matrix Confluence Analyser
```powershell
cd C:\Users\ElliotBladen\Apps\BettingEngine
$env:PYTHONUTF8="1"; $env:BETMATE_ROOT="C:\Users\ElliotBladen\Apps"
& ".\.venv\Scripts\python.exe" scripts\matrix_confluence.py --season 2026 --round 13

# With Supabase push:
& ".\.venv\Scripts\python.exe" scripts\matrix_confluence.py --season 2026 --round 13 --push

# Adjust thresholds:
& ".\.venv\Scripts\python.exe" scripts\matrix_confluence.py --season 2026 --round 13 --min-edges 2 --min-edge-pct 15
```
Reads all 3 matrices (NRL H2H xlsx, totals xlsx, handicap CSV). For each game applies contextual rows: generic home/away, night/day, day of week, rest category (short/normal/long), after win/loss, vs-opponent, venue. Normalises directions per team role. Flags ⚡ where 3+ edges ≥20% align. **Decision-support only — not wired into pricing yet.** End-of-2026 review will quantify how much T9 is worth pricing in.

### DB Tables (key)
`teams`, `venues`, `referees`, `matches`, `results`, `team_stats`, `market_snapshots`, `model_runs`, `model_adjustments`, `signals`, `bets`, `bankroll_log`

---

## DECISION RULES

### EV Formula
```
model_probability = 1 / model_odds
EV = (model_probability * market_odds) - 1
```
Signal eligible only if: EV >= 20%, no hard veto, data quality acceptable.

### Kelly
Quarter Kelly in Year 1. Hard stake cap. Minimum actionable threshold.

### Tier Coverage Reporting — MANDATORY (established 2026-07-07)
Every time a round is priced (NRL or AFL), the output must state which tiers actually fired with real data and which were skipped/defaulted, and why. Never just hand over prices without this — a tier silently defaulting to neutral (e.g. injuries not scraped, weather not fetched, emotional flags stale) changes what the price is worth, and that has to be visible every time, not just when something notable happens to go wrong. Minimum bar: at least 75% of the tiers in scope for that sport must be genuinely populated (real data, not a default/neutral fallback) before the pricing is considered fit to hand over — if it falls short, say so plainly and fix the gap before delivering rather than quietly shipping a thin price.

---

## CODING STANDARDS
- Python first, small functions, explicit names, no magic numbers
- Config files for thresholds/toggles (EV threshold, Kelly fraction, stake caps, moon factor toggle)
- Append-only for snapshots and model outputs — never overwrite history
- Every model run has a `model_version`, every signal links to a run, every bet links to a signal

---

## CLV REPORTING — MANUAL STEPS

### Bet Recording (`data/bets/actual_bets_2026.csv`)
Bets are entered manually after placing. Key gotcha:

**Round labeling — NRL rounds start on THURSDAY.**
Thursday night game = first game of the NEW round. Do not label it as the previous round.
- Example: May 7 (Thu) Dolphins v Canterbury = **R11**, not R10.
- Mislabeled bets won't appear in that round's CLV report (script filters by round number).
- If bets were entered wrong, fix the `round` column before running the CLV report.

**AFL rounds** follow the same rule — check the fixture to confirm the round number.

### Historical Data Lag (AusSportsBetting)
CLV reports require results from `aussportsbetting.com`. Their file typically lags **several days to a week** after the round completes.

| Sport | Download script | Typical lag |
|-------|----------------|-------------|
| NRL | `nrl_historical_results.py` (BetMate) | 2–4 days post-round |
| AFL | `fetch_aussportsbetting_nrl.py --page-url afl` (BettingEngine) | 3–7 days post-round |

Do not run CLV reports until the historical file contains that round's results — the report will silently produce wrong output if results are missing.

### Running CLV Reports Manually
```powershell
# NRL
& .\.venv\Scripts\python.exe scripts\nrl_weekly_clv_report.py --season 2026 --round 11
& .\.venv\Scripts\python.exe scripts\nrl_weekly_ml_clv_report.py --season 2026 --round 11

# AFL
& .\.venv\Scripts\python.exe scripts\afl_weekly_ml_clv_report.py --season 2026 --round 9

# Rolling summary (all sports)
& .\.venv\Scripts\python.exe scripts\rolling_clv_summary.py --sport ALL
```
Use `--round 0` to auto-detect latest round.

### Post-CLV Scripts (run after weekly CLV files are filed)
```powershell
# Update CLV running totals (NRL + AFL)
& C:\Users\ElliotBladen\.local\bin\uv.exe run python scripts\update_clv_running.py

# Update model accuracy vs market (adds new round to running file)
& C:\Users\ElliotBladen\.local\bin\uv.exe run python scripts\generate_model_accuracy.py

# After new pricing round — convert any txt outputs + copy to data/pricing/
# (First add the new round to SOURCES list in the script)
& C:\Users\ElliotBladen\.local\bin\uv.exe run python scripts\convert_pricing_files.py
```

---

## BACKLOG (medium-term)

| Item | Trigger | Notes |
|------|---------|-------|
| Build MCP server | AFL automation stable + signals pipeline built | Full architecture in `handover/MCP_PREP.md`. Read-only query layer for Baz. Sport-parameterised from day 1. ~1 day to build once prereqs are met. |
| Wire signals pipeline | Next week (after AFL build) | Triple-confluence rule (Option A): all 3 matrices ≥20% → gold, 10-20% → silver. ML discrepancy = yellow flag not veto. Pinnacle for EV calc, best AU bookie for stake. |
| Fix migration 009 | Before AFL build | `009_injury_unique_constraint.sql` blocks migration runner. Fix before running new migrations. |
| AFL results scraper | Next AFL session | `fetch_afl_results.py` — runs Tuesday 09:00 (not Monday; AFL rounds end Sunday, injury list updates Tuesday) |
| AFL injury scraper | Next AFL session | BetMate `afl_injuries.py` — scrapes AFL.com.au `/matches/injury-list`, Tuesday 10:00 |
| AFL Tuesday pipeline | After scrapers built | Tue 09:00 results → 10:00 injuries → 17:00 historical → 19:30 prepare_round. See `handover/AFL_PREP.md` |
| Referee scraper automation | Post-R10 | Currently manual CSV |
| **T10 Origin window doesn't cover the round it matters most for** | Found 2026-07-07, R19 | `find_active_origin_game` uses `camp_start <= match_date < camp_end`. `camp_end` is set to the day after the Origin game (e.g. G3: camp_end `2026-07-09`), so it correctly covers the camp week itself — but the very next NRL round (R19, games `2026-07-10` to `2026-07-12`) falls just outside the window, even though that's exactly when Origin players are back at their clubs carrying real fatigue on a 2-4 day turnaround. T10 silently returns 0.0 for the whole round in this case. **Calibration (user-confirmed 2026-07-07): players who backed up the week after Origin play at ~66% capacity — i.e. a 0.34× multiplier on the standard `_ORIGIN_PTS` absence values, not the full 1.0× (fully absent) or a naive 0.5× guess.** Manually overlaid this for R19. Real fix: extend `camp_end` to cover the following round with this 0.34× decay built in, or add a distinct "post-Origin fatigue" mode to `tier10_origin.py` rather than reusing the absence formula unmodified. |

---

## PRODUCT PHILOSOPHY
- Correctness over cleverness
- Explainability over opacity — every number must be reproducible
- Human stays in control — V1 recommends and logs, does not bet autonomously
- Do not introduce black-box ML as the core engine
- Do not build for AFL/EPL/racing yet — finish NRL V1 first
