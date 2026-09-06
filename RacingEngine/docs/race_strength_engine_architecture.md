# Race Strength Engine — Research & Architecture

Date: 6 September 2026
Proposed version: `race-strength-shadow-v1`
Status: architecture and research only. No price, rating, EV or stake may consume
any output until the promotion gates in §8 pass. Target contribution once
promoted: **1–5 %** of the pricing signal, never dominant.

## 1. Product boundary

The Race Strength Engine answers one question: **how good was the opposition a
horse has actually been beating (or being beaten by)?** — so that when horses
from different form pools meet, the engine knows which form lines were earned in
deeper water.

Worked example (the reason this exists). On 5 Sep 2026, `form-first-v2.0` rated:

| Race | Grade | Race strength | Winner run | 2nd run |
|---|---|---:|---:|---:|
| Concorde Stakes (Randwick R8) | G2 | 110.7 | Tempted 110.7 | Headwall 110.6 |
| Moir Stakes (Sandown R8) | **G1** | 108.1 | My Gladiola 108.1 | Cavalry Girl 107.1 |

The Group 2 was the stronger race. Tempted and Headwall have recent figures of
107–110 across group company; My Gladiola's line was 79 → 90 → 106 → 108 and
Cavalry Girl's 59 → 83 → 96 → 96. If these fields meet next week the raw ratings
will look close, and the engine must apply a **class-exposure delta** that
favours the Concorde horses.

It does **not** predict the winner, replace `form-first-v2.0`, or re-rank a race
on its own. It emits a small, bounded, per-runner adjustment plus diagnostics.

## 2. What already exists (reuse, do not rebuild)

| Asset | What it gives us |
|---|---|
| `v2_run_performances.race_strength` | Per-race field-strength figure (n≈29,541, mean 85.2, sd 12.7). Already the "the Concorde was stronger" signal. This is the **seed**. |
| `v2_run_performances` full history | 2,750 races with participant lists, finishing detail, dates — everything franking needs. |
| `collateral_revision_v2.py` (V2.9 shadow) | Time-stamped collateral revision when two horses meet again. Currently hand-coded for one pair (Gringotts). **Generalise this into Layer 2.** |
| `v2_race_pace_shapes` + Expected Tempo V0 | Whether a race was truly run — needed to know when a strength figure is tempo-distorted (the Moir problem). |
| `canonical_sectionals`, official clocks, `performance-par-v1.0` | Going-adjusted time merit as an independent corroboration of race level. |
| `group1_backtest.py` | Existing black-type evaluation harness to extend. |

## 3. Signal decomposition

"Quality of a race" is not one thing. The engine separates:

1. **Nominal grade** (G1/G2/G3/Listed/BM). Weak on its own — the Moir/Concorde
   case is the proof. Used only as a shrinkage prior.
2. **Participant class** — the field's official ratings and recent `form-first`
   figures, trimmed to the principals. This is what `race_strength` already does.
3. **Tempo integrity** — a truly-run race produces informative beaten margins.
   A false tempo does not just make the result *unreliable*, it makes it
   *biased*: it favours on-pace / sharp-quickening types and penalises
   strong-galloping horses and backmarkers who need a genuine speed. So the
   beaten form of an anti-suited horse carries a legitimate excuse (Giga Kick,
   Rothfire in the Moir), and the on-pace winner may be flattered. The response
   is **not** a one-directional penalty — see §4 Layer 1. Sourced from the
   Expected Tempo / pace-shape layer plus a per-horse tempo-suitability tag.
4. **Franking** — did the other runners go on to perform well? Clean and hard to
   game, but lagged 2–8 weeks.
5. **Time-vs-par merit** — going-adjusted clock evidence that the race was run at
   a genuine level, as a bounded cross-check.

## 4. Layered architecture

```text
 race_strength (existing)   grade prior   tempo integrity   time-vs-par
            \                    |              |               /
             +--------- Layer 1: Race Strength Index (RSI) ----+
                                      |
              participants run again (append-only, no lookahead)
                                      |
                    Layer 2: Franked RSI  rsi_franked(race_id, as_of)
                                      |
              per horse: decayed roll-up weighted by finishing merit
                                      |
             Layer 3: Class Exposure   { class_ceiling, class_habitual, conf }
                                      |
                    upcoming race field + context
                                      |
        Layer 4: Matchup Class Delta   bounded ± adjustment per runner
                                      |
              future Pricing Engine (after promotion, capped 1–5 %)
```

