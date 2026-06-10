# Session Diary — 2026-06-05 — NRL Half-Time Pricing Architecture

## What was done

### Research
Deep research session covering:
1. **MCP Phase 2** — AFL support wired into Baz tool-use loop (injuries, ML data in signals, sport param on get_game_context, chaining rule)
2. **Crypto / Baz token** — researched AI agent token space. Billy Bets is the closest competitor (Virtuals Protocol, Base chain, $1M from Coinbase Ventures). They cover US sports only, use SportsTensor (not proprietary), and are currently at -3.71% ROI. No competitor covers NRL/AFL. No AI agent token has a CLV-verified on-chain track record.
3. **NRL half-time pricing** — full research on methodology, academic papers, NRL-specific stats
4. **Half-time anomaly detection** — ETxP model (r²=0.83 between inside-20 possessions and expected score), error rate regression, set restart inflation, conversion luck

### Architecture built — NRL Half-Time System

**3 new scripts:**

| File | Purpose |
|------|---------|
| `scrapers/nrl_halftime_stats.py` | Collects half-time stats (manual entry + NRL API stub) |
| `BettingEngine/scripts/halfTime_price_nrl.py` | Bayesian pricing update (HT score → updated H2H, hcap, total) |
| `BettingEngine/scripts/halfTime_matrix_nrl.py` | 5-signal anomaly matrix with composite score |
| `scripts/run_halftime_nrl.ps1` | Pipeline wrapper: collect → price → matrix |

**New data directory:**
- `data/nrl/halfTime/R{nn}/` — per-game HT stats JSON
- `data/nrl/halfTime/historical/` — calibration data once 50+ observations collected

**Output:**
- `BettingEngine/outputs/nrl_halftime_matrix_latest.json` — consistent with T9 confluence pattern

---

## The Half-Time Model

### Pricing model (`halfTime_price_nrl.py`)
- **Bayesian update**: `expected_margin = HT_margin × 0.50 + pregame_hcap × 0.50`
- Regression factor = 0.50 (calibrate from historical data once collected)
- Second half total: lookup table based on first-half total (regression to mean)
  - Low 1H (<12 pts) → expect ~24.5 pts in 2H
  - Average 1H (19-24 pts) → expect ~22 pts in 2H
  - High 1H (>30 pts) → expect ~18.5 pts in 2H
- Error adjustment: 1.2 pts per error differential
- Restart inflation: deflate by 80% (second half has only 14% of first-half restart frequency)
- Conversion luck: missed conversions at baseline 75% conversion rate = pts owed
- Monte Carlo simulation: 20,000 runs, Normal(mean, std×1.4) for overdispersion
- Output: HT H2H odds, HT hcap line, HT total line, signal notes

### Anomaly matrix (`halfTime_matrix_nrl.py`)
5 signals with weights:

| Signal | Weight | Threshold | Basis |
|--------|--------|-----------|-------|
| ETxP divergence | 3 | 6+ pts gap | r²=0.83 inside-20 vs expected score |
| Error rate | 2 | 2+ extra errors | 77.5% win rate for lower-error team |
| Restart inflation | 2 | 3+ restart gap | 2H avg 0.5 restarts vs 3.6 in 1H |
| Conversion luck | 1 | 2+ missed conversions | Random, regresses to 75% mean |
| Pre-game contradiction | 1 | 8+ pts divergence | Model vs actual HT margin |

Composite score ≥ 6 → STRONG | 3-5 → MODERATE | 2-3 → WEAK | <2 → NEUTRAL

---

## The NRL API Investigation — OUTSTANDING

The stats scraper has a manual mode (working now) and an NRL API auto mode (stub).

**What needs confirming:**
- Exact URL for live match stats during a game
- Field names for: inside-20 possessions, errors, set restarts, completion rate
- The `matchState` / `clockStatus` field name for detecting half-time
- Inspect NRL.com network requests during a live Thursday night game

**Known:** `https://www.nrl.com/draw/data/?competition=111&season={s}&round={r}` returns fixtures with matchId, nickName, scores. Whether it includes detailed live stats during a game is unknown.

**Candidate stats API:**
- `https://www.nrl.com/api/stats/nrl-premiership/{season}/round-{n}/{matchSlug}/`
- Match centre URL from fixture `matchCentreUrl` field (inspect raw API response)

---

## How to Use Tonight

For any NRL game at half time:

```powershell
# Manual mode (enter stats you see on NRL.com match centre)
& C:\Users\ElliotBladen\Apps\scripts\run_halftime_nrl.ps1 `
    -Round 14 `
    -Home "South Sydney Rabbitohs" `
    -Away "Manly-Warringah Sea Eagles"
```

Enter the stats when prompted. The system outputs:
1. Updated H2H odds and lines
2. Anomaly matrix with flags
3. Headline signal: "STRONG anomaly — Souths looks better than 6-12 suggests"

---

## Pending

- NRL API live stats endpoint investigation (do this during a Thursday night game — inspect browser network requests on nrl.com match centre)
- Historical backtest: extract HT scores from Flashscore for 2024-2025 NRL, combine with pricing CSVs, calibrate regression factor empirically
- Baz integration: add `get_halftime_context` tool to baz_server.py + route.ts
- AFL version: AFL half-time is different (three more quarters, ~0.65-0.70 regression factor) — do next week per user decision
- Supabase table: `nrl_halftime_matrix` (key) + `nrl_halftime_snapshots` (per-game stats log)

---

## Files created/changed this session

| File | Change |
|------|--------|
| `scrapers/nrl_halftime_stats.py` | NEW — HT stats collector |
| `BettingEngine/scripts/halfTime_price_nrl.py` | NEW — Bayesian pricing model |
| `BettingEngine/scripts/halfTime_matrix_nrl.py` | NEW — 5-signal anomaly matrix |
| `scripts/run_halftime_nrl.ps1` | NEW — pipeline wrapper |
| `data/nrl/halfTime/` | NEW — data directories created |
| `BettingEngine/baz_server.py` | AFL injuries injected, ML data in /signals, BETMATE_ROOT path |
| `app/api/chat/route.ts` | sport param on get_game_context, ML/injury rendering, chaining rule |
