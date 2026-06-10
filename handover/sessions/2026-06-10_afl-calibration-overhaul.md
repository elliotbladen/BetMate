# Session Handover — 2026-06-10
## AFL Pricing Model Calibration Overhaul

---

### What We Did

Deep research into why the AFL handicap model was producing lines 15-20pts too extreme vs market.
Identified structural bugs and applied fixes. Re-ran AFL R14 pricing with corrected model.

---

### Market vs Model Comparison (Before Fixes)

| Game | Model | Market | Gap |
|------|-------|--------|-----|
| Bulldogs vs Crows | Crows -10.9 | Bulldogs -4.5 | 15.4pt + DIRECTION FLIP |
| Cats vs Suns | Cats -42.3 | Cats -25.5 | 16.8pt |
| Demons vs Bombers | Demons -50.6 | Demons -30.5 | 20.1pt |
| Kangaroos vs Eagles | NM -35.5 | NM -6.5 | 29.0pt |
| Power vs Swans | Swans -32.8 | Swans -17.5 | 15.3pt |
| Saints vs Giants | Giants -20.3 | Giants -2.5 | 17.8pt |
| Tigers vs Lions | Lions -48.9 | Lions -46.5 | 2.4pt ✅ |

Average gap: 16.7 pts. Only Tigers vs Lions was accurate.

---

### Root Causes Identified

**1. POINTS_PER_ELO too aggressive (0.13)**
Linear ELO scaling overcooks mid-range gaps (100-250 ELO points). AFL has ~33pt margin standard deviation — moderate ELO edges don't translate linearly to margin. At ELO diff of 150-200, the model was producing T1 margins of 25-30pts when the market only prices 12-15pts.

**2. T2 style cap too high (7.0)**
Games were constantly hitting the 7.0 cap. This added a flat 7pt pile-on to already-too-large T1 values. When tiers all align for the strong team, the compounding is severe.

**3. Venue home advantage applied uniformly**
MCG and Marvel Stadium are shared by 3-6 clubs each. Real home advantage at shared venues is ~1-2 pts. Model was applying 6pts (HOME_ADV_ELO=46) to every MCG game, overcooking lines like Demons vs Bombers.

**4. ELO margin cap was missing (already fixed this session)**
`compute_t1_rules()` had no cap. Sydney vs Tigers R12 produced -95.6 T1 margin. Cap of ±50 added.

**5. small_forward silent zero in T5 (already fixed this session)**
Any player entered as `small_forward` silently returned 0.0 impact.

---

### Fixes Applied

| File | Change |
|------|--------|
| `scripts/prepare_afl_round.py` | `POINTS_PER_ELO = 0.09` (was 0.13) |
| `scripts/prepare_afl_round.py` | `T2_MAX = 4.0` (was 7.0) |
| `scripts/prepare_afl_round.py` | `T2_TOT_MAX = 2.0` (was 3.0) |
| `scripts/prepare_afl_round.py` | Added `VENUE_HOME_ADV_OVERRIDES` dict + `get_home_adv_elo(venue)` helper |
| `scripts/prepare_afl_round.py` | `compute_t1_rules()` now accepts `venue` param, uses `get_home_adv_elo()` |
| `scripts/prepare_afl_round.py` | `build_feature_row()` uses `get_home_adv_elo(venue)` for ELO diff |
| `scripts/prepare_afl_round.py` | All ELO diff calculations (T1, ML features, calibration) updated |
| `pricing/afl_tier5_injury.py` | `small_forward` entries added to IMPACT_TABLE |

**Venue home advantage overrides (MCG/Marvel → 15 ELO ≈ 1.4pts):**
```python
VENUE_HOME_ADV_OVERRIDES = {
    'MCG':            15.0,
    'Marvel Stadium': 15.0,
    'Marvel':         15.0,
    'Docklands':      15.0,
}
```
All other venues use `HOME_ADV_ELO = 46.0` (~4.1 pts at new POINTS_PER_ELO=0.09).

---

### AFL R14 Final Prices (Post-Fix)

