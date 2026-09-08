# Rating model selection — which model is production, which is shadow

Date: 8 September 2026
Follow-up to `rating_system_audit_2026-09.md` (6 Sep).
Question from the user: *"form-first-v3.0 — that's the one to use, right? Audit it.
We need one model running with one shadow model behind it."*

---

## TL;DR

| Role | Model | Why |
|---|---|---|
| **Production form rating** | **`form-first-v3.0`** | Strictly supersedes v2: same collateral method + real bug fixes + pace/tempo corrections + a saner scale. Running v2 instead means shipping figures with known-wrong weight and tempo handling. |
| **Shadow** | **`performance-par-v1.0`** | The time/speed figure. It is already what v3 consumes as its speed input, and it is the **only** model that beats a uniform guess on the naive ranking test. Form-vs-speed cross-check = standard professional practice; disagreement → low confidence → no bet. |
| **Retire / stop maintaining** | `horse-ability-v2.1…v2.6` (6 shadows), `achieved-run-v2.x`, `base-lengths-v0.1` | Stale (last built 22 Aug), unused by any pricing path, and the reason "what do we rate Lindermann" currently has four different answers. |

**Important caveat:** v3 is the right *choice*, but it is **not yet a validated
betting input**. Its headline feature is dormant, and it was shipped without
re-running the two gates the 6 Sep audit mandated. It fails both today. See
§4 and §6. Nothing downstream consumes any rating model for pricing yet
(`price_card.py` still uses `base-lengths-v0.1`), so this is a research
decision, not a live-money one — for now.

---

## 1. What `form-first-v3.0` actually is

v2's method (`race_strength = w·collateral + (1−w)·class_standard`, then
`− margin·ppl + weight`) with four changes from audit recommendations 1–4:

| # | Change | State | Verdict |
|---|---|---|---|
| 4 | **Variable pounds-per-length** — `ppl × going × tempo`, not distance alone. Firm 1.05 → heavy 0.85; confirmed false-tempo race cuts ppl up to 30%; unseen-tempo race −10%. | **live** | Sound. Matches BHA/Timeform practice. |
| 3 | **Compression fix** — `class_standard` is now a *low-coverage stabiliser only* (leans on it when `anchor_coverage < 0.60`), not a two-way magnet toward a fixed par. Plus a **margin taper** (linear credit to 4 L, then ×0.45) for F2. | **live (partial)** | Helps the top end a little (−2.4 vs −3.1 vs official). The deep uncompression is **blocked** — expressing a 125+ run needs a fast-time signal, i.e. change 1. |
| 2 | **Pace/tempo folded into the level** — `v2_race_pace_shapes` + `v2_runner_pace_ratings` neutralise collateral anchors and add a bounded per-run pace term. | **live (67% of races)** | Directionally correct and hand-verified: Pride Of Jenni's margin-inflated 2024 QE −2.4, deep-race runs the old model buried (Prognosis, Gringotts) +3. The two pace-model versions still disagree on borderline races. |
| 1 | **Form + speed dual rating** — promote `performance-par-v1.0` to a co-equal blended input. | **BUILT BUT DORMANT** | Wired lift-only and inert at the top. **Blocked on `performance-par-v2.0`** — par-v1 has no weight/class/pace adjustment, so it under-rates slow-run tactical WFA G1s by 20–40 pts and over-rates fast light-weight handicaps. This was the audit's *"largest single lever"* and it is not yet pulled. |

Two post-build bug fixes (commits `35bbedf`, `ead102a`) are also real
improvements, both caught by inspection not by a test:
- **Weight is a merit term, not the handicapper's policy scale.** Was 2.2 pts/kg
  (what the handicapper uses to *set* weights); now 0.9 handicap / 0.2 WFA. Before
  the fix, a mare's conqueror out-rated her for carrying the 2 kg sex allowance
  (Buckaroo > Via Sistina in the 2025 Cox Plate).
- **`pace_collapse` ≠ false tempo.** A collapsing/fast tempo means the early
  speed was *genuine* → beaten margins are more reliable, not less. Was being
  double-penalised.

---

## 2. Coverage & scale (this DB, `--as-of 2026-09-06`)

| | rated runs | p5 | p50 | p95 | p99 | max | sd |
|---|---:|---:|---:|---:|---:|---:|---:|
| `performance-par-v1.0` | 28,485 | 81.4 | 96.2 | 106.4 | 111.6 | 130.9 | 8.0 |
| `form-first-v2.0` | 29,541 | 49.0 | 74.1 | 103.1 | 112.4 | 127.4 | 17.4 |
| **`form-first-v3.0`** | 29,498 | 60.0 | 75.6 | 103.7 | 112.5 | **127.6** | **13.5** |

