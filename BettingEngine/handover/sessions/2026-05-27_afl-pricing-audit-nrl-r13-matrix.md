# Session Handover — 2026-05-27
## AFL Pricing Deep Audit + NRL R13 Matrix Analysis

---

## What Was Done This Session

### 1. NRL R13 Matrix Analysis — Completed

Read the full `outputs/nrl_handicap_matrix.csv` (1,136 rows) and extracted all edges ≥15% for every R13 team, incorporating: day of week, time of day, rest days, moon phase, H2H vs specific opponent, venue, month, role as fav/dog, and form.

**Top 3 confirmed edges:**

**#1 — Cronulla -2.5 (★★★★★ — 9-way confluence)**
| Factor | Signal | Edge |
|--------|--------|------|
| Thu/Fri night game | Sharks COVER | +44.8% (72.4% cover, n=29) |
| vs Manly H2H | Sharks COVER | +71.4% (85.7% cover, n=7) |
| Ocean Protect Stadium | Sharks COVER | +25.6% (62.8% cover, n=43) |
| Short rest (≤6 days) — Manly | FADE Manly | -35.2% (32.4% cover, n=34) |
| vs Cronulla H2H — Manly | FADE Manly | -71.4% (14.3% cover, n=7) |
| Full moon — Manly | FADE Manly | -38.4% (30.8% cover, n=13) |
| May — Roosters positive | context only |
| Model Sharks -4.2 vs market -2.5 | 1.7pt gap | Model backs market direction |

**#2 — Cowboys -3.5 at GIO Stadium (★★★★)**
| Factor | Signal | Edge |
|--------|--------|------|
| Full moon (±1 day) | Cowboys COVER | +45.4% (72.7% cover, n=11) |
| vs Canberra H2H | Cowboys COVER | +66.6% (83.3% cover, n=6) |
| Sunday game | Cowboys COVER | +33.4% (66.7% cover, n=24) |
| vs Cowboys H2H — Raiders | FADE Raiders | -66.6% (16.7% cover, n=6) |

**#3 — Storm FADE (★★★) — Roosters vs Storm**
| Factor | Signal | Edge |
|--------|--------|------|
| Saturday game | Storm FADE | -33.4% (33.3% cover, n=36) |
| Slight fav (-1 to -9) | Storm FADE | -27.6% (36.2% cover, n=47) |
| Night game | Storm FADE | -15.8% (42.1% cover, n=76) |
| May — Roosters | Roosters COVER | +28.6% (64.3%, n=14) |
| Full moon — Roosters | Roosters COVER | +23% (61.5%, n=13) |
| After a loss — Roosters | Roosters COVER | +16.2% (58.1%, n=43) |

---

### 2. Wests Tigers vs Bulldogs — Detailed Analysis

**Context:** Saturday 30 May, CommBank Stadium, Night, Full Moon ≈ 99.7%

**Tigers signals (all FADES):**
| Factor | Signal | Edge |
|--------|--------|------|
| Full Moon | Tigers FADE | -55.6% (22.2% cover, n=9) ★ |
| Slight Fav (-1 to -9) | Tigers FADE | -46.6% (26.7% cover, n=15) ★ |
| May | Tigers FADE | -25.0% (37.5% cover, n=16) |
| Night game | Tigers FADE | -20.0% (40.0% cover, n=40) |
| CommBank (HOME) | Tigers COVER | +28.6% (64.3%, n=14) — offsets |
| vs Bulldogs H2H | Tigers COVER | +20.0% (60.0%, n=5) — weak |

**Bulldogs signals (all FADES):**
| Factor | Signal | Edge |
|--------|--------|------|
| CommBank Stadium (away) | Bulldogs FADE | -40.0% (30.0% cover, n=10) ★ |
| vs Wests Tigers H2H | Bulldogs FADE | -20.0% (40.0% cover, n=5) |
| Full Moon | Bulldogs FADE | -16.6% (41.7% cover, n=12) |
| Night game | Bulldogs FADE | -16.2% (41.9% cover, n=43) |

**Net result:** Both teams' primary matrix signals are fades. No clean directional handicap bet.
**Best play:** UNDER 48.5 — model 47.8 vs market 48.5. Full moon + night + May all suggest sloppy, close game. If betting this game at all, the totals market is cleaner than the handicap.

---

### 3. AFL Pricing Deep Audit — Completed

Read the full AFL pricing stack: all 7 tier modules + `prepare_afl_round.py` + `model_accuracy/MODEL_ACCURACY_RUNNING_2026.csv` + R12 pricing output.

**Verdict: Structure is sound. Problems are bugs + missing data layers, not architecture.**

---

#### BUG #1 — `small_forward` silent zero impact (CRITICAL, easy fix)
**File:** `pricing/afl_tier5_injury.py`
**Problem:** `IMPACT_TABLE` has no entry for `('small_forward', ...)`. Any player entered with `position: 'small_forward'` silently returns `(0.0, 0.0)` — they're treated as uninjured.
**Fix — add these 4 rows to IMPACT_TABLE:**
```python
('small_forward', 'elite'):   (-1.5, -0.5),
('small_forward', 'good'):    (-1.0, -0.5),
('small_forward', 'average'): (-0.5,  0.0),
('small_forward', 'depth'):   ( 0.0,  0.0),
```

---

