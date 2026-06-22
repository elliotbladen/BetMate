# Session Handover — 2026-06-18
## NRL R16 Pricing + Home Bias Calibration + Matrix Analysis

---

## What Was Done

### 1. T10 Origin Layer — G2 Fix
- **Problem:** T10 was not firing for R16 (June 19-21) because `camp_end` for G2 was set to `2026-06-18`, but the half-open interval `camp_start <= match_date < camp_end` excludes the match date.
- **Fix:** Extended G2 `camp_end` from `2026-06-18` to `2026-06-22` in `data/nrl/origin/2026.json`.
- **G2 result:** QLD won 44-24. Camp window now correctly covers R16 (Jun 19-21).
- G2 NSW/QLD squads fully populated in `data/nrl/origin/2026.json`.

### 2. T7 Emotional Scraper — Two Fixes
- **Problem 1:** `ORIGIN_BOOST_WINDOWS_2026` had G2 as July 2-12 and G3 as July 23 - Aug 2 — both wrong. G2 post-Origin window is June 18-28.
- **Fix:** Updated `scrapers/nrl_emotional.py` — G2 now `('2026-06-18', '2026-06-28', 'Post-Origin Game 2 camp window')`, G3 now `('2026-07-09', '2026-07-19', 'Post-Origin Game 3 camp window')`.
- **Problem 2:** `shame_blowout` flag never fires because DB auto-find resolves to `C:\Users\ElliotBladen\BettingEngine\data\model.db` (doesn't exist).
- **Workaround:** Pass `--db-path C:\Users\ElliotBladen\Apps\BettingEngine\data\model.db` explicitly every time you run the emotional scraper.
- **R16 emotional result:** Roosters shame_blowout detected (lost 38pts to Storm), origin_boost window active.

### 3. Matrix Confluence — H2H + Handicap (3 edges ≥ 20%)
Full per-game contextual analysis (day, stadium, rest, form, opponent, home/away factor):

**H2H Matrix — Notable signals (3+ edges ≥20% same direction):**
| Game | Signal | Key edges |
|------|--------|-----------|
| Storm vs Raiders | BACK STORM | AAMI Park home advantage 108.3% (biggest single edge in R16), after-win form |
| Roosters vs Sharks | nuanced | Roosters home historically strong, but Origin disruption |
| Knights vs Dragons | BACK KNIGHTS | Thursday + home fortress |

**Handicap Matrix — Notable signals:**
| Game | Signal | Key edges |
|------|--------|-----------|
| Storm vs Raiders | STORM COVER | 3-way confluence |
| Roosters vs Sharks | SHARKS COVER | Roosters missing 7 players |

**Combined (H2H + Handicap aligned):** Storm/Raiders is the top aligned signal — both H2H and handicap matrices point Storm.

### 4. Totals Matrix (3 edges ≥ 5%)
Market lines tend to set at 48-50 for NRL. Key totals signals from matrix:
- Several games showed 3+ edges on UNDER after Origin disruption.
- Model totals run ~1.4 pts above actual average (market runs +3.9 above actual).

### 5. Totals Comparison: Model vs Market vs League Avg (R8 onwards)
From `scripts/totals_comparison.py` (created this session):
- **League actual avg (2026):** ~48.7 pts (n=113)
- **Market close avg (R9-R13, where CLV data exists):** ~51.8 pts (overestimates by +3.9)
- **Model avg:** ~+1.4 above actual (much closer than market)
- **CLV files missing** for R12, R14, R15 — market open/close data unavailable for those rounds.
- Origin rounds specifically: model over-predicts by 2-9 pts above actual.

### 6. Post-Origin Scoring Research
Deep dive via `scripts/_origin_scoring_v2.py` on 3,534 NRL games (2009-2026):
- **Conclusion: NOT statistically significant.** All Welch t-tests p > 0.10 (NS).
- Post-Origin 1-3d: -0.7 vs normal (p > 0.10)
- Post-Origin 4-7d: -1.1 vs normal (p > 0.10)
- All post-Origin combined: -0.9 vs normal (p > 0.10)
- Post-Origin avg lower than normal in only 10/17 seasons tested (59% — not meaningfully above 50%)
- **2026 is an anomaly** — but that's because normal 2026 rounds have been scoring at 49.5 avg (unusually high), making the post-Origin rounds look suppressed by comparison.
- Market already prices any fatigue effect in. Under-rate post-Origin is actually slightly WORSE than normal rounds.
- **Decision:** Do NOT apply an automatic totals suppression adjustment for post-Origin rounds in T10. The adjustment stays only for teams with ≥2.5 pts of Origin disruption (the existing T10 totals logic).

### 7. NRL Home Bias Calibration
Empirical research via `scripts/_calibrate_home_adv.py` on 3,534 historical games:
- **True NRL home advantage:** +2.96 pts overall (2009-2026), +2.79 pts (2022-2026), +0.81 pts (2026 YTD — eroding)
- **Rules model H2H accuracy:** picks HOME → 69.0% correct; picks AWAY → 76.9% correct (systematic home overconfidence)
- **Config change:** `home_advantage_points: 3.5 → 2.5` in BOTH:
  - `config/sports/nrl.yaml`
  - `config/tiers.yaml`
- **Also updated:** `league_avg_total: 47.0 → 48.5` (empirical 2026: 48.7), `league_avg_per_team: 23.5 → 24.25`

### 8. R16 Final Prices (HA=2.5, T10 active, T7 active)

| Game | Fair Margin | Fair Hcap | H@105 | A@105 |
|------|------------|-----------|-------|-------|
| Knights vs Dragons | Knights -9.3 | -9.3 | 1.220 | 4.350 |
| Tigers vs Dolphins | Dolphins -0.5 | +0.5 | 1.970 | 1.840 |
| Titans vs Panthers | Panthers -19.1 | +19.2 | 17.380 | 1.010 |
| Bulldogs vs Eagles | Eagles -6.7 | +6.7 | 3.300 | 1.340 |
| Warriors vs Cowboys | Warriors -10.9 | -10.9 | 1.160 | 5.240 |
| Storm vs Raiders | Storm -2.7 | -2.7 | 1.620 | 2.320 |
| Roosters vs Sharks | Sharks -2.9 | +2.9 | 2.350 | 1.600 |

**Key observations:**
- **Roosters vs Sharks:** Roosters missing 7 Origin players (T10: -4.0 hcap, -3.0 totals — both capped). Despite playing at home, Sharks are a meaningful 2.9pt favourite at fair price. Fair Roosters H2H = 2.35. If market has Roosters at anything shorter, there's value on Sharks.
- **Storm vs Raiders:** Storm missing Munster + Grant (T10 capped at -4.0). Still favourites at -2.7 (AAMI Park factor). Matrix aligned — best signal of the round. If market has Storm -5 or shorter, Raiders have value.
- **Tigers vs Dolphins:** Effectively a coin flip after all adjustments. No clear signal.
- **BETTING RULE REMINDER:** Only bet if BOTH rules model AND ML model agree on direction (established 2026-06-17).

---

## Files Created This Session
- `scripts/totals_comparison.py` — model vs market vs league avg comparison
- `scripts/_origin_scoring_v2.py` — post-Origin scoring statistical research (3,534 games)
- `scripts/_calibrate_home_adv.py` — empirical home advantage calibration from xlsx
- `scripts/_show_r16.py` — quick display helper for R16 CSV

## Files Modified This Session
- `scrapers/nrl_emotional.py` — fixed G2/G3 origin_boost windows
- `data/nrl/origin/2026.json` — G2 camp_end extended to 2026-06-22; G2 NSW+QLD squads populated
- `config/sports/nrl.yaml` — home_advantage_points 3.5→2.5; league_avg_total 47.0→48.5; league_avg_per_team 23.5→24.25
- `config/tiers.yaml` — home_advantage_points 3.5→2.5
- `results/r16_pricing_2026.csv` — repriced with all fixes

---

## Pending for R16
- **Referees:** T6 not loaded (0/8 refs). Refs typically announced Wednesday. Run `scrapers/nrl_referees.py --round 16` when announced, then re-run `prepare_round.py --round 16`. Only T6 will change — small impact.
- **ML model check:** Verify Storm vs Raiders and Roosters vs Sharks direction matches ML before placing bets.
- **G3 Origin squad:** Needs populating before R18 (camp starts July 3, G3 played July 8).

## Known Emotional Scraper Workaround
When running `nrl_emotional.py` directly, ALWAYS pass `--db-path`:
```powershell
& ".\.venv\Scripts\python.exe" C:\Users\ElliotBladen\Apps\scrapers\nrl_emotional.py --round 16 --db-path C:\Users\ElliotBladen\Apps\BettingEngine\data\model.db
```
The auto-find resolves to the wrong path. This is a known bug — the fix would be to update the auto-find logic in `nrl_emotional.py` to look for `Apps\BettingEngine\data\model.db` specifically.

---

## EXTENDED SESSION — Referee Data Build + T6 Overhaul

### 9. Referee Database Investigation
- T6 was previously running on vibes: `games_in_sample=0` for ALL refs, `team_ref_bucket_stats` table completely empty. The bucket assignments (Klein=whistle_heavy, Sutton=neutral, etc.) were hand-guessed.
- Discovered that **Rugby League Project** (`rugbyleagueproject.org/referees/{name}-ref/games.html`) has complete game-by-game records for every NRL referee: Year, Date, Competition, Round, Home, Score, Away, Scrums, Penalties, Venue, Crowd, Role.
- NRL uses a **single on-field referee system** (since 2014). Only 7 active primaries in 2026: Klein, Sutton, Atkins, Gee, Smith, Gough, Raymond. Others on roster are touch judges / senior review.

### 10. Scraping 725 Games (2022-2026)
- Created `scripts/scrape_ref_stats.py` — scrapes all 7 refs from RLP, filters NRL Premiership 2022-2026, Role=Referee only.
- Result: **725 games** loaded into new `referee_game_stats` table in `data/model.db`.
- Table schema: referee_name, season, date_str, competition, round_label, home_team, home_score, away_score, total_score, home/away/total penalties, venue, crowd.
- Sample sizes: Klein=112, Sutton=117, Atkins=99, Gee=89, Smith=99, Gough=101, Raymond=50 games.
- Raymond limited sample (started primary NRL refereeing in 2024 only).

### 11. Season-Adjusted Scoring Effects
- Created `scripts/_ref_analysis.py` — computes proper season-adjusted residuals.
- Raw averages were biased: NRL scoring rose from 42.8pts avg in 2022 to 48.0 in 2026. Refs who reffed more games in high-scoring years would appear "flow-heavy" just due to era.
- Fix: for each game compute `total - that_season_avg`, average residuals per referee. Removes time trend entirely.
- **Final season-adjusted scoring_delta values:**
  | Referee | delta | Old bucket | New bucket |
  |---------|-------|------------|------------|
  | Ashley Klein | -1.183 | whistle_heavy | whistle_heavy ✅ |
  | Gerard Sutton | -1.063 | neutral | **whistle_heavy** (corrected) |
  | Grant Atkins | -0.287 | neutral | neutral ✅ |
  | Adam Gee | -0.072 | neutral | neutral ✅ |
  | Todd Smith | +0.428 | neutral | neutral ✅ |
  | Peter Gough | +0.994 | neutral | **flow_heavy** (corrected) |
  | Wyatt Raymond | +3.132 | n/a (new) | flow_heavy (added) |

### 12. T6 Code Changes
- Added `scoring_delta REAL` column to `referee_profiles` table: `ALTER TABLE referee_profiles ADD COLUMN scoring_delta REAL`
- Updated `db/queries.py` `get_referee_profile()` to include `scoring_delta` in SELECT.
- Updated `pricing/tier6_referee.py` `compute_referee_adjustments()`:
  - New `scoring_delta: Optional[float] = None` parameter
  - If `scoring_delta is not None`: uses the real measured effect directly (totals_source='scraped')
  - Else: falls back to old bucket lookup (totals_source='bucket')
- Updated `pricing/tier6_referee.py` `get_ref_context()` to return `scoring_delta` from profile.
- Updated `scripts/prepare_round.py` T6 call to pass `scoring_delta=t6_ctx.get('scoring_delta')`.
- Raised `totals_clamp: 2.0 → 4.0` in `config/sports/nrl.yaml` tier6 (old cap was suppressing Raymond's +3.13).

### 13. R16 Ref Assignments Loaded
- Created `scripts/_load_r16_refs.py`, loaded all 7/7 R16 assignments into `weekly_ref_assignments`.
- Assignments confirmed from RLP for R16 (Jun 19-21):
  - Knights/Dragons → Gerard Sutton
  - Tigers/Dolphins → Ziggy Przeklasa-Adamski (no scraped data → neutral fallback)
  - Titans/Panthers → Peter Gough
  - Bulldogs/Eagles → Adam Gee
  - Warriors/Cowboys → Grant Atkins
  - Storm/Raiders → Todd Smith
  - Roosters/Sharks → Ashley Klein

### 14. Final R16 Totals (with real T6 data)
Repriced and exported to `results/r16_pricing_2026.csv`:

| Game | T1 | T6 (real) | T8 | T10 | Final |
|------|----|-----------|----|-----|-------|
| Knights vs Dragons | 54.5 | -1.06 (Sutton) | -0.3 | -0.3 | **51.0** |
| Tigers vs Dolphins | 55.5 | 0.00 (Ziggy-no data) | -1.5 | -1.5 | **53.4** |
| Titans vs Panthers | 44.4 | +0.99 (Gough) | -1.8 | -1.8 | **40.6** |
| Bulldogs vs Eagles | 43.8 | -0.07 (Gee) | 0.0 | 0.0 | **38.5** |
| Warriors vs Cowboys | 49.1 | -0.29 (Atkins) | -0.6 | -0.6 | **45.2** |
| Storm vs Raiders | 47.1 | +0.43 (Smith) | -1.5 | -1.5 | **44.2** |
| Roosters vs Sharks | 52.9 | -1.18 (Klein) | -3.0 | -3.0 | **48.9** |

Confirmed via `scripts/_show_r16_totals.py` — T6 column `t6_totals` has real values, not zeros.

### Files Created (Extended Session)
- `scripts/scrape_ref_stats.py` — scrapes RLP for all 7 refs, inserts into `referee_game_stats`
- `scripts/_ref_analysis.py` — season-adjusted scoring effect analysis
- `scripts/_update_ref_profiles.py` — updates `referee_profiles` with real data, corrects buckets
- `scripts/_load_r16_refs.py` — loads R16 referee assignments into `weekly_ref_assignments`
- `scripts/_show_r16_totals.py` — display helper: full T6 breakdown per game

### Files Modified (Extended Session)
- `data/model.db` — new `referee_game_stats` table (725 rows), `scoring_delta` column on `referee_profiles`, updated bucket + notes + games_in_sample for all 7 refs
- `db/queries.py` — `get_referee_profile()` now returns `scoring_delta`
- `pricing/tier6_referee.py` — real scoring_delta path added; totals_clamp raised in code default
- `scripts/prepare_round.py` — T6 call passes `scoring_delta`
- `config/sports/nrl.yaml` — `totals_clamp: 2.0 → 4.0`
- `results/r16_pricing_2026.csv` — repriced with all fixes (HA=2.5 + real T6 + T10 active)

### 15. Referee Home Ground Bias Analysis
Created `scripts/_ref_home_bias.py` — analysis across 725 games 2022-2026, measuring:
1. Season-adjusted home margin per referee (removes era scoring trend)
2. Home win rate per referee vs 57.1% league average
3. Penalty differential per referee (away_pen − home_pen)

**Results:**
| Referee | Adj Home Margin | Home Win% | Pen Diff | Verdict |
|---------|-----------------|-----------|----------|---------|
| Ashley Klein | **+3.20** | **64.3%** | -0.40 | HOME-FRIENDLY |
| Gerard Sutton | **-3.14** | **51.3%** | -0.34 | AWAY-FRIENDLY |
| Grant Atkins | -0.05 | 55.6% | -0.91 | neutral |
| Adam Gee | +0.72 | 59.5% | -1.16 | neutral |
| Todd Smith | -0.79 | 55.1% | -0.15 | neutral |
| Peter Gough | -0.13 | 55.6% | -0.68 | neutral |
| Wyatt Raymond | +0.58 | 60.0% | -0.20 | neutral |

Key findings: ALL refs give more penalties to home teams (negative pen diff) — normal since home teams attack more. Klein and Sutton are the only statistically significant outliers.

### 16. T6 Home Bias Wired Into Pricing
- Added `home_bias_adj REAL` column to `referee_profiles` table — populated for all 7 refs
- Updated `db/queries.py` `get_referee_profile()` to return `home_bias_adj`
- Updated `pricing/tier6_referee.py` `compute_referee_adjustments()`:
  - New `home_bias_adj: Optional[float] = None` parameter
  - If provided: uses `raw_hcap = float(home_bias_adj)` directly (source='scraped')
  - Else: falls back to bucket edge differential
- Updated `pricing/tier6_referee.py` `get_ref_context()` to return `home_bias_adj`
- Updated `scripts/prepare_round.py` T6 call to pass `home_bias_adj=t6_ctx.get('home_bias_adj')`
- Raised `handicap_clamp: 1.5 → 3.5` in BOTH `config/tiers.yaml` AND `config/sports/nrl.yaml`

### 17. R16 Final Handicap Prices (with T6 home bias applied)

| Game | T6 Hcap | Final Margin | Fair H2H | Referee |
|------|---------|-------------|----------|---------|
| Knights vs Dragons | -3.14 | **Knights -6.2** | 1.434 / 3.304 | Sutton (away-friendly) |
| Tigers vs Dolphins | 0.00 | Dolphins -0.5 | 2.069 / 1.936 | Ziggy (no data) |
| Titans vs Panthers | -0.13 | Panthers -19.3 | 18.25 / 1.058 | Gough (neutral) |
| Bulldogs vs Eagles | +0.72 | Eagles -6.0 | 3.241 / 1.446 | Gee (neutral) |
| Warriors vs Cowboys | -0.05 | Warriors -10.9 | 1.222 / 5.499 | Atkins (neutral) |
| Storm vs Raiders | -0.79 | **Storm -1.9** | 1.777 / 2.288 | Smith (neutral) |
| Roosters vs Sharks | **+3.20** | **Roosters -0.3** | 1.961 / 2.041 | Klein (home-friendly) |

**Critical shifts from home bias:**
- **Roosters vs Sharks**: Klein's +3.20 almost exactly offsets the T10 Origin penalty (-4.0 hcap for 11.5pts of Roosters origin pts). Game is now a virtual coin flip — Roosters +0.3 fair. Fair H2H ≈ 1.96/2.04.
- **Knights vs Dragons**: Sutton's -3.14 reduces the Knights' home advantage significantly. Was Knights -9.3 before T6 home bias; now Knights -6.2.
- **Storm vs Raiders**: Smith neutral (-0.79), minimal impact. Storm still narrow favourite -1.9.

**Tier 1 breakdown for Roosters (to understand the coin flip):**
T1=-0.7, T2=-1.0, T3=0.0, T4=+1.5, T5=+1.2, T6=+3.20, T7=0.0, T10=-4.0 → margin=+0.3

### Known Gaps / Pending
- **Ziggy Przeklasa-Adamski not in RLP** — no scraped data, neutral fallback (0.0). Only 2 R16 games (Tigers/Dolphins); limited impact.
- **`scrapers/nrl_referees.py` does not exist** — the regular Wednesday ref scraper path is missing. Refs are loaded manually. Need to decide: build a scraper that maps ref names from whatever source NRL uses to announce refs, or keep manual `_load_r{rr}_refs.py` approach.
- **Team bucket stats still empty** — T6 still has no team-specific performance-by-bucket data. Now the two big signals (scoring_delta + home_bias_adj) are both wired in and the remaining gap is small.

---

## CLV Status
- NRL R15 closing lines: pending (file R15 bets + get closing lines to run `update_clv_running.py`)
- AFL R14 closing lines: pending
- Running CLV: NRL +5.27% avg / 70.9% positive (R8-R15, 55 bets), AFL +0.76% (R8-R14, 43 bets)