v3's scale is meaningfully saner than v2 — the maiden-race floor lifts from 49 to
60 and spread tightens (sd 17.4 → 13.5) from the margin taper + variable ppl.
Median runs ~+3.4 above v2. **Neither v2 nor v3 can express a 125+ elite run** —
that ceiling is structural (collateral is anchored on official ratings, all-time
max 127) and only lifts with change 1.

---

## 3. F1 — compression vs official rating (winners, mean Δ = model − official)

| official band | n | par-v1 | v2 | **v3** |
|---|---:|---:|---:|---:|
| 0–80 | ~1,500 | **+28.5** | +6.5 | **+6.6** |
| 80–95 | 557 | +14.1 | +3.1 | +2.5 |
| 95–105 | 300 | +2.2 | +0.8 | −0.3 |
| 105–115 | 174 | −6.2 | −0.6 | −1.6 |
| 115+ | 68 | −13.9 | −3.1 | **−2.4** |

v3 marginally reduces top-end compression and de-inflates the 95–105 band, but
**the low-end over-rating (+6.6 for sub-80 horses) is unchanged**. The audit
predicted this — the fix is blocked on the speed anchor.

---

## 4. F6 — naive predictive test *(the one that matters, and the one v3 skipped)*

Median-of-last-3 prior rating → softmax → temperature fit on 2024 → test on 2025.
1,238 common test races (all three models ≥60% prior-form coverage).

| model | fitted temp | log loss ↓ | race Brier ↓ | top-pick strike |
|---|---:|---:|---:|---:|
| `performance-par-v1.0` | 30* | **2.318** | **0.895** | **15.0%** |
| `form-first-v2.0` | 30* | 2.362 | 0.907 | 12.4% |
| **`form-first-v3.0`** | 30* | **2.369** | 0.908 | 12.9% |
| uniform (guess evenly) | — | 2.345 | 0.901 | — |

\* temperature maxed the grid — the optimiser wants to flatten the ratings almost
entirely, i.e. the raw spread carries little clean ranking signal.

**v3 is worse than a uniform guess and worse than the par model it sits on top
of, and is statistically indistinguishable from v2.** The 6 Sep audit's
recommendation 7 was explicit: *re-run this test after every change and require it
to beat both uniform and par-v1.* v3 was shipped with the test deliberately
skipped ("validation belongs at the pricing-engine layer"). On the test as it
stands, v3 does not clear the bar.

**Sanity gate** (Spearman vs 24 published 2024/25 official ratings, gate = ≥0.50):
- `form-first-v2.0`: **0.65** (passes)
- `form-first-v3.0`: **0.47** (fails)

n=24 and the set is elite horses — exactly where v3's uncompression changes bite
— so this is soft evidence, and *some* divergence from official ratings is
intended. But a 0.65 → 0.47 drop on the gate v2 has to pass, shipped without
anyone re-running it, is a flag.

---

## 5. Why v3 is still the right production choice

The predictive test says v3 ≈ v2 ≈ noise at *ranking a field on the raw number*.
It does **not** say v3 is worse than v2 as a rating. Everything that is different
between them is a defensible improvement a human handicapper would endorse:

- Real bug fixes (weight-as-merit, tempo direction) — v2 emits known-wrong
  figures for WFA races and pressured-tempo races.
- Saner scale, less top compression, margin taper.
- Pace corrections that the audit author hand-checked case by case.

Running v2 in production over v3 buys nothing and keeps the bugs. The predictive
weakness is **shared** — it is a "raw ratings are too compressed to rank a field"
problem that only change 1 (+ a real pricing layer that adjusts for today's
distance/going/class/weight/fitness) fixes, and that is true of v2 too.

---

## 6. Open gates before v3 is a *betting* input (not just the chosen rating)

1. **Build `performance-par-v2.0`** — weight + class + going/variant + pace-adjusted
   speed figure (the `pace_shape` data supports it). This is the blocker for
   everything below.
2. **Flip change 1 to a real two-way blend** (`SPEED_LIFT_W` → `SPEED_W ≈ 0.4`).
   Changes 1 + 3 together are what finally lift the elite ceiling past 120.
3. **Re-run F6 and require v3 to beat uniform *and* par-v1.** Non-negotiable per
   the 6 Sep audit. If it can't, the raw rating is not fit to feed a price.
4. **Re-run the sanity Spearman** on the full audit set, not n=24; understand the
   0.47.
