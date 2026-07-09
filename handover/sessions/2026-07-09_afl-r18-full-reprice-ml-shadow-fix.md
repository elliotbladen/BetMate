# 2026-07-09 — AFL R18 full re-price (all tiers) + ML shadow deploy fix

## What was asked
"Price up fully all tiers AFL. All tiers. Make sure if you can't price anything you tell me."

## What was delivered
AFL R18 (Jul 9–12, 9 games) fully priced with **all 9 tiers in scope populated with real data** — T1–T7 rules, ML shadow, T9 matrix confluence. Supersedes the Jul 7 start-of-week run.

- Writeup: `BettingEngine/outputs/results/r18_afl_pricing_2026.md`
- CSV: `BettingEngine/results/r18_afl_2026.csv` (9 rows, DB `afl_shadow_predictions` updated)
- T9 JSON: `BettingEngine/outputs/afl_t9_confluence_latest.json`
- Predictions pushed live to betmate.au (Supabase + endpoint check OK — the Thu 09:00 task had fired before the R18 CSV existed, so it had pushed R17; re-ran manually)

## The one thing that could NOT be priced
**Market comparison — EV, edges, bet selection.** The Odds API key returns **401 Unauthorized**; snapshots stopped 2026-07-03 (last file `data/odds_snapshots/2026/2026-07-03.csv`). Fair prices are complete but there is nothing to compare them to. **Fix the key first next session**, run a snapshot, then re-assess R18 vs market (especially Fremantle -28.5 vs the 6-way Swans matrix, and the two H2H-disagreement games).

## Bugs found & fixed

### 1. ML shadow silently broken since the Jul 5 retrain (the big one)
The Jul 8 pkl regeneration produced split-feature models (margin/total: 38 cols incl. 8 EMA features + `mkt_home_prob_open`; H2H: 30 cols) but `prepare_afl_round.py` still built the old 29-col feature row. `load_models()`/`compute_ml_bias()` threw, the except swallowed the error, and the shadow section was skipped with a vague one-liner. R18's Jul 7 pricing ran on the OLD pkls so nobody noticed.