### Layer 1 — Race Strength Index (RSI)

Per historical race, a revised field-strength:

```
rsi = w_field · trimmed_participant_class
    + w_grade · grade_standard
    + w_time  · clamp(time_vs_par_merit, ±cap)
```

- `w_field` scales with anchor coverage.
- **Tempo handling is uncertainty-first, not a penalty.** When tempo integrity
  is low:
  - the RSI *level* stays roughly where participant-class puts it — a false
    tempo does not make a race weak, it makes it *unknown*;
  - `rsi_confidence` drops sharply;
  - a bounded **per-horse tempo-suitability** term is applied inside the
    collateral: an anti-suited beaten runner gets an "excuse" credit, an
    on-pace winner gets a "flattered" discount. The net move can be **either
    direction** and is capped.
  - the honest resolution is deferred to Layer 2 franking.
- Emits `rsi`, `rsi_confidence`, and a `components` JSON so every figure is
  reproducible.
- Back-compatible: with neutral tempo and no time evidence, `rsi ≈ race_strength`.

Worked example — the Moir. Participant-class ≈ 108–113 (Giga Kick 116 etc.), so
the RSI *level* is not cut, but `rsi_confidence` is low; Giga Kick/Rothfire (a
strong-tempo style, beaten in a crawl) get a small excuse credit; My Gladiola
(on-pace, won the sprint home) gets a small flattered discount. Then we wait for
those horses to run again.

### Layer 2 — Franked RSI (generalise `collateral_revision_v2`)

Append-only, time-stamped revisions. For each race, when a participant next runs:

- beaten runner **wins/places in a race of known RSI** → frank the source race up
- beaten runner **is well beaten again** → frank it down
- weight the revision by the later race's own confidence and recency
- **strict no-lookahead**: `rsi_franked(race_id, as_of=D)` only uses runs before D

This is the single highest-value layer — it is how "the Concorde form was well
franked / the Moir form fell apart" becomes a number.

### Layer 3 — Class Exposure (per horse)

A decayed rolling roll-up of the (franked) RSI of races the horse has contested,
weighted by **finishing merit within each race** (winning a 110 race ≫ last in
one):

- `class_ceiling` — best RSI the horse has been genuinely competitive in
  (won, placed, or beaten < ~1.3 L)
- `class_habitual` — half-life-decayed average RSI of recent starts
- `exposure_confidence` — from run count and recency

### Layer 4 — Matchup Class Delta (the payoff)

For an upcoming race:

```
context      = trimmed median of field class_habitual (+ grade of today's race)
raw_delta_i  = k · tanh( (exposure_i − context) / scale )
delta_i      = clamp(raw_delta_i · exposure_confidence_i, ±CAP)
```

Then **zero-centre `delta` across the field** — it is a redistribution of
confidence, not inflation. Also emit a race-level `class_spread` (how mismatched
the field is on exposure) — a wide spread is itself a betting signal and a flag
that the raw ratings are least trustworthy.

`exposure_confidence_i` already carries the tempo-integrity uncertainty from
Layers 1–3, so a runner whose recent form is mostly from false-tempo races
gets a **shrunk** delta in both directions. When two form pools of differing
tempo integrity meet (Moir vs Concorde), the delta between them is deliberately
*smaller* than for two truly-run pools — the correct output is "hold judgment /
trim stake", not a confident lean.

`CAP` starts at **±2.0 rating points** (≈ the 1–5 % price weight target) and is
only widened if the season backtest earns it.

## 5. The deep option — simultaneous solve (v2, flagged not scheduled)

The layered pipeline is sequential and approximate. The rigorous version treats
every result as pairwise/rank evidence and solves for `{horse latent ability over
time}` and `{race strength}` **jointly** as a maximum-likelihood fixed point:

- **Whole-History Rating** (Coulom, 2008) — time-varying strength, the natural
  fit; published applications to racing exist.
- **Massey / Colley least-squares / SRS** — race strength falls out as a
  by-product of a linear system; strength-of-schedule is built in.