5. **Market-price backtest** (CLV vs opening/closing odds) — still "not run". The
   only test that actually answers "sufficient for betting".

---

## 7. Infrastructure gap (independent of model choice)

`form-first-v3.0` writes **per-run** figures only (`v3_run_performances`). There
is no consolidated "current rating per horse" for it or for v2. The only
per-horse rollup table, `horse_rating_states`, holds the **legacy**
`performance-par-v1.0` — so anything that naively queries "the ratings table"
(a helper, Baz, a fresh session, the Mac) gets the wrong model.

**Build `v3_horse_rating_states`** — `(model_version, as_of_date, horse_key,
horse_name, overall_rating, peak_rating, recent_rating, reliability, rated_runs,
uncertainty, detail_json)` — a recency-weighted rollup of the per-run v3 figures
(the "Horse Ability Rating" in the tracker's rating architecture, which currently
only exists for legacy + the dead shadows). Point all consumers at it. Tag or
drop the legacy rows in `horse_rating_states`.

---

## 8b. Architecture — where the rating drifted, and the correction *(8 Sep)*

The intended pipeline is documented in `v2_ratings_architecture.md`:

| Step | Layer | Engine |
|---|---|---|
| 1 | Base run figure — **adjusted time + margin + weight + WFA + class standards** | rating |
| 2 | Sectionals / pace / wind / rail / going | rating |
| 3 | **Collateral form network** — later results *revise* earlier races, bounded | rating |
| 4 | Sustainable horse ability (recency, uncertainty, distance bands) | rating |
| 5 | Counterfactual pace scenarios | rating |
| 6 | **Barrier / map / weather / today's pattern → price → EV** | **pricing** |

That doc is explicit that a **"dominant winner must receive positive
performance evidence; it is insufficient merely to downgrade beaten runners"**
and that **"independent time, variant, WFA, margin and sectional evidence may
move a lightly raced horse rapidly away from a stale official-rating prior."**

**What actually happened:** `form-first-v2.0` collapsed Step 1 into *collateral
only* — `race_strength = w·(median top-4 official handicap ratings + margins) +
(1−w)·class_standard`. The horse's own adjusted time barely enters. The Lindermann
case is the failure mode the architecture doc warns against: he rates ~117 because
he beat Ceolwulf (official **119**, actually racing to ~112) and Fangirl (official
**118**, actually ~110) — two stale marks propping up his collateral.

**Why it drifted (from the build notes):**
1. **The clock data can't yet carry a speed figure.** Readiness audit (15 Aug):
   **490 of 4,104 races have no official time**, runner-time coverage 76.5%,
   margin coverage 54.7%, NSW vs VIC sectional semantics inconsistent.
2. **The time approach was tried and failed its isolated gates.** The 22 Aug
   "time and margins" experiment and the Step 11 daily-variant / carried-weight
   candidates (`step11_models.py`) were all built, tested and **frozen — no
   promotion** ("no version achieved both conditions simultaneously").
3. `performance-par-v1.0`'s naive current-state predictor failed a 577-race
   chronological test and was frozen. `form-first-v2.0` was promoted in the
   23 Aug "V2 reset" because it passed the elite **sanity gate** — which only
   checks *"correlates with official ratings at Spearman ≥ 0.5"*. That is
   circular (F8), and F6 shows form-first fails the actual predictive test.

**The correction — `performance-par-v2.0` as the Step-1 spine, not a v3 bolt-on:**

The pieces already exist as frozen research; par-v2 *composes* them into one
adjusted speed figure and refreshes them to the current cutoff:

```
par_v2_run_figure =
    100
  + (par_time(track,dist,going) − runner_time) / secs_per_length     # raw time vs par
  − daily_track_variant(meeting)                                      # step11_models: daily-track-variant-v1.0
  + weight_merit(carried − reference, race_type)                      # 0.9 pts/kg hcp, 0.2 WFA (from v3 commit 35bbedf)
  + pace_adjustment(v2_race_pace_shapes / v2_runner_pace_ratings)     # slow-run race → add back; collapse → dock leaders
  + bounded_class_anchor_pull(thin field / no variant only)           # one-sided, not a two-way magnet
  + capped_last400_sectional
```

- **Coefficients are taken from prior completed research, not fitted fresh** —
  variant shrinkage k=6, weight 0.9/0.2 pts/kg, sectional cap ±2. This avoids the
  "pick an intermediate strength after seeing the results" trap the build notes
  prohibit.
- **Then collateral (`form-first`) is demoted to Step 3** — a bounded, franked
  revision layer on top of the par-v2 base, not the base itself. `class_standard`
  stays only as a one-sided floor for thin/imported fields.
