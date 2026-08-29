# Championship Player Shadow — GW1 Build + Cross-League Backfill + Double-Count Fix

Date: 2026-08-16

## What happened

### 1. Player shadow v2 built end-to-end

v1 (sparse player-ID features via DictVectorizer) had failed — no signal, -0.0005 MAE degradation. Replaced with v2: position-grouped rolling per-90 stats.

**Approach:** For each match, aggregate per-player rolling averages (goals, assists, shots, SOT, saves per 90 + minutes) by position group (GK/DEF/MID/ATT) for home and away sides. 56 features total. Ridge regression (alpha=50.0) predicts residual (actual goals - base lambda), capped at +/-0.12 goals.

**Files created/modified:**
- `ml/football/player_layer/backfill_espn_player_stats.py` — added `--league` flag (championship/epl/league1), separate cache dirs and output filenames per league
- `ml/football/player_layer/train_starter_shadow.py` — full rewrite from v1 to v2 (position-grouped rolling features). Fixed 18 missing team name aliases. Cross-league rolling features wired in. Now trains on post-tier lambdas.
- `scripts/compare_championship_player_shadow.py` — GW1 base vs player-shadow comparison script

**Data backfilled (ESPN public API):**
- Championship: 2023 (18,452 rows / 463 matches), 2024 (19,830 / 496), 2025 (20,673 / 517)
- EPL: 2024 (14,588 / 365), 2025 (14,549 / 364)
- League One: 2024 (16,067 / 447), 2025 (18,531 / 515)
- 968 Championship match feed JSONs cached in `match_feeds/`
- EPL feeds in `match_feeds_epl/`, League One in `match_feeds_league1/`

### 2. Cross-league carry-forward data

**Problem found:** Teams promoted/relegated into Championship had zero player carry-forward data.

**Fix:** `backfill_espn_player_stats.py` now accepts `--league epl|league1|championship`. Both the training script and comparison script include cross-league files. Player pool: 1,635 → 3,199.

| Team | Before | After |
|------|--------|-------|
| Lincoln | 2/11 | 11/11 |
| Bolton | 2/11 | 9/11 |
| Wolves | 1/11 | 11/11 |

### 3. Double-counting fix

**Problem found:** Shadow was trained on pre-tier lambdas (raw D-C from `backtest_results.csv`) but applied to post-tier lambdas (from `price_match()` which includes T3/T5/T6/T7/T8). Baseline mismatch = double-counting risk.

**Fix:** Ran backtest with `--apply-tiers` to produce `backtest_results_tiers.csv`. Updated `train_starter_shadow.py` to use tier-adjusted lambdas as baseline (auto-detects `backtest_results_tiers.csv`, falls back to base if absent). Shadow now learns residuals AFTER tiers are applied — adding its delta to `price_match()` output is clean.

**Impact:** Shadow improvement jumped from +0.0015 MAE (pre-tier baseline) to **+0.0162 MAE** (post-tier baseline). 10x more signal — the shadow finds real value in what the tiers leave behind.

**Residual T5 note:** T5 injuries are always 0 in the backtest (no historical injury data), so the shadow was trained where T5 never fired. In production when injuries ARE passed to `price_match()`, there's a small T5/shadow overlap. Contained by the ±0.12 cap. Will reassess if shadow goes live.

### 4. Tier overlap research

Investigated whether the shadow should replace any tiers:

| Tier | Overlap with shadow | Verdict |
|------|:-------------------:|---------|
| T2 PPDA | None (inactive in Championship) | Keep |
| T3 Form/Rest | Partial — rolling player stats encode form | Keep |
| T5 Injuries | Medium — player counts proxy for absences | Keep |
| T6 Refs | Zero — shadow has no ref data | Keep |
| T7 Set-pieces | Zero — shadow has no corner data | Keep |
| T8 New-team | Minimal | Keep |
| T9 Manager | Zero | Keep |

**Decision: keep all tiers as-is. Shadow runs as paper-trade diagnostic only.** Do not replace or modify the tier stack. After a full season of CLV data, reassess whether to adopt the shadow for live pricing.

### 5. GW1 results (9 of 11 matches — 2 not yet played)

Four-way log loss comparison:

| | Open Mkt | Close Mkt | Base Engine | Player Shadow |
|--|:--------:|:---------:|:-----------:|:-------------:|
| Avg LL | **1.078** | 1.088 | 1.100 | 1.094 |
| Games won | 3/9 | 1/9 | 2/9 | 3/9 |

Shadow beats base. Both behind market on this tiny sample.

**Per-game detail:**

| Match | Score | Open | Close | Base | Shadow | Best |
|-------|:-----:|:----:|:-----:|:----:|:------:|:----:|
| Sheff Utd v Birmingham | 0-0 | 1.250 | 1.256 | 1.632 | 1.598 | OPEN |
| Stoke v Swansea | 1-2 | 1.122 | 1.162 | 1.016 | 1.038 | BASE |
| Portsmouth v QPR | 1-3 | 1.196 | 1.166 | 1.332 | 1.375 | CLOSE |
| Norwich v West Brom | 1-2 | 1.359 | 1.398 | 1.094 | 0.985 | SHADOW |
| Middlesbrough v Lincoln | 2-1 | 0.350 | 0.398 | 0.630 | 0.630 | OPEN |
| Charlton v Derby | 2-1 | 1.014 | 1.046 | 1.192 | 1.235 | OPEN |
| Bristol City v Millwall | 0-2 | 1.096 | 1.050 | 0.871 | 0.912 | BASE |
| Bolton v Preston | 2-1 | 0.848 | 0.851 | 0.779 | 0.772 | SHADOW |
| Wolves v Blackburn | 2-2 | 1.463 | 1.466 | 1.352 | 1.299 | SHADOW |

Output: `outputs/football/championship/gw1_player_shadow_comparison.json`

## What still needs doing

1. **Re-fetch Burnley/West Ham and Watford/Southampton match feeds** — games were STATUS_SCHEDULED on Aug 16. Re-fetch after completion:
   ```bash
   PYTHONPATH=. python3 scripts/compare_championship_player_shadow.py
   ```

2. **Weekly shadow tracking** — run comparison script each GW, accumulate CLV data. After the full season, compare shadow CLV vs base CLV to decide whether to adopt.

3. **GW2+ workflow** — after team sheets are announced, re-fetch match feeds for the new round, then run the comparison. The `compare_championship_player_shadow.py` script is the template.

## RacingEngine scope decision (same session, earlier)

User corrected the V2 build order — Class/Race Strength comes first, not campaign stage/track bias. User explicitly restricted Claude's role on RacingEngine to data processing, evaluation/logging, and pipeline plumbing only. Core rating architecture is user-built. See `handover/sessions/2026-08-16_v2-build-spec-and-scope-decision.md` and memory file `feedback_racing_engine_scope.md`.