- **Plackett–Luce** likelihood — the correct model for a multi-runner finishing
  order (vs Bradley–Terry for pairs).
- **Glicko-2** — carries an explicit rating deviation, so confidence is native.

Heavier to build, fit and keep stable. Build the layered engine first; use its
shadow record to decide whether the simultaneous solve is worth it.

## 6. Prior art

Timeform race ratings and "franked form"; Racing Post Ratings / Topspeed; Beyer
speed figures (track-variant adjustment — same idea, different axis); Whole-History
Rating; Glicko / Glicko-2; Massey, Colley, and the Simple Rating System used in
gridiron strength-of-schedule; Bradley–Terry / Plackett–Luce ranking models.

## 7. Data readiness

Everything Layers 1–4 need is already in `racing_engine.sqlite`. No new external
feed. Layer 1 mostly re-reads `race_strength`; Layer 2 needs the participant →
subsequent-run join (present); Layer 3/4 are aggregation. The simultaneous solve
would want the full result graph exported once.

## 8. Promotion gates

Consistent with V2.10, Map Position and Expected Tempo — **shadow only** until:

1. Append-only prospective `rsi`, `rsi_franked`, `class_exposure` and
   `matchup_delta` snapshots stored for a **full season**, frozen before each
   race, never overwritten.
2. On a held-out season, the matchup delta must improve calibration / CLV
   **specifically on cross-pool and rematch races** (the cases it targets) —
   not just not-hurt the average.
3. No lookahead anywhere: every franked figure audited to use only prior runs.
4. Contribution to any price capped at **5 %**, and a recorded integration
   decision, before it moves a cent.

`matchup_delta` must never feed back into `rsi` or `performance_rating` within a
cycle — strictly one-directional.

## 9. Integration into the future Pricing Engine

The Pricing Engine **calls** this engine; it does not contain it. Per upcoming
race it reads `get_class_exposure(horse_key, as_of=race_date)` for each runner,
computes the Layer 4 matchup delta, and adds it to that runner's base form
rating before deriving a price. It is one module of ~5–6 (base form rating,
pace/tempo, settling map, going/track, jockey-barrier, race strength).

**Weight policy** — design target is **3 %** nominal, confidence-scaled.

| Phase | Live weight | Notes |
|---|---|---|
| Shadow season 1 | **0 %** | log what it would have done; frozen pre-race snapshots |
| First promotion (design target) | **3 %** | meaningful when it fires, small
  enough a miscalibration can't damage the engine. Not 2 % (too timid to matter
  even in clash cases); not 4–5 % (overlaps the base rating's collateral form,
  thin data for a year, minority of races → more than it has earned in year one) |
| Hard cap, seasons 1–2 | **3 %** | even if the backtest says more |
| Widen toward **5 %** | only after a second season confirms |

The weight is **confidence-scaled, not flat**: effective contribution =
`nominal_weight · f(class_spread · exposure_confidence)`. A homogeneous field →
≈ 0. A wide-spread, well-franked clash (Moir pool vs Concorde pool) → at the
cap. Fit the nominal weight to measured CLV improvement, walk-forward, on the
subset of races where `class_spread` exceeds a threshold — never the average.

## 10. Build order / effort

| Step | Est. | Notes |
|---|---|---|
| Layer 1 RSI + schema + tempo contract | 1–2 d | reuses `race_strength` |
| Layer 2 franking (generalise `collateral_revision_v2`) | ~2 d | highest value |
| Layer 3 class-exposure roll-up | ~1 d | |
| Layer 4 matchup delta + backtest harness | ~1 d | extend `group1_backtest.py` |
| Prospective snapshot + monthly scorecard | ~1 d | mirrors Expected Tempo |
| (v2) simultaneous WHR/Massey solve | 1–2 wk | decide after a shadow season |

## 11. Resume point

Build Layer 1: `racing_engine/race_strength_index.py` reading
`v2_run_performances.race_strength` + `v2_race_pace_shapes` + grade + time-par,
writing an append-only `v2_race_strength_index` table with full component
provenance. Then generalise `collateral_revision_v2` into the Layer 2 franking
pass. Do not expose any output to pricing.