- **Today's-context (barrier, map, weather, jockey, pattern) never enters the
  rating** — that is Step 6, the pricing engine. This part is already correct.

**Validation gate (non-negotiable, from audit rec 7):** the composed par-v2 run
figure, fed through the frozen naive chronological protocol, must beat **both**
uniform **and** `performance-par-v1.0`. If it can't, it is not the spine.

Build order and status: §9.

---

## 9. Refresh + rebuild — 8 Sep 2026

### Refresh (done)

DB was already current (last metro meeting 5 Sep; no racing 6–8 Sep). Rebuilt all
three models at `--as-of 2026-09-08`, DB backed up to
`data/racing_engine.sqlite.bak-pre-refresh-0908`:

| Model | Result |
|---|---|
| `performance-par-v1.0` | 34,636 performances, 14,137 horse states |
| `form-first-v2.0` | 29,541 performances. Sanity gate **passes** (Spearman 0.686). Built-in predictive test: **log loss 2.520 vs uniform 2.345 vs par-v1 2.325** — v2 materially worse than both, confirming F6 on fresh data. |
| `form-first-v3.0` | 29,498 performances. Speed alignment a=−55.8 b=1.35 (the alignment is over-aggressive — a separate v3 issue, moot once par-v2 replaces par-v1 as the speed input). |

### Rebuild — `performance-par-v2.0`, incremental

