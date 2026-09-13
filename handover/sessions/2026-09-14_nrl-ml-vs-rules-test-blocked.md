# 2026-09-14 — NRL ML shadow vs rules engine: the test cannot be run, and why

> **Part of a larger session.** The consolidated record covering both days —
> AFL prelims, the model validation and correction, the owner scope direction and
> the NRL rebuild — is [`2026-09-13_14_SESSION-RECORD_afl-prelims-model-validation-nrl-rebuild.md`](2026-09-13_14_SESSION-RECORD_afl-prelims-model-validation-nrl-rebuild.md).


**Ask:** run the AFL-style comparison for NRL — does the ML shadow beat the rules engine on
H2H, handicap and totals?

**Outcome: the head-to-head cannot be answered with existing data.** Not a small gap — the
two prediction series do not overlap on a single game. What *can* be measured is below,
along with the exact unblock.

---

## Why it cannot be run

| Source | What it holds | 2026 coverage |
|---|---|---|
| `results/r*_pricing_2026.csv` | **rules** predictions (T1+tiers) | **R11–R27, 116 games** (25 with actuals filled) |
| `ml/nrl/results/features_nrl.csv` | features the ML needs | **R1–R6 only, 48 games**, stops 2026-04-12 |
| `ml_shadow_predictions` (model.db) | **ML** predictions, deployed | **R24–R25, 16 rows** |
| `MODEL_ACCURACY_RUNNING_2026.csv` | rules v ML v market | **NRL R9–R11 only, 24 games** |

- **Rules R11–R27 and ML features R1–R6 have ZERO overlap.** The ML cannot be scored on any
  game the rules engine priced.
- The 16 deployed shadow rows are the only true head-to-head, and **only 8 have a result in
  the DB** (R25 results were never loaded). Actuals were never backfilled — `baz_learning_review.py`
  already flags this: *"ml_shadow_predictions exist but actual outcomes have not been backfilled"*.
- The 24 games in `MODEL_ACCURACY_RUNNING` are the **old** ML shadow, superseded by the
  premarket model built 2026-08-12. Different model, not comparable.

**Maximum honest head-to-head sample available anywhere: 8 games.**

Contrast with AFL, where the same test ran on 86–95 games: there, rules and ML are written
to **the same per-round CSV** by the same script. NRL's ML was bolted on in August and writes
to a **separate table** that nothing joins back to the rules output.

This is DATA_INTEGRITY_LESSONS #10 — records with holes. The shadow has been "live" since
August and has produced nothing scoreable.

---

## What CAN be measured

### 1. The ML in absolute terms — 426 walk-forward games (2024+2025, trained on prior seasons only)

| Metric | Value |
|---|---:|
| Margin bias | −1.39 |
| Margin MAE | **14.36** |
| Margin RMSE | 18.34 |
| H2H — classifier | 61.0% acc, log loss 0.6553, Brier 0.2316 |
| H2H — margin→prob | 62.7% acc, log loss 0.6559, Brier 0.2313 |

Clean walk-forward, no leakage. This is a competent NRL model in absolute terms.

### 2. The ML vs the market — but only n=65

**Closing-market coverage in the backtest workbook is 65 of 426 games (15%).** Everything
below rests on that 65.

| | bias | MAE | RMSE |
|---|---:|---:|---:|
| ML margin | −1.36 | 14.29 | 17.79 |
| Market close | −2.18 | **14.08** | 17.82 |

Paired |error| ML v market: **+0.21 pts, p=0.760 — indistinguishable.**

| H2H (n=65) | acc | log loss | Brier |
|---|---:|---:|---:|
| ML classifier | 60.0% | 0.6418 | 0.2253 |
| ML margin→prob | **67.7%** | 0.6357 | 0.2228 |
| Market close | 60.0% | **0.6331** | **0.2222** |

**Handicap ATS v closing line: 36–29, 55.4%, ROI +5.78% at $1.91, p=0.457,
bootstrap 95% CI [−17.7%, +29.3%].** Above break-even, nowhere near significant.

### 3. Totals — not tested at all, ever

