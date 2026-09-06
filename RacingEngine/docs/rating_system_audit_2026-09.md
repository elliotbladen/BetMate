# Horse Rating System — Audit & Review

Date: 6 September 2026
Model audited: `form-first-v2.0` (`racing_engine/v2_ratings.py`)
Reviewer's brief: full audit + external benchmark against professional rating
systems; verdict on sufficiency.

## 1. What the system is

`form-first-v2.0` is a **collateral-form / handicapping-style rating**, in the
family of the official BHA figure or Racing Post Ratings (RPR). It is **not** a
speed figure (Beyer / Topspeed / Ragozin / Thoro-Graph).

Per run, for the winner: `rating = race_strength`; for others:
`race_strength − beaten_lengths × ppl + weight_component`.

`race_strength = w · collateral + (1−w) · class_standard`, where:
- `collateral` = median of the **top-4 finishers'** `[official_handicap_rating
  + beaten_lengths × ppl + weight_delta]` — sound practice, matches the BHA
  ("principals, not the beaten tail").
- `class_standard` = a fixed holding figure per class family (G1 = 115, … ,
  maiden = 72).
- `w = min(0.80, 0.25 + 0.65 · anchor_coverage)` — with full coverage, 0.80.
- `ppl` = distance-only interpolation (3.0 lb/L at ≤1000 m → 1.0 at ≥2800 m).

**Explicitly excluded from the level** (per the run detail JSON):
`official_clock_used_for_level: false`, `sectionals_role: future pace/confidence
only`. No time, no sectionals, no going, no pace/tempo shape.

Model family in the DB:
| Version | Rows | Role |
|---|---:|---|
| `base-lengths-v0.1` | 204 | Elo-style ancestor, retired |
| `performance-par-v1.0` | 19,667 | par/time-based, **going-aware**, not production |
| **`form-first-v2.0`** | 29,541 | **accepted production model** |
| `achieved-run-v2.x`, `horse-ability-v2.x` | shadow | ongoing experiments |
| `v2_race_pace_shapes` / `v2_runner_pace_ratings` | 3,430 / 34,968 | **pace shape computed for nearly every race — unused by the rating** |
| `canonical_sectionals` | 87,026 | unused by the rating |

## 2. How professional systems do it

| System | Basis | Pace / trip | Going | Class anchor | Scale top |
|---|---|---|---|---|---|
| **Timeform** | time **+** subjective race read, single number | yes — "compromised by pace, wide trips, eased late" | yes | race standards as *holding* figures only | 147 (Frankel) |
| **RPR** (form) | handicapper watches replays, weight-adjusted | yes (judgment) | yes | previous form + race standards | ~140 |
| **Topspeed** (time) | race time → figure via standard times + **going allowance + wind** | implicit (truly-run assumption) | yes, explicit allowance | standard times | — |
| **Beyer** | final time + distance + **daily track variant** (par vs actual, human-judged) | lengths-behind → points | via the variant | class pars per track/distance | ~120s of points |
| **Ragozin / Thoro-Graph** | time with **ground-loss, trip, weight, pace, wind, surface** folded in | yes — core of the method | yes | pattern projection, not a class par | ~0–2 elite (low = good) |
| **BHA official** | replays ×many; weight, lengths, going, **tempo**, draw, slow starts | yes | yes | previous performances + race standards + **same-card time comparisons** | ~140 |
| **WHR** (academic) | Bayesian dynamic Bradley–Terry over the whole result graph | — (implicit) | as covariates | none — strength is latent | continuous |

**Two universal features `form-first-v2.0` lacks:**
1. Every serious operation runs **both a form figure and a speed/time figure**
   and cross-checks them (Topspeed vs RPR; Beyer alongside Brisnet class).
2. Every serious operation folds **pace/tempo and trip** into the figure.

## 3. Audit findings

### F1 — Systematic compression: over-rates moderate horses, under-rates elite

Across **2,625 winners**, model vs official rating:

| Official rating band | n | Model − official |
|---|---:|---:|
| 60–80 | 1,474 | **+6.3** |
| 80–95 | 557 | +3.1 |
| 95–105 | 300 | +0.8 |
| 105–115 | 174 | −0.6 |
| **115–140** | 68 | **−3.1** |

The scale pivots near 100–110 and rotates inward. Cause: the fixed
`class_standard` pull (0.2 weight, G1 = 115) *lifts* sub-par fields and *drags*
elite fields toward 115; and the collateral is anchored on official ratings,
of which only 0.15 % ever exceed 120 (all-time max 127). 99.9 % of all run
ratings are ≤ 118. **The model structurally cannot express a 125+ performance.**
Worked cases this session: Sir Delius QE 122.3 (≈ 4–6 pts light), Lindermann
Chelmsford 117.5 (about right — he is genuinely that good).

### F2 — Margin drives the figure with no shape correction

G1 winners, by winning margin:

| Won by | n | Winner rating |
|---|---:|---:|
| 0–0.5 L | 82 | 106.1 |
| 1.5–3 L | 25 | 111.8 |
| **6–20 L** | 3 | **123.2** |

A 6 L+ G1 win rates ~17 points above a 0.3 L G1 win. `ppl` is fixed by distance
only — not by going or by how the race was run. Consequence: **front-running
steals in slowly-run races are over-rated** (Pride Of Jenni 2024 QE = 124.5, but
run in 122.0 s vs a 120.4–120.6 s norm for that race — ~9 lengths slow; ~half
her figure above the class standard is winning margin over 116–118-rated
horses). The mirror case — **anti-suited horses beaten in a false tempo are
under-rated** (Giga Kick/Rothfire in the 2026 Moir).

### F3 — No time / speed figure at all

The engine has `performance-par-v1.0` (going-aware, par-based) and 87 k
sectionals, and uses neither for the level. Professional practice is a
form/speed dual rating. **This is rating with one eye closed.**

### F4 — No going adjustment to the level

BHA, Timeform, Topspeed, Beyer all adjust for ground. `form-first-v2.0` does not
(it only launders it indirectly through official ratings). A genuine Soft-track
performance and a Good-track one of equal merit are treated identically at the
front end; the fixed `ppl` also mis-scales beaten margins on soft ground
(margins stretch — BHA varies ppl by going).

### F5 — Anchors on official ratings, which lag reality

Ceolwulf ran to 108–113 recently but carries an official 119, which propped up
Lindermann's Chelmsford collateral. No mechanism prefers recent form-first
history over a stale mark when the two diverge.

### F6 — Predictive power is near zero in the engine's own backtest

Chronological test (train 2024, test 634 races in 2025), softmax of
median-of-last-3 rating, temperature fitted on 2024:

| | log loss ↓ | race Brier ↓ | top-pick strike |
|---|---:|---:|---:|
| **`form-first-v2.0`** | **2.455** | **0.935** | 12.6 % |
| `performance-par-v1.0` | 2.307 | 0.896 | 13.9 % |
| uniform (guess evenly) | 2.322 | 0.898 | — |

`form-first-v2.0` is **worse than uniform on log loss and Brier**, and **worse
than the older par model it replaced** on every metric. The fitted temperature
maxed out the grid (15) — the optimiser wanted to flatten the ratings almost
entirely, i.e. the rating spread carries little clean signal.

*Caveat:* the test is deliberately naive (raw median-of-3, no adjustment for
today's distance / going / class / weight / fitness / barrier). A real pricing
layer would adjust. But professional ratings still beat uniform meaningfully on
naive tests, because a true 115 beats a true 85 most days. This does not say the
ratings are worthless — it says the **raw rating is too noisy / compressed to
rank a field**, and V2 regressed V1 here.

### F7 — 2yo races on an open-company scale

"Group 1" 2yo winners (Golden Slipper etc.) rate ~66–95 because the field's
official ratings are 2yo-level. Needs age-conditional class pars.

### F8 — Sanity gate is partly curve-fit

Hard-coded `elite_names = {autumnglow, sirdelius, viasistina, mrbrightside}` and
"top-10 must contain ≥ 7 group_1 runs". The only non-circular check is
audit-Spearman ≥ 0.50 (actual 0.686) — and that tests against official ratings,
which F1/F5 show are themselves imperfect.

### F9 — No trajectory / "likely to improve" signal

Timeform's `p`, Ragozin's pattern projection ("forward, regress, duplicate").
`form-first-v2.0` emits a point estimate + confidence; `_previous_form` is a
flat median-of-3. No lightly-raced-upside or bounce/regression read.

### F10 — Data-quality leak in V1 (minor, but telling)

`performance-par-v1.0` has a max rating of **376** — an uncleaned clock error.
V2's clock quarantine is better, but the shared cleaning layer needs hardening
before V1 is composed back in.

## 4. What it does well

- **Transparency** — every figure ships a component breakdown. Better than the
  proprietary black boxes.
- **Data hygiene** — append-only snapshots, strict no-lookahead, clock
  quarantine, versioned models. Professional-grade.
- **Collateral method** — median of the top-4 principals, excluding the beaten
  tail, is exactly right and matches the BHA.
- **It has a real chronological backtest** — most homebrew systems never build
  one. (It's just currently failing it.)
- **Conservative** — will not emit wild figures.
- Correlates with official ratings at Spearman 0.686 — a reasonable descriptive
  floor.

## 5. Verdict — is it sufficient?

**As a transparent research baseline / V1: yes, a credible start, and the
engineering is genuinely good.**

**As the rating engine under a betting model: no, not yet.** Three blocking
gaps:

1. **No speed/time figure** (F3) — you are pricing with one input missing that
   every professional operation treats as mandatory, and the engine's own
   time-aware model out-predicts it (F6).
2. **No pace/tempo correction** (F2) — it provably misreads front-running steals
   and false-tempo races, i.e. it is least reliable exactly in the races where
   there is an edge.
3. **Near-zero raw predictive power** (F6) — correlating with official ratings
   is not the same as ranking a field; V2 regressed V1 on the backtest.

The compression (F1) is secondary but bites hardest at the top of the market —
the elite horses you would most want to back are the ones it under-rates.

## 6. Recommendations (prioritised)

1. **Build `form-first-v3.0` as a form + speed dual rating.** Promote
   `performance-par-v1.0` from "V1 we compare against" to a co-equal input:
   `v3 = blend(collateral_form, going_adjusted_speed_figure)`, cross-checked,
   with disagreement surfaced as lower confidence. Largest single lever.
2. **Fold pace/tempo into the level.** `v2_race_pace_shapes` (3,430 races) and
   `v2_runner_pace_ratings` (34,968) already exist. In a false-tempo race:
   dampen margin credit; add a bounded "flattered by soft lead" discount for the
   front-running winner; add a bounded "beaten by the tempo" excuse for
   anti-suited losers. This is Layer 1 of the Race Strength Engine — do it
   **inside the core rating**, not only as a bolt-on.
3. **Fix the compression.** Taper `class_standard` weight to ≈ 0 when
   `anchor_coverage` is high and collateral diverges from standard; treat
   `class_standard` as a *floor* for thin/imported fields, not a two-way anchor;
   let the scale run past 120.
4. **Variable pounds-per-length** — by going and by final-time-vs-par, not
   distance alone (per BHA / Timeform practice).
5. **Recency-weight the anchor** — prefer recent form-first history over a stale
   official rating when they diverge (the franking mechanism).
6. **Age-conditional class pars** — a 2yo scale.
7. **Re-run the chronological backtest after every change** and require it to
   beat **both** uniform and `performance-par-v1.0`. It currently beats neither.
8. **Add the market-price backtest** — CLV vs opening/closing odds. Listed in the
   code as "not run". It is the only test that matters for betting; until it
   exists, "sufficient for a betting engine" cannot be answered empirically.
9. **Harden the shared clock-cleaning layer** (F10) before composing V1 back in.
10. **Replace the curve-fit sanity checks** with held-out predictive gates.

## 7. Longer horizon

The layered fixes above are the pragmatic path. The rigorous end-state is a
**joint solve** — Whole-History Rating (Coulom 2008) or a Massey/Plackett–Luce
system that estimates horse latent ability over time and race strength
simultaneously from the whole result graph, with going/pace as covariates. That
naturally removes F1 (no fixed class par), F5 (no stale anchor) and F6 (fitted
to prediction, not to official ratings). Heavier to build and keep stable;
justify it once the dual-rating v3 has a shadow-season record.

## 8. Resume point

Start with recommendation 1: a `form_speed_figure.py` that computes a
going/variant-adjusted time figure per run (extending `performance.py`), then a
`form_first_v3.py` that blends it with the collateral figure and re-runs the
`prediction_test`. Gate on beating uniform and V1.

---

## 9. `form-first-v3.0` — what was built (2026-09-06)

`racing_engine/form_first_v3.py`, table `v3_run_performances`, 29,541 runs.
The user's call: build the four fixes, no rating-only backtest (validation
belongs at the pricing-engine layer against market prices).

| Change | State | Notes |
|---|---|---|
| **4. Variable ppl** (going × tempo, not distance alone) | **live** | `GOING_PPL_MULT` firm 1.05 → heavy 0.85; a confirmed false-tempo race cuts ppl up to 30%; an unseen-tempo race takes a 10% haircut. |
| **3. Compression fix** | **live (partial)** | Class standard is now a **low-coverage stabiliser only** (`coverage < 0.60` leans on it), not a two-way magnet toward a fixed par. Cleaner method. But the deep top-end uncompression (F1: elite runs −3 vs official) is **blocked** — it needs a fast-time signal to rate a run 125+ without a 125-rated official anchor, i.e. it needs change 1. Also added a **margin taper** (linear credit to 4 L, then ×0.45) for F2. |
| **2. Pace into the level** | **live (coverage-limited)** | `v2_race_pace_shapes` / `v2_runner_pace_ratings` neutralise the collateral anchors and add a bounded per-run pace term. Fires on the 67 % of races with sectionals; the two pace-model versions (v2.0 / v2.1) disagree on borderline races (Pride Of Jenni's 2024 QE: `slow_early` vs `even`). |
| **1. Form + speed dual rating** | **built, dormant** | Wired as a **lift-only** blend (a fast raw time can push a run UP, never cut it). Currently inert at the top because `performance-par-v1.0` has **no weight/class/pace adjustment** — it under-rates slow-run tactical WFA Group 1s by 20–40 points and over-rates fast light-weight handicaps. **Blocked on `performance-par-v2.0`.** A crude weight add-back (`SPEED_WEIGHT_PTS_PER_KG`) is in place as a stopgap. |

**Immediate next task: `performance-par-v2.0`** — a going/variant + weight + class + pace-adjusted speed figure (the `pace_shape` data supports it). Then flip change 1 to a proper two-way blend (`SPEED_LIFT_W` → a real `SPEED_W ≈ 0.4`) and changes 1 + 3 together finally fix the top-end compression.

### First v3 leaderboard (top 12, since 2023-09-06)

| # | Run | v3 | (v2, Δ) |
|---|---|---:|---|
| 1 | Via Sistina — 2024 Cox Plate (1st) | 125.3 | (127.4, −2.1) |
| 2 | Buckaroo — 2025 Cox Plate (2nd) | 122.6 | (122.0, +0.6) |
| 3 | Gringotts — 2026 Doncaster (4th) | 122.5 | (119.8, +2.7) |
| 4 | Giga Kick — 2024 Premiere Stks (2nd) | 122.3 | (122.4, −0.0) |
| 5 | Pride Of Jenni — 2024 QE Stks (1st) | 122.1 | (124.5, **−2.4**) |
| 6 | Sir Delius — 2026 QE Stks (1st) | 122.1 | (122.3, −0.1) |
| 7 | Prognosis — 2024 Cox Plate (2nd) | 122.0 | (118.8, **+3.2**) |
| 8 | Gold Trip — 2023 Caulfield Cup (3rd) | 121.4 | (121.4, 0.0) |
| 9 | Ceolwulf — 2025 Champions Mile (1st) | 121.1 | (121.6, −0.5) |
| 10 | Johnny Rocker — 2024 Manikato (2nd) | 120.7 | (120.8, −0.1) |
| 11 | Dubai Honour — 2026 Tancred (2nd) | 120.4 | (121.6, −1.2) |
| 12 | Pericles — 2025 Champions Mile (2nd) | 120.1 | (121.5, −1.4) |

Directionally: Pride Of Jenni's margin-inflated QE comes down 2.4 and drops below
Sir Delius (matches the manual read); deep-race runs the old model buried
(Prognosis, Gringotts) come up ~3; Via Sistina's Cox Plate stays #1. Absolute
scale runs ~+3.6 above v2 — arguably v2 was compressed, but this needs the
par-v2 speed anchor to confirm rather than a fixed recenter.