| # | Increment | Coefficient source | Status |
|---|---|---|---|
| 1 | **Scaffold + daily track variant + clock quarantine.** `racing_engine/performance_par_v2.py`, `par_run_performances` table with explicit attributable components (`raw_time_vs_par`, `daily_variant`, `weight_merit`, `pace_adjustment`, `class_anchor`, `sectional_component`, `margin_component`). | `step11_models` k=6 shrinkage, ≥3 races/meeting | **DONE 8 Sep** |
| 2 | **Weight merit** — `(carried − field median) × pts/kg`, capped ±6. Handicap/Quality 0.9 pts/kg; WFA/set-weights 0.2 (the weight there is an age/sex/penalty allowance, not merit). Relaxes the winner ceiling for a beaten topweight. | v3 commit `35bbedf`: 0.9 / 0.2 pts/kg | **DONE 8 Sep** |
| 3 | **Pace adjustment** — slow-run race adds a bounded amount back to the whole field; fast/pressure/collapse race trusts the time (no add-back); per-runner shape/trip term from `v2_runner_pace_ratings` nets the flattered winner down. | `v2_race_pace_shapes` v2.1, physical reasoning for K | **DONE 8 Sep** |
| 4 | **Thin-par class anchor** — one-sided upward pull toward the class holding standard, only when the *track par* is thin (<12 races) or the meeting has no daily variant. Never caps a figure at/above the standard. Margin-only rows are NOT treated as thin. | v3 §3 method | **DONE 8 Sep** |
| 5 | Scale calibration | — | **deferred — see note** |
| 6 | Run the frozen naive predictive protocol; require beat vs uniform AND par-v1 | audit rec 7 | **passes at every increment** (2.2933 vs par-v1 2.3061 vs uniform 2.3484) |
| 7 | Make par-v2 the base of `form-first-v3.1`; collateral becomes a bounded **franked** revision on top (the race's strength is confirmed/downgraded as its beaten field runs again) | — | **next** |
| 8 | `par_v2_horse_rating_states` consolidated per-horse rollup (§7) | — | pending |

**Why increment 5 is deferred.** par-v2's class spread is tight — G1 winners
median 104.4, benchmark winners 101.1, only ~3 points apart. That is *inherent to
a time figure* (Topspeed vs RPR disagree by 10–20 lb for exactly this reason: a
slow-run good race posts a modest clock). Forcing a linear stretch to widen it
blows the top out (Via Sistina's Cox Plate 128.6 → ~170+). The class spread
belongs in the **franked form layer (increment 7)**, where collateral brings it
back in a bounded way. Calibrate the *composite* figure's scale there, against a
reference, rather than distorting the time figure now and risking the Lindermann
/ Tempted calibration that increments 1–4 got right.

### Results by increment (`--as-of 2026-09-08`, `--test`)

Naive predictive gate (1,376 test races, 2025-01-01 →). par-v1 = 2.3061,
uniform = 2.3484 throughout.

| | par-v2 log loss | Brier | top-pick strike | verdict |
|---|---:|---:|---:|---|
| Increment 1 (variant + clock quarantine) | 2.2988 | 0.8919 | 15.0% | passes |
| Increment 3 (+ pace) | 2.2931 | 0.8905 | 15.9% | passes |
| Increment 3 + winner ceiling | 2.2938 | 0.8906 | 15.6% | passes; 0.0007 correctness cost |
| Increment 2 (+ weight merit) | 2.2935 | 0.8905 | 15.4% | passes; winner-ceiling clamps 1096→740 as beaten topweights let through |
| **Increment 4 (+ thin-par class anchor)** | **2.2933** | 0.8905 | 15.5% | passes; fires on 4% of runs (thin par / no variant), mean +1.6 L |

`form-first-v2.0` = 2.520 and `form-first-v3.0` fail this gate.

Weight-merit distribution: median |adj| 1.1 L, p90 3.2 L, ±6 cap binds on 0.2%
of runs. Class anchor: 1,360 runs, mean +1.6 L — only genuinely thin-par or
no-variant races. **Lindermann/Tempted unchanged through increments 2 and 4**
(Chelmsford par sample is 136, Concorde is WFA) — median-last-3: Lindermann
101.4, Ceolwulf 102.9, Tempted 106.4 (→ ~110 recency-weighted).

### Winner ceiling — "rate on the merits of the day"

The winner franks the form: a beaten runner can be pulled **level** with the
winner by a strong pace/trip read but not **past** it. Each beaten figure is
capped at `winner − max(0.10, 0.15 × beaten_lengths)`. Relaxes to allow a beaten
topweight through once the weight term (increment 2) lands. Applied to ~3% of
historical runs.

### The Lindermann / Tempted case now lands on the expert anchor

| horse | par-v2 last start | par-v2 median-last-3 | expert view |
|---|---:|---:|---|
| **Lindermann** (Chelmsford, `sprint_home`, won) | **99.3** | 101.0 | low 100s ✓ |
| **Ceolwulf** (Chelmsford 2nd, beaten 1.8 L, did the early work) | **99.0** (pace read wanted 100.3; winner ceiling holds it just behind) | 102.9* | just behind on the day ✓ |
| **Tempted** (Concorde, `sustained_high_pressure`, won) | 110.3 (time trusted, no add-back) | 106.8 → ~110 recency-weighted | ~110–11 ✓ |

The whole Chelmsford field now rates 96.7–99.3, winner on top — a tight bunch for
a slow-run G2 where nobody was fully tested. `form-first` had Lindermann at 117.5.

\* Ceolwulf's higher *median-last-3* is his other recent runs, not the Chelmsford
— a legitimate current-ability read once the per-horse rollup (increment 8) exists.
On the day, Lindermann now correctly rates above him.

### Known gaps remaining (increments 4 + 5)

- **Scale is still compressed** (p5–p95 ≈ 85–105): par-v1's median-time anchor
  bunches the field. Increment 5.
- **Compression vs official is still par-v1-like** (+30 low / −13 top) — partly
  *correct* (a sub-80 horse that runs a fast winning time has outrun its mark and
  a time figure should say so), partly the thin-field problem increment 4's
  one-sided class anchor addresses.

---

## 8. Worked example — the horses that started this

**Expert calibration anchor (user, 8 Sep):** *Tempted ~110–111. Lindermann in
the low 100s.* Respected form analysts have the Concorde (Tempted) as the
stronger race — it was run at a genuine sustained pace; the Chelmsford
(Lindermann) was a slow-tempo sprint-home.

| model | Lindermann | Tempted | verdict vs the anchor |
|---|---:|---:|---|
| `form-first-v2.0` last start | 117.5 | 110.7 | Lindermann **~15 too high** (rated off Ceolwulf's stale official 119) |
| `form-first-v3.0` last start | 115.6 | 110.2 | same problem |
| `performance-par-v1.0` last start | ~102 | ~107 | closer |
| **`par-v2` increment 1 — last start** | **96.2** | **110.3** | Tempted **nailed**; Lindermann a touch low |
| **`par-v2` increment 1 — last 3 runs** | 96 / 100 / 108 → **~100 agg** | 110 / 107 / 104 → **~108 agg** | **both land on the expert anchor** |

**The time spine is already landing where the domain expert expects — at
increment 1, before pace, weight or scale calibration.** It is `form-first`
(collateral) that is wrong at 117.

This also calibrates increment 3: Lindermann's slow Chelmsford warrants only a
**modest** pace add-back (his single-run figure ~96 → ~100–102), not a large one.
A slow-tempo race is *less* reliable, not proof the horse is 15 lengths better
than the clock says.