| Game | Model Line | Market | Gap | Notes |
|------|-----------|--------|-----|-------|
| Bulldogs vs Crows | **Crows -7.3** | Bulldogs -4.5 | 11.8pt | Direction still flipped — ML also says Crows (-15.3). Jordan Dawson T6 major flag driving it. |
| Cats vs Suns | Cats -37.3 | Cats -25.5 | 11.8pt | Still overcooking — T3 travel/rest stack amplifies. Cats may have further systemic overcalibration. |
| Demons vs Bombers | Demons -36.1 | Demons -30.5 | 5.6pt | ✅ Much better — MCG venue fix helped. |
| Kangaroos vs Eagles | NM -27.4 | NM -6.5 | 20.9pt | Persistent outlier — see Known Limitation below. |
| Power vs Swans | Swans -15.8 | Swans -17.5 | 1.7pt | ✅ Essentially spot on. |
| Tigers vs Lions | Lions -29.2 | Lions -46.5 | 17.3pt | ⚠️ Over-corrected — ELO cap + POINTS_PER_ELO reduction pushed this too low now. |
| Saints vs Giants | Giants -15.9 | Giants -2.5 | 13.4pt | Persistent — ML says -22.5, matrix says Giants cover (4-way). Market may be wrong here. |

**Average gap: improved from 16.7 pts → ~11.8 pts** (30% improvement across the board).

---

### Known Limitation — Non-Linear ELO Scaling

The core tension is that `POINTS_PER_ELO = 0.09` works well for moderate ELO gaps but underpredicts extreme gaps:
- Tigers/Lions gap of 478 ELO should produce ~46pt line. Model now gives -29.2 (too low).
- Cats/Suns gap of 150 ELO produces -37.3 (still ~12pts above market).

A linear ELO→margin conversion can't solve both simultaneously. True fix is a **probability-based sigmoid mapping** (`expected_margin = (win_prob - 0.5) × 105`) which naturally compresses extreme differences. This is a larger architectural change — flagged for next AFL model session.

---

### Known Limitation — Kangaroos vs Eagles Fixture

Optus Stadium is West Coast's physical home ground, but the Odds API (and AFL fixture) lists North Melbourne as the "home" team for this game. The model applies home advantage to North Melbourne and penalizes Eagles for being "away from own fortress." This is structurally ambiguous — North Melbourne may have been officially designated as home for commercial scheduling reasons. The 20.9pt gap on this game likely reflects: (a) Eagles' home crowd advantage not captured, (b) possible ELO overcalibration of North Melbourne after a strong recent run.

**Workaround:** Manual override in FIXTURE or INJURIES dict to note this game is physically at Eagles' home ground.

---

### What Research Found (Summary)

Deep web research via agent confirmed key AFL prediction challenges:
1. **AFL margin SD ~33 pts** vs NRL ~15-20 pts — far higher inherent variance
2. **Set-shot conversion variance** (41-60% range across teams) explains ±8-10pts per game — not modelled
3. **Shared venue home advantage** (MCG/Marvel ≈ 1-2pts, dedicated fortresses ≈ 5-8pts) — now partially fixed
4. **Season-phase K-factors** — models like The Arc use K=92 (rounds 1-5), K=62 (regular), K=33 (finals). Our static K may be over-trusting preseason ratings early in the year.
5. **Quarter-by-quarter variance** — Q4 has much higher scoring variance than Q1-Q3. Teams trailing at 3QT have 20%+ chance of covering. Not modelled.

---

### Next Session — AFL Model Improvements

Priority list:
1. **Probability-based margin scaling** — replace `elo_diff * 0.09` with `(win_prob - 0.5) * SCALE`. Calibrate SCALE against 2026 closing lines once season has 15+ rounds. Estimate SCALE ≈ 90-100.
2. **Set-shot conversion tracker** — pull weekly team kicking % from AFL Tables, apply ±2-3pt adjustment.
3. **Validate T3 travel contributions** — the Cats vs Suns T3 stack (+4.8pts for 1406km travel) may be overcooking. Check vs actual outcomes.
4. **Season calibration recalibration** — `margin_correction` increased from +2.8 to +5.7 after POINTS_PER_ELO change. This means model is still underpredicting home team performance by 5.7pts on average. Expected to settle as more 2026 games are added.

---

### Files Changed This Session

- `BettingEngine/scripts/prepare_afl_round.py` — POINTS_PER_ELO, T2_MAX, T2_TOT_MAX, venue home advantage, compute_t1_rules venue param, all ELO diff calculations
- `BettingEngine/pricing/afl_tier5_injury.py` — small_forward IMPACT_TABLE entries
- `BettingEngine/results/r14_afl_2026.csv` — updated R14 prices
