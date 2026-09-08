# Finals emotional tier, football CLV/ROI, historical-odds refresh

Date: 2026-09-08 (Mac, home machine)

## 1. Historical odds refreshed

- **AFL** workbook now through **2026-09-05**, **NRL** through **2026-09-06**
  (AusSportsBetting). **NFL** fetched and byte-identical to the 21 Aug copy —
  correct, the 2026 season opens 2026-09-09.
- `scripts/fetch_aussportsbetting_nrl.py` archive stem now detects `nfl` too.
- **EPL 4,590 / Championship 6,684 rows, both through 2026-09-06.** Both leagues
  played last weekend (EPL GW3 4-6 Sep; Championship midweek 1-2 Sep + 5-6 Sep).
- **football-data.co.uk root cause:** the `www` vhost was returning nginx 503 for
  hours while the **bare domain served 200**. `fetch_results.py` only knew `www`,
  fell through to the Internet Archive and silently merged a stale 10-row
  snapshot. Fixed: both hosts tried before the archive, archive use is announced,
  and a live-merge returning fewer rows than held now warns.

## 2. NRL/AFL finals — emotional tier added

`scripts/price_finals_emotional_2026.py` calls the production tier functions
(`config/tiers.yaml :: tier7_emotional`, `AFL_T6_CONFIG`). Nothing hand-calculated.

- **AFL T6 was never priced** for the semis (6 Sep report said "left neutral").
- **NRL T7 had two invalid flags**: Cowboys `shame_blowout` (lost by 20, threshold
  is 30+) and Souths `star_return` for Latrell (he returned in R27). Both removed.
  Roosters `shame_blowout` stands — a 30-point loss exactly on the threshold.
- `must_win` applied to sudden-death games only; symmetric, so margins are
  unchanged and only totals move. **This is a reading, not a documented rule** —
  the config says "finals-*positioning*". Ratify or veto.
- Net: Sharks −12.0 → **−13.0**, Souths −10.7 → **−9.2**, both AFL totals **+1.0**.
- Saved in the canonical schema with `actual_*`/`*_error` blank, ready to score:
  `data/pricing/nrl/NRL_PRICING_R28_2026-09-08_finals_wk1.csv`,
  `data/pricing/afl/AFL_PRICING_R26_2026-09-08_semi_finals.csv`.

## 3. Football — bets graded, model vs market, season ledger

- **GW3/GW5 saved bets:** 12 selections, 3W-9L, −7.23u, **ROI −57.84%**, but
  **CLV +8.57%** (beat close 8/12) and **vs open +6.85%** (beat open 9/12).
- **Full-round model vs market (22 matches):** EPL 1X2 RPS 0.1503 vs close 0.1508
  (parity, beat close 6/10) and **O/U clearly better than the market**. EFL lost
  on every metric (RPS 0.2286 vs 0.1915, beat close 3/12).
- **Correction:** the "model under-weights draws / Championship rho" theory I
  raised from the bet sample is **not supported**. EPL GW3 ran 6 draws in 10 and
  the market's mean draw probability (0.243) matched the model's (0.235); in the
  Championship the model carried a *higher* draw probability than the market
  (0.284 vs 0.261). Variance, not calibration.
- **Season ledger (21 placed bets, through 9-06):** EPL 13 bets −4.41u ROI −33.92%
  CLV +7.78%; **EFL 8 bets, 0 wins, −8.50u ROI −100%**, CLV +6.67% but almost
  entirely one price. EPL and EFL should be treated as two different-quality
  models, not one engine having a bad run.

## 4. Research page live

R27 + AFL Finals Week 2 results posted to all three tabs at betmate.au/research
(0.5u flat). NRL running total → +2.14u, AFL → +0.26u, Sports Betting → +26.35u.
Also fixed `app/racing/map/page.tsx`, which had a hard import on a gitignored
JSON and had been **failing every Vercel deploy since `d4bd586`**.

## Open items

- **Odds API still `DEACTIVATED_KEY`** — no market data for NRL/AFL, so finals
  pricing is model-only and there is no EV/CLV path for those codes.
- **`data/nrl/origin/2026.json` missing on this machine** — blocks the
  `update_clv_running.py` rebuild (NRL/AFL running CLV still ends R15/R14).
- **RacingEngine DB is a week stale here** — no `v3_run_performances`, results end
  2026-08-29. Code travelled, data did not (gitignored, seed is from 27 Aug).
- **`price_efl_week4_2026.py` prints instead of saving.** The GW5 model-vs-market
  had to use a reconstruction. Make it write JSON like the EPL pricer does.
- The 23-bet "previous weekend" in the 2026-08-31 combined report has no
  underlying graded file; excluded from the season ledger.
- AFL/NRL gameweek labelling is inconsistent for one Championship round
  (`gw4_10pct_ev_candidates` and `gw5_bets` are the same fixtures).