#### BUG #2 — HOME_ADV_ELO too high (CRITICAL, easy fix)
**File:** `scripts/prepare_afl_round.py`
**Problem:** `HOME_ADV_ELO = 65.0` → 65 × 0.13 = **8.45 pts** home advantage. AFL modern era is 4–6 pts. Model accuracy R9 showed **+8.40 pt home bias** in handicap predictions — exactly matching this constant.
**Fix:** Lower to ~46 ELO pts (46 × 0.13 = **5.98 pts**). Recommend 46.
```python
HOME_ADV_ELO = 46.0  # was 65.0 — 8.45pts too high for modern AFL era
```

---

#### BUG #3 — No ELO margin cap (CRITICAL, medium fix)
**File:** `scripts/prepare_afl_round.py`, `compute_t1_rules()`
**Problem:** Linear ELO with no cap produces -95.6 pts for Sydney vs Tigers (R12). Market had -61.5. The model can't be used when it produces nonsense extreme values.
**Fix:** Add hard cap at ±50 pts on T1 ELO-derived margin before tier adjustments.
```python
t1_margin = max(-50.0, min(50.0, raw_t1_margin))
```

---

#### MISSING — AFL cover rate matrix (HIGH VALUE, 1-2 days to build)
NRL has `outputs/nrl_handicap_matrix.csv` — 1,136 rows, all teams × all situational categories.
AFL has **nothing equivalent**. The Carlton/Geelong totals matrix (`_carlton_geelong_totals_matrix.py`) was run manually for R12 and found 8-way confluence. This should be systematised.
**To build:** Write `scripts/generate_afl_handicap_matrix.py` using AFL historical results from `BettingEngine/outputs/afl_weekly_review/historical/latest.xlsx`.
Cover all: team, day, time, venue, month, rest, H2H vs opponent, fav/dog role, form, moon phase. Match NRL matrix schema.

---

#### MISSING — AFL umpire tier (MEDIUM VALUE, requires data source)
NRL has T6 (referee) — penalty tendency, set restarts, scoring environment.
AFL has no umpire tier. AFL umpire nominations come Wednesday. Effect is ~3–5 pts on totals (free kicks materially affect scoring).
**To build:** Needs data source. If found, wire as T7 (push emotional to T8 or merge).

---

#### MINOR — T2 style cap too conservative
**File:** `scripts/prepare_afl_round.py`
`T2_MAX = 7.0` — ±7 pts cap. NRL T2 has ±10 pts. AFL style matchups are often more extreme (high-pressure vs run-and-gun). Consider raising to ±10.0 once cover rate matrix is built and calibration is validated.

---

#### MINOR — T3E occasion missing Dreamtime at the 'G
**File:** `pricing/afl_tier3_situational.py`, `signal_3e_occasion()`
Has ANZAC Day + Queen's Birthday. Missing: **Dreamtime at the 'G** (Essendon vs Richmond at MCG, late June). Add a similar flag.

---

#### MINOR — Fixture hardcoded in prepare_afl_round.py
FIXTURE dict manually entered each round (see rounds 7, 8, 12 pattern). Same for INJURIES.
This is a process risk — easy to forget to update. Long-term: read from fixture CSV.

---

## Model Accuracy Summary (from MODEL_ACCURACY_RUNNING_2026.csv)

| Sport | Round | Hcap MAE vs market | Hcap bias vs actual | Total bias vs actual |
|-------|-------|---------------------|---------------------|----------------------|
| AFL | 8 | 43.25 | +20.12 | -20.44 |
| AFL | 9 | 33.26 | +8.40 | +4.00 |
| NRL | 9 | 17.48 | +9.27 | -6.15 |
| NRL | 10 | 11.01 | +2.45 | -2.26 |
| NRL | 11 | 15.22 | +10.61 | +7.13 |

AFL MAE improving (43→33) as we add data, but still 2× NRL error. Root causes: home bias bug + ELO cap.

---

## What To Do Next Session (priority order)

### Priority 1 — Fix bugs (1 hour)
1. Add `small_forward` to `pricing/afl_tier5_injury.py` IMPACT_TABLE
2. Lower `HOME_ADV_ELO` from 65.0 to 46.0 in `scripts/prepare_afl_round.py`
3. Add ELO margin cap at ±50 pts in `compute_t1_rules()` in `prepare_afl_round.py`

### Priority 2 — Missing data layers (1-2 days)
4. Build `scripts/generate_afl_handicap_matrix.py` — AFL situational cover rate matrix
5. Add Dreamtime at the 'G to `pricing/afl_tier3_situational.py`

### Priority 3 — Consider if data exists (multi-day)
6. AFL umpire tier — find data source first
7. Raise T2 cap from ±7.0 to ±10.0 (after calibration validated)

### Also pending from R13
- Run `nrl_injuries.py` once before finalising bets (refs load auto Wednesday 14:00)
- R12 CLV when closing lines available
- AFL R13 fixture CSV: `BettingEngine/outputs/afl_round_prep/r13_2026/fixture_r13_2026.csv` (manual)

---

## Key Files Modified This Session
None — this was a read-only audit session. All fixes identified but not yet implemented.

## Key Files Read
- `outputs/nrl_handicap_matrix.csv` (1,138 lines)
- `outputs/results/r13_nrl_pricing_2026.md`
- `scripts/prepare_afl_round.py` (1,199 lines)
- `pricing/afl_tier5_injury.py`
- `pricing/afl_tier3_situational.py`
- `pricing/afl_tier4_venue.py`
- `pricing/afl_tier6_emotional.py`
- `pricing/engine.py`
- `data/model_accuracy/MODEL_ACCURACY_RUNNING_2026.csv`
- `outputs/results/r12_afl_pricing_2026.md`
