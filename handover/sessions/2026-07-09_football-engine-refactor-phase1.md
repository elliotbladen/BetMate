# 2026-07-09 — Championship build Phase 1: league-parameterised refactor ✅ GATE PASSED

Phase 1 of the approved Championship plan (`ml/football/CHAMPIONSHIP_PLAN.md`).

## What changed
- `WorldCupEngine/ml/epl/` → **`WorldCupEngine/ml/football/`** (git mv, history preserved)
- Data moved to `ml/football/data/epl/` (per-league data dirs)
- New: `league_config.py` (LeagueConfig + YAML loader) and `leagues/epl.yaml` holding
  every EPL constant verbatim (data paths, rho, blend weights, decay, Elo params, all
  tier coefficients)
- `dixon_coles.py`: decay_rate/min_matches now fit() params; goals-fed leagues supported
  (caller puts goals in the xg columns)
- `elo.py`: EloTracker constructor takes league params (home_advantage, k_base, k_new,
  threshold, reversion, draw_base); `build_from_history(**elo_kwargs)`
- `tiers.py`: new frozen `TierParams` dataclass; all tier functions take it (defaults =
  EPL values, so old callers behave identically)
- `price_match.py` + `backtest/walk_forward.py`: `--league` arg (default epl), all
  constants/paths from config; walk_forward gains a goals-fed branch in load_and_merge
- All `ml.epl` imports and data paths fixed across fetchers/archive scripts; docs
  (ARCHITECTURE.md, BettingEngine/CLAUDE.md) updated

## The regression gate — PASSED exactly
| Metric | Pre-refactor baseline (run today) | Post-refactor `--league epl` |
|---|---|---|
| RPS 2021/22 / 22/23 / 23/24 | 0.1319 / 0.1399 / 0.1287 | **identical** |
| Aggregate RPS / Brier / Acc | 0.1335 / 0.1910 / 54.2% | **identical** |
| price_match Arsenal–Chelsea | λ2.04 μ1.41, H 0.508 @1.97 | **identical** (H2H/AH/ratings) |

Note: `data/epl/clv/backtest_results.csv` content changed vs the committed version —
the committed file was from an OLDER code version (missing the T7 corner feature
columns). Today's baseline regenerated it (season metrics identical); the production
pricer's Over 2.5 moved 0.675→0.673 because its isotonic calibrator now reads the
refreshed file. Data refresh effect, not a refactor effect.

## Also fixed this session
- CLAUDE.md correction: the EPL build diary is NOT missing — it lives at
  `BettingEngine/handover/sessions/2026-07-05_epl-engine-build.md` (BettingEngine has
  its own handover dir separate from repo root).

## Next (Phase 2)
E1 fetcher (football-data league code E1, seasons 2014/15→2025/26 with **2025/26
excluded from all development runs — vault hold-out**), `leagues/championship.yaml`,
goals-fed D-C constants refit (base goals, HFA, decay, tau vs ~33% draw rate).