**Fix (all in `scripts/prepare_afl_round.py`):**
- `FEATURE_COLS_REG` (38) + `FEATURE_COLS_H2H` (30) — verified to match `feature_names_in_` on both pkls exactly.
- `get_ema_form()` — deploy-time EMA replication of `ml/afl/game_log.py` (8-game window, 0.75 decay, opposition-adjusted margin × opp_pre-game_ELO/1500).
- `load_market_h2h_probs()` — vig-free home prob from the latest odds snapshot feeds `mkt_home_prob_open`; games not found fall back to `elo_win_prob` (training's NaN fill). With the snapshot stale (R17 games only), all R18 games used the fallback — no wrong data leaked.
- `compute_ml_bias()` rewritten to use the real feature columns from `features_afl.csv` (it carries all 38) instead of the old synthetic reconstruction.
- The swallowing `except` now prints the actual exception.

### 2. T2 style data was 2 months stale
`footywire_snapshots.csv` last had R9 (May 12) — the Jul 7 R18 pricing used it silently ("R18 snapshot" label is misleading: it means "most recent ≤ R18"). Footywire is back up after its Jul 2 outage — scraped a genuine season-to-date-entering-R18 snapshot today (18 teams). NB the scraper's final `print` crashes on cp1252 without `PYTHONUTF8=1` — data still writes.

### 3. Bogus Adelaide emotional flag (T6)
Scraper flagged "personal_tragedy major — Jordan Dawson ruled out after brother's death" for R18. Web-verified: the death was **April 2026**, Dawson has played since, including 27 disposals vs West Coast in R17. Removed via corrected `outputs/afl_round_prep/r18_2026/emotional_r18_2026.json` (prep file takes precedence over `latest-emotional.json`). Crows line -30.6 → -26.9. **Pattern to watch: the emotional scraper recycles old headlines.**

### 4. Brisbane injuries (T5)
From today's Lions Qscan report: Jack Payne confirmed done for 2026 (marked season-ending for carry-forward), Darcy Gardiner (hamstring 4–6 wks) added — missed by the Jul 6 scrape. McCluggage + Zorko return vs Essendon (correctly not in the outs list).

## Key pricing outcomes
- Model picks: Freo -28.5, Coll -20.3, StK -6.8, Geel -18.6 (@GWS), Haw -20.1 (@Carl), Adel -26.9, WB -44.0, Melb -39.0, BL -55.3.
- **Alignment: all 9 games rules+ML agree on the winner** — reverses Jul 7, where the old ML had Sydney over Freo.
- **H2H off-limits (rules vs ML H2H disagree): GWS/Geelong, Carlton/Hawthorn.** Caveat: ML H2H ran with the ELO fallback for the market feature — re-check once odds are back.
- Top signals: Adelaide -26.9 (6-way matrix, rules/ML within 0.4pts), Collingwood (8-way H2H matrix incl. four 100% splits), Melbourne (6-way incl. 100% Tigers-vs-Melb).
- Caution: Fremantle (matrix 6-way against, ML 21pts below rules), Brisbane -55.3 (extreme-ELO overcook + 4-way matrix fade + ML overshooting via Essendon's EMA freefall).

## Guardrails added (same session, after user sign-off) — recurrence prevention

1. **Single source of truth for ML feature lists:** new `ml/afl/features.py` holds `FEATURES_MARGIN_TOTAL` (38) + `FEATURES_H2H` (30); both `ml/afl/train.py` and `scripts/prepare_afl_round.py` import from it. A retrain can no longer drift from deploy.
2. **Hard validation at model load:** `load_models()` now compares each pickle's `feature_names_in_` against the shared lists and raises a descriptive error on mismatch (instead of the old silent skip).
3. **DATA HEALTH preflight + speak-up recap in `prepare_afl_round.py`:** every pricing run now checks and REPORTS — ELO freshness (features vs round date), T2 snapshot round/date staleness, T5 empty/ageing, T6 empty, ML availability, odds snapshot age + per-game market coverage, and T7 weather fetch failures. Warnings print in a block up front and are repeated after the DB store so they can't be scrolled past. Verified live on R18: correctly flagged the two market issues, prices unchanged.
4. **`load_style_snapshot` is honest now:** returns metadata (source, actual round, as_of_date, rounds stale) instead of mislabeling old data as "R{n} snapshot".
5. **Footywire scraper hardened:** auto round label (max games+1, self-correcting against the CSV's previous max), new `as_of_date` column, unicode print crash fixed.
6. **New scheduled task "BetMate AFL Footywire T2 Snapshot" (Tue 16:05)** via `BettingEngine/scripts/run_afl_footywire_snapshot.ps1` — the T2 file was orphaned (nothing fed it; last data May 12). Logs to `BettingEngine/outputs/logs/afl_footywire_snapshot.log`.
7. **Emotional scrapers (AFL + NRL): 10-day recency filter** on Google News items + date-prefixed headlines + explicit prompt instruction to disregard resurfaced old stories — closes the Dawson stale-headline hole.
8. **`_export_afl_prices.py`:** `--round` now auto-detects the latest priced round from the DB (was hardcoded default 13).

## Loose ends for next session
1. **Odds API is down for now (user-confirmed 2026-07-09)** — not a local key problem to fix. Everything market-facing is blocked meanwhile: snapshots, movement tracking, odds board freshness, EV, `mkt_home_prob_open`. When it's back, run `scripts/run_odds_snapshot_cycle.ps1` and confirm snapshots resume.
2. Re-compare R18 fair prices vs market once odds flow again — especially Fremantle -28.5 (matrix conflict) and the two H2H-disagreement games.
3. ~~`_export_afl_prices.py` round default~~ ✅ fixed — auto-detects latest round.
4. ~~Emotional scraper stale-headline problem~~ ✅ fixed — 10-day recency filter, both sports.
5. Not committed yet — run `& scripts\git-sync-end.ps1 "AFL R18 all-tiers re-price + ML shadow deploy fix"` at end of session (two-machine rule).