`train_nrl_ml_shadow.py` **fits** a total model (`ml/models/total_model_v20260812.joblib`)
but the walk-forward evaluates only margin and H2H. `walk_forward_metrics.csv` has no totals
column and the market backtest has no totals market. **There has never been an out-of-sample
evaluation of NRL ML totals.** Given totals is the one market where AFL showed a significant
result, this is the biggest single hole.

---

## One thing that was verified and is worth keeping

**The NRL shadow is pure ML with no tiers applied** — `ml_adj_margin == ml_raw_margin` and
`ml_adj_total == ml_raw_total` on all 16 rows, despite the tier columns being populated and
non-zero (max would-be effect 6.25 pts on margin, 3.9 on totals). That matches the design
note ("rule tiers are diagnostic only and are no longer added to ML") — the code does what
the doc says. **This differs from AFL, where the ML primary gets the full tier stack.** Any
NRL comparison must account for it: the NRL ML is running without help the rules engine has.

---

## Unblock — in order

1. **Backfill R25 NRL results into `model.db`,** then run `scripts/ingest_actuals.py` so the
   16 shadow rows score. Cheap. Gives 16 games — still too few to conclude, but it stops the
   bleeding and clears a blocker `baz_learning_review.py` has been reporting.
2. **Rebuild `features_nrl.csv` for 2026 R7–R27.** The source data is present (`model.db`:
   196 matches, 180 results). ⚠️ **The builder that produced the existing file is not
   findable in the repo** — `ml/nrl/features.py` is only a feature-name contract, and the
   `scripts/build_nrl_free_t2_*` scripts write different files. It needs locating or
   rewriting, with point-in-time care on ELO, venue, referee and weather features
   (DATA_INTEGRITY_LESSONS #5 — filtering by date is not enough if the values embed later data).
3. **Score the production model on R11–R27** and join to the rules pricing CSVs. That yields
   ~116 comparable games, matching the AFL sample size.
4. **Add totals to the walk-forward** so the untested model gets tested.
5. **Fix the market coverage** — 65/426 closing lines. 2026 NRL market data exists in
   `data/odds_snapshots/2026/`, so closing lines can be reconstructed for the 2026 games.
6. **Structural fix: write ML and rules to the same per-round artefact,** the way AFL does.
   The whole problem is that they live in different places and nothing joins them.

Until (2) and (3) are done, **there is no evidence either way on whether the NRL ML beats the
rules engine.** The rules engine remains official — which, given NRL's running CLV of +4.99%
over 58 bets, is not a bad place to be sitting.

---

# REBUILT (2026-09-14) — pipeline built, test now runs, first results

Owner asked for the rebuild so the blend can be tuned for 2027. Done. The test that
was impossible this morning now runs on **92 games**.

## What was built

| File | Purpose |
|---|---|
| `scripts/build_nrl_results_history.py` | **NEW.** Assembles canonical NRL results from the nrl.com draw API, caching raw JSON so re-runs are free. Unmapped team nicknames are a hard error, never a silent pass-through. |
| `scripts/build_nrl_features.py` | **NEW.** Point-in-time feature builder. Uses the old `features_nrl.csv` as the 2009→2026-04-12 spine and extends it, with a validation gate that reproduces the spine. |
| `scripts/score_nrl_ml_vs_rules.py` | **NEW.** Runs the production models, joins to the rules pricing CSVs, reports margin / totals / H2H and the blend-weight curve. |
| `ml/nrl/results/nrl_results_history.csv` | 208 completed 2026 matches, R1–R28, through 2026-09-13. |
| `ml/nrl/results/features_nrl_extended.csv` | **3,629 rows (was 3,469)** — 2026 now complete at 208 games instead of 48. |
| `outputs/results/nrl_ml_vs_rules_2026.csv` | The 92-game joined comparison. |

### The ELO rule was recovered, not guessed

The original builder is not in the repo, so the ELO rule was **recovered by fitting to
the spine's own `elo_diff`**: K=20, no margin multiplier, no home-field term in the
update, 25% regression to 1500 at each season boundary. Grid-searched over K, HFA,
three margin-multiplier forms and reversion.

### Validation gate — the builder reproduces the spine

| Feature | n | mean abs error |
|---|---:|---:|
| `home_travel_km` / `away_travel_km` | 1,089 | **0.000** |
| `home_prev_margin` | 3,323 | **0.000** |
| `home_win_streak` | 3,469 | **0.000** |
| `actual_margin` | 3,469 | **0.000** |
| `venue_avg_total` | 3,281 | 0.018 (rounding) |
| `elo_diff` — all seasons | 3,469 | 2.249 |
| **`elo_diff` — 2025–26 only** | 261 | **0.404** |

0.40 ELO points is about **0.016 points of margin**. Two things were discovered and
fixed during validation rather than assumed:

- **Form and rest reset at each season boundary** (the spine carries `prev_margin` NaN,
  streaks 0 and `rest_days` NaN on every season's first game). ELO carries across with
  reversion; venue stats carry across untouched. Fixing this took `home_win_streak`
  from 74 mismatched rows to zero.
- **Travel is exactly constant per (team, venue)** — 0 of 424 observed pairs disagree —
  so it is looked up from the spine rather than recomputed from coordinates the DB does
  not have (`team_home_bases` is empty, `venues.lat/lng` are NULL).
- **Identity check:** all 46 joinable spine 2026 rows match the API on score exactly.
  The 2 that did not join are the Las Vegas round, dated in US local time by the spine
  and AEST by the API — same fixtures, two calendars. Handled with a ±2-day key.

## FIRST RESULTS — 92 games, R11–R25, 15 May to 23 Aug

⚠️ The ML runs **without tier overlays** (matching how the shadow is actually deployed);
the rules column carries the full T1–T10 stack.

### Margin

| Estimator | bias | MAE | RMSE | sign acc |
|---|---:|---:|---:|---:|
| **Rules (T1–T10)** | +4.37 | 14.29 | **18.39** | **69.6%** |
| ML (no tiers) | +4.22 | 14.51 | 19.80 | 65.2% |
| Blend 25% ML | +4.33 | 14.11 | 18.51 | 68.5% |
| **Blend 40% ML** | — | **14.07** | 18.66 | 68.5% |
| Blend 75% ML | +4.25 | 14.22 | 19.23 | 66.3% |

**Rules beats ML outright on margin.** A light blend shaves MAE (14.29 → 14.07 at 40%
ML) but **p=0.535 — not significant**, and rules alone has the best sign accuracy.

### Totals — this is where the ML earns its place

| Estimator | bias | MAE | RMSE |
|---|---:|---:|---:|
| Rules (T1–T10) | +2.34 | 12.92 | 16.00 |
| ML (no tiers) | −4.04 | 12.22 | 15.13 |
| **Blend 50% ML** | −0.85 | 11.94 | 14.92 |
| **Blend 60% ML** | −1.49 | **11.88** | **14.86** |

**The 50/50 totals blend beats rules by 0.98 pts, p=0.0266 — SIGNIFICANT**, and the only
significant result in the NRL set. The two heads are biased in **opposite** directions
(rules +2.34, ML −4.04) and the blend crosses zero bias at ~37% ML, which is exactly the
mechanism that makes blending work.

**Note this is the inverse of AFL**, where rules totals were significantly *better* than
ML (p=0.014) and blending hurt. The two sports want opposite treatments on totals.

### H2H

| Estimator | acc | log loss | Brier |
|---|---:|---:|---:|
| Rules (sign of margin) | **69.6%** | — | — |
| ML classifier | 60.9% | 0.6604 | 0.2338 |
| ML margin→prob | 65.2% | 0.6479 | 0.2270 |

**Rules wins H2H clearly.** The rules H2H *probability* is not stored in the pricing
CSVs, so log loss cannot be compared — worth adding.

## Answering the owner's guess

> *"maybe next season we will have a blend of 75 rules, 25 ML"*

On this evidence, **75/25 is about right for margin** (14.11 v a 14.07 optimum at 40%),
**too rules-heavy for totals** (optimum 50–60% ML), and **wrong for H2H**, where rules
alone is best. The engine may want a different weight per market rather than one number.

⚠️ **The optimal weights above were chosen by minimising error on the same 92 games, so
they are in-sample.** The honest claim is "blending helps on totals", not "0.6 is the
weight". A held-out season is needed before any weight is fixed.

## Still open

1. **R21, R23 and R27 pricing CSVs have no `final_margin` column** — a schema drift that
   costs ~24 comparable games. Fixing it takes the sample from 92 to ~116.
2. **Store the rules H2H probability** in the pricing CSV so H2H can be scored on log
   loss and Brier, not just sign accuracy.
3. **No market comparison yet** — 2026 NRL closing lines were not assembled, so there is
   no ATS or EV test and no CLV. `data/odds_snapshots/2026/` has the raw material.
4. **Backfill R25 results** into `model.db` and run `ingest_actuals.py` (still outstanding).
5. **Structural fix still wanted:** write rules and ML to the same per-round artefact, as
   AFL does. The scoring script papers over it with a join; the real fix is upstream.
6. Retrain consideration: the production models are trained through 2025 and were fitted
   on the *old* spine. They have not been retrained on the extended table — deliberately,
   so 2026 stays a clean out-of-sample test.

---

# CONCLUSION — leave the rules margin/H2H alone, blend the totals

Owner's read, tested and confirmed. One extra test settled it: **is the totals gain
really from the ML, or just from removing the rules model's +2.34 bias?**

| Totals estimator | bias | MAE | vs rules | p |
|---|---:|---:|---:|---:|
| Rules, as-is | +2.34 | 12.92 | — | — |
| Rules minus its own bias | 0.00 | 12.65 | −0.26 | 0.276 |
| ML, as-is | −4.04 | 12.22 | −0.69 | 0.367 |
| ML minus its own bias | 0.00 | **11.82** | −1.10 | 0.065 |
| **Blend 50/50** | −0.85 | 11.94 | **−0.98** | **0.027** |
| Blend 50/50, debiased | 0.00 | 11.98 | −0.93 | **0.016** |

**Debiasing the rules model alone does NOT capture the gain** — it recovers only a
quarter of it and is not significant. The improvement genuinely requires the ML.

| Margin estimator | bias | MAE | sign acc | vs rules | p |
|---|---:|---:|---:|---:|---:|
| Rules, as-is | +4.37 | 14.29 | **69.6%** | — | — |
| Rules minus its bias | 0.00 | 13.92 | 66.3% | −0.36 | 0.412 |
| Blend 40% ML | +4.31 | 14.07 | 68.5% | −0.22 | 0.441 |

**Nothing helps the margin significantly, and debiasing actively HURTS sign accuracy
(69.6% → 66.3%)** — which is the metric an H2H or line bet actually depends on. Chasing
MAE there would cost the thing that matters.

## The call

1. **Margin and H2H — leave the rules engine exactly as it is.** No blend, no debias.
   It wins outright on sign accuracy and nothing beats it significantly on error.
2. **Totals — blend, at a flat 50/50.** Significant (p=0.027), and 50/50 matters: it is
   a natural, pre-specifiable weight, not the fitted optimum (0.6). Implementing the
   fitted weight would be curve-fitting one season.
3. **Do NOT carry this to AFL.** AFL is the mirror image — rules totals beat ML there
   significantly (p=0.014) and blending hurt, while the margin/H2H/handicap blend was
   the one that helped. **Per-sport, per-market. There is no single house weight.**

## The caveat that limits all of it

**We have shown the blend beats the rules model. We have NOT shown it beats the market.**
No 2026 NRL closing lines were assembled, so there is no ATS, EV or CLV test on totals.
In the AFL work the market beat every model variant on almost every measure — a model
improving on itself is not the same as an edge. **Assemble the closing lines before any
of this is staked.**

Also: n=92, one season, and roughly six paired tests were run — p=0.027 is nominal and
would not survive a strict multiple-comparison correction. The direction is consistent
and mechanistically explainable (the two heads carry opposite biases, +2.34 and −4.04,
which cancel), but this is one season of evidence, not a settled fact.
