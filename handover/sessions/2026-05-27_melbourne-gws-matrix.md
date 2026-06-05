# Session Diary — 2026-05-27 — Melbourne vs GWS Totals Matrix (AFL R12)

## What was done

Final AFL R12 totals matrix: Melbourne Demons vs GWS Giants, Sun 31 May, MCG, market total 176.5.

Script: `BettingEngine/scripts/_melbourne_gws_totals_matrix.py`

---

## Game params

- Melbourne: prev LOSS (lost to Western Bulldogs 90-93 away, May 24), 7d rest
- GWS Giants: prev WIN (beat Brisbane 166-88 home, May 24, +78pt margin), 7d rest
- Moon: 99.7% illumination — May 31 IS the full moon (is_full_moon = True)
- Day: Sunday afternoon (~15:20 MCG), day game (not night)

---

## Matrix result: No triple confluence — signals split. SKIP.

**Melbourne (HOME) — 3 UNDER / 2 OVER:**

| Condition | Edge | Direction | n | Avg vs line |
|-----------|------|-----------|---|-------------|
| Sunday games | 19% | OVER | 35 | +8 |
| Day games | 10% | OVER | 57 | +4 |
| After a loss | 13% | UNDER | 48 | -4 |
| Full moon (±1d) | 20% | UNDER | 12 | -10 |
| May games | 14% | UNDER | 20 | -0 |

**GWS Giants (AWAY) — 2 UNDER / 2 OVER:**

| Condition | Edge | Direction | n | Avg vs line |
|-----------|------|-----------|---|-------------|
| Away games | 13% | UNDER | 55 | -6 |
| Sunday games | 17% | OVER | 39 | +7 |
| After a win | 18% | UNDER | 56 | -4 |
| Full moon (±1d) | 23% | OVER | 14 | +4 |

**Key conflict:** Full moon fires for both teams — in opposite directions.
- Melbourne near full moon: 20% UNDER, avg -10 below line (n=12)
- GWS near full moon: 23% OVER, avg +4 above line (n=14)

The two Sunday signals both point OVER (Melbourne +19%, GWS +17%) but this is countered by Melbourne's loss form (UNDER) and the conflicting full moon signals.

**Non-applicable but notable:** GWS as away team at the MCG goes OVER 77.8% (n=9, avg 167 vs line 162, +5). Small sample; not formally applicable in the matrix framework since the venue condition only triggers for the home team. Worth tracking as sample builds.

---

## Decision

**SKIP totals.** ML is at market (~178 vs 176.5). No clean confluence direction. Confirmed SKIP in `r12_afl_pricing_2026.md`.

---

## Files updated

- `BettingEngine/scripts/_melbourne_gws_totals_matrix.py` — NEW (created this session)
- `BettingEngine/outputs/results/r12_afl_pricing_2026.md` — Melbourne/GWS totals section updated with matrix result

---

## AFL R12 Matrix Analysis — Complete Summary

All 7 R12 games now either matrix-analyzed for totals or explicitly skipped:

| Game | Matrix run? | Signal |
|------|-------------|--------|
| St Kilda vs Hawthorn | No (model signal clear: UNDER 182.5, no need) | UNDER — model below market |
| Carlton vs Geelong | ✅ `_carlton_geelong_totals_matrix.py` | **OVER 179.5 — Medium** (Geelong 8-way OVER confluence) |
| Sydney vs Richmond | ✅ `_afl_totals_matrix.py` | SKIP (full moon OVER vs May UNDER conflict) |
| Brisbane vs Fremantle | No (monitor Darcy) | Skip for now |
| Bulldogs vs Collingwood | No (model signal clear: UNDER 180.5, ruck crisis) | UNDER — strong model signal |
| Melbourne vs GWS | ✅ `_melbourne_gws_totals_matrix.py` | SKIP (full moon conflict, 2v3 split) |
| West Coast vs Essendon | No (model/ML diverge on totals — skip confirmed) | SKIP |

---

## Context: full moon patterns this round

May 31 is the exact full moon. Games touching the ±1 day window:
- Sydney vs Richmond (May 30): Sydney full moon OVER edge (n=7, 71.4%) — thin, conflicted by Richmond May UNDER
- Melbourne vs GWS (May 31): Melbourne full moon UNDER (-10 vs line) vs GWS full moon OVER (+4 vs line)
- Carlton vs Geelong (May 29): outside window (2 days away) — Geelong near-full moon OVER 62% (n=10, +17) did NOT fire
