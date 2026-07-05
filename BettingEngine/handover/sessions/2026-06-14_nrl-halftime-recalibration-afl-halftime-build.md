# Session 2026-06-14: NRL Halftime Recalibration + AFL Halftime Build

## What Was Completed

### AFL Halftime Pipeline — Full Build
Three new scripts created this session:

**`scripts/fetch_afl_ht_scores.py`**
- Scrapes afltables.com Q1-Q4 scores for 2022-2026
- Parses `<table>` blocks with exactly 2 `<tr>` rows each containing `<tt>` cumulative score cells
- Q2 score = halftime score
- Result: 969 games scraped, 875/885 matched (98.9%) to halftime dataset
- 10 misses are pre-season/anomaly games — acceptable
- Key date fix: mixed `DD/MM/YYYY` (2022-25) and ISO format (2026) required per-format parsing
- Dataset updated at `data/inplay/afl/halftime/processed/halftime_dataset.csv`

**`scripts/afl_ht_h2h_matrix.py`**
- AFL halftime H2H matrix, same structure as NRL version
- 18 team sheets, 884 games
- Sections: OVERALL, HALFTIME SCORE POSITION (purple), DAY OF WEEK, FORM, REST, MOON PHASE, BY MONTH, H2H vs OPPONENT
- Output: `outputs/afl_ht_h2h_matrix.xlsx`

**`scripts/afl_ht_live.py`**
- Polls Squiggle API every 30s for `complete=50` or "Half Time" in timestr
- Extracts goals/behinds, calculates pts (goals×6 + behinds)
- Saves JSON → `data/afl/halfTime/R{nn}/`
- Auto-fires `halfTime_price_afl.py`

**`scripts/halfTime_price_afl.py`** (already existed from prior session)
- AFL Bayesian halftime model: REGRESSION_FACTOR=0.45, BASELINE_ACCURACY=0.52
- Loads pregame from `results/r*_afl_2026.csv`

### NRL Halftime Model Recalibration

**Bug fixed (prior session, confirmed):** Sign convention in `halfTime_price_nrl.py`
- `fair_hcap_line = -10.4` = home winning by 10.4 (betting convention)
- Was being read directly as pg_hcap, causing both Bayesian terms to pull toward away
- Fix: `pg_hcap = -_safe_float(pregame.get("fair_hcap_line", 0))`

**Constants updated (prior session):**
```python
REGRESSION_FACTOR = 0.55        # Swartz et al. 2022: 50-60% pre-game at HT
AVG_SECOND_HALF_TOTAL = 23.5    # raised from 22.5
POINTS_PER_ERROR_DIFF = 1.4     # raised from 1.2; 77.5% win rate for fewer-error team
RESTART_NET_PTS = 0.72          # NEW: Rugby League Eye Test May 2026 (1.24 vs 0.52 per set)
RESTART_H2_DEFLATION = 0.36     # NEW: H2 has 39% of H1 restart frequency; 36% won't repeat
CONVERSION_ADJ_CAP = 2.0        # NEW: cap noise from small kick samples
```

**Calculation code updated (this session):**
- `restart_advantage = (home_restarts - away_restarts) * RESTART_NET_PTS * RESTART_H2_DEFLATION`
  - Was: `* 4.5 * 0.80` (3.6 pts per restart diff)
  - Now: `* 0.72 * 0.36` (0.26 pts per restart diff) — research-backed, much more conservative
- `conversion_adj = max(-CONVERSION_ADJ_CAP, min(CONVERSION_ADJ_CAP, conversion_adj))` added

**Validation run (Warriors 6 vs Sharks 8 — R15 2026):**
- Error adj: -5.6 (Sharks had 4 fewer errors in H1)
- Conversion adj: +2.0 (capped — Warriors missed conversions)
- Restart adj: +0.3 (Warriors received slightly more restarts)
- Result: Warriors 62% win probability, fair H2H 1.61/3.58
- Actual result: Sharks 10-8 (user bet Sharks +4.5 at 1.9 pre-HT — correct fade of Warriors)

### Research Findings Used
- **Set restarts:** 61% H1 / 39% H2 split (structural); H2 rate = 64% of H1 rate
- **Restart net pts:** 1.24 vs 0.52 per normal set = 0.72 net (Rugby League Eye Test, May 2026)
- **Error weight:** Each error ~1.4 pts; teams with fewer errors win 77.5% (Eye Test 2025)
- **Regression factor:** Swartz et al. 2022 (Annals of Applied Statistics) supports 50-60% pre-game at HT
- **Conversion:** Near-independent per kick; 75% NRL baseline rate well-supported; cap at 2.0 pts

### Bookmaker Research — AFL In-Play
- **Online in-play betting is illegal in Australia** (Interactive Gambling Act 2001)
- Exemption: Betfair exchange (parimutuel pool carve-out)
- Betfair runs a halftime line pool for AFL (Tote-style, not fixed odds)
- No fixed-odds in-play operator takes AFL HT line bets legally
- Offshore option (e.g., Pinnacle via VPN) — legally grey, KYC/payout risk
- Bet365/Neds/TAB restrict sharp winners quickly

## Files Changed
- `scripts/halfTime_price_nrl.py` — restart calculation + conversion cap updated
- `scripts/fetch_afl_ht_scores.py` — NEW (afltables.com scraper)
- `scripts/afl_ht_h2h_matrix.py` — NEW (AFL HT matrix)
- `scripts/afl_ht_live.py` — NEW (live Squiggle scraper)
- `scripts/halfTime_price_afl.py` — NEW (AFL HT pricing model)
- `data/inplay/afl/halftime/processed/halftime_dataset.csv` — 875 games with HT scores

## Next Session
- Validate AFL halftime model against historical dataset (build backtest)
- Consider wet surface adjustment flag for AFL model (user asked: +10-18 pts H2 uplift when pitch dries)
- NRL R14 refs still not loaded — re-run `run_nrl_pricing.ps1` after Wednesday refs scrape
- NRL R14 T7 emotional stale — run `uv run python scrapers/nrl_emotional.py --round 14` first
- Update CLV running totals if R12/R13 historical data is now available on aussportsbetting
