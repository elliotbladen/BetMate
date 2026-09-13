# Session record — 13–14 September 2026

**AFL preliminary finals priced · the model validated properly (and one of my own tables
corrected) · owner scope direction for 2027 AFL · NRL ML pipeline rebuilt from scratch**

This is the consolidated record of the whole session. The two working diaries carry the
detail:

- `2026-09-13_afl-prelim-finals-pricing.md` — AFL R27 pricing, the combined model, T2/T6
  work, the correction, the totals test, and the profitability analysis
- `2026-09-14_nrl-ml-vs-rules-test-blocked.md` — the NRL blocker, the rebuild, and the
  conclusion

Round report: `BettingEngine/outputs/results/afl_prelim_finals_pricing_2026.md`

---

## 1. What was asked, in order

1. Price the two AFL preliminary finals; ingest the semi-final scores into the ELO; account
   for Hawthorn and Sydney having had a week off; follow the .py script; process all tiers.
2. Run the combined model (25% rules / 75% ML); refresh the stale inputs off the internet;
   research whether any emotional tier should be priced in; rework.
3. *"you're telling me the opposite"* — challenge to my blend-validation table.
4. Test the totals.
5. *"I would have been profitable if I knew this at the start of the season."*
6. Record that 2027 AFL is a rebuild, **not** a full gut-and-replace.
7. Test whether the NRL ML shadow beats the rules engine.
8. Rebuild the NRL pipeline so that test can run.

---

## 2. AFL preliminary finals — the prices

**PF1 — Sydney v Fremantle · SCG · Fri 18 Sep 19:40**
**PF2 — Hawthorn v Brisbane · MCG · Sat 19 Sep 17:15**

| | Rules | Primary (ML+tiers) | Blend 25/75 | Market (20 books) |
|---|---|---|---|---|
| Syd v Fre | Syd −15.2 | Syd −32.4 | **Syd −28.1** | **Fre −11.5**, total 185.5 |
| Haw v Bri | Haw −7.1 | Haw −8.3 | **Haw −8.0** | **Bri −1.5**, total 184.5 |

Semi results ingested (Fremantle 120 d Geelong 106; Brisbane 144 d Adelaide 91), all 3,568
pre-existing workbook rows verified byte-identical after the append, `features_afl.csv`
rebuilt 1,068 → 1,070. Post-semi ELO pinned as `FINALS_ELO_OVERRIDE[27]`: Sydney 1743.2,
Brisbane 1735.1, Fremantle 1709.4, Hawthorn 1704.9 — validated twice (reproduces the R26
overrides exactly, and matches the independently recorded post-week-1 figures).

### Verdict

- **PF1: no bet, and no usable model price at all.** T5 cannot price a mass absence.
- **PF2: Hawthorn +1.5 @ $2.00 is live** (+13.7% on the bias sensitivity, +24.6% frozen).
- **No totals bet on either.**

---

## 3. The headline AFL finding — T5 cannot price a mass absence

Sydney are missing six of their best 22: **Heeney, Warner, Blakey, Jordon and Bice**, all
club-suspended on 19 Aug for the rest of the season, plus captain **Callum Mills** (ACL in
the QF). T5 reads that as **−12.32 raw, clamped to its ±8.0 cap**. To reach the market it
would need **−34.7**, or **−41.5** on the blend. Short by a factor of four.

The `IMPACT_TABLE` tops out at −5.0 for one elite key forward and the cap exists to stop two
or three outs dominating a price. There is no representation for losing five at once.

**The Championship "absentees are already in the ratings" lesson does not transfer.** That
holds where a rating was fitted with zero appearances from the player. Sydney's 1743 was
built across a full season *with* those players and has been moved by only two games since —
both 53-point wins, which pushed it **up**. So the absence is in neither T5 nor the ELO.

The resulting **+99% EV on Sydney** is the tell. A three-figure edge against 20 books is a
broken input, not a bet. **Blending makes it worse**, moving Sydney from −15.2 to −28.1,
because 75% of the weight lands on the head most blind to the problem: the ML margin
regressor has no injury input at all.

---

## 4. ⚠️ I published a wrong table and the owner caught it

My first blend-validation table said the blend was no better than the rules model. That
contradicted a prior project finding, the owner pushed back, and **they were right.** Three
errors:

1. **Double-counted tiers.** `primary_margin` is stored for only 4 rows, so I reconstructed
   it as `ml_margin + (t2+t3+t4+t5+t6+t8)` — but stored `ml_margin` **already contains t2,
   t5, t6, t8**. A `+1.95` offset fitted from those 4 observations then absorbed most of the
   error, so the reconstruction looked right to ~2 points while being structurally wrong.
   The exact identity is `primary_margin = ml_margin + t3_hcp + t4_hcp`, verified to 0.03.
2. **Scored the wrong model.** I measured the sign of the ML *margin regressor* and called it
   the ML H2H result. The claim is about the separate **H2H classifier** (`ml_h2h`), which I
   never touched. DATA_INTEGRITY_LESSONS #3.
3. **Treated a non-significant bias as established** and applied a −5.70 "correction" as
   though it were a fix.

**Corrected — 86 priced 2026 games:**

| Margin | bias | MAE | RMSE | sign |
|---|---:|---:|---:|---:|
| Rules | +5.30 | 26.75 | 35.01 | 68.6% |
| ML + tiers | +4.61 | 25.19 | 32.49 | **72.1%** |
| **Blend 25/75** | +4.78 | **24.94** | **32.49** | 67.4% |
| Market close | +1.10 | 25.14 | 32.34 | 67.4% |

| Handicap ATS | | H2H | acc | log loss |
|---|---|---|---:|---:|
| Rules **47.7%** (41–45) | | Rules | 68.6% | 0.5920 |
| ML+tiers 52.3% | | ML classifier | 67.4% | 0.5801 |
| **Blend 57.0%** (49–37) | | **Blend** | **69.8%** | **0.5607** |
| break-even 52.4% | | Market | 68.6% | 0.5618 |

**The blend has the lowest margin MAE of anything including the market, the best H2H log
loss and Brier, and the only positive ATS record. The rules model is below break-even on the
spread.** The prior project finding stands; my table had inverted it.

**The lesson, recorded:** a fudge factor fitted to a handful of points masked a structural
error, and the result looked plausible. Validate composition *before* comparing — which is
exactly what I then did for the totals and for the whole NRL rebuild.

---

## 5. AFL totals — rules+tiers wins, significantly

| Totals | bias | MAE | O/U v close |
|---|---:|---:|---:|
| **Rules (T1+tiers)** | −4.95 | **22.36** | **55.8%** (48–38) |
| ML + tiers | −14.70 | 27.87 | 50.0% |
| Blend 25/75 | −12.26 | 25.62 | 51.2% |
| Market close | +0.50 | 21.52 | — |

Paired: rules v ML **better by 5.52 pts, p=0.014**; v blend better by 3.26, p=0.062; **v
market worse by 0.83, p=0.593 — indistinguishable from the market.** Rules is the only
totals estimator above the 52.4% break-even. **Blending hurts on AFL totals** — the inverse
of the margin result, and exactly what the frozen spec already does.

**But this week is still a no-bet.** The rules total normally sits *below* the market (mean
−6.3, p90 +10.8); this week it is +23.7 and +12.2 *above*. Only 9 of 95 games all season went
past +12, and in that bucket the model is right 55.6% (5–4, 95% CI 25–83%). **The 55.8% is
earned almost entirely on the Under side.** Magnitude says +52% EV; track record says +5.6%.
Trust the track record.

---

## 6. "Would I have been profitable knowing this in March?"

Tested. **Probably not dramatically — and the leak was the selection filter, not the model.**

| Strategy (flat, $1.91) | record | ROI | 95% CI |
|---|---:|---:|---|
| Handicap, blend, vs open | 48–38 | +6.60% | [−13.4%, +26.6%] |
| Totals, rules, vs open | 56–39 | **+12.59%** | [−7.5%, +30.7%] |

Edges survive at the **opening** line — the price actually available. But every interval
spans zero, and proving them needs ~350 bets (totals) to ~1,290 (handicap): **2–6 seasons.**

**The actual 2026 AFL ledger already agreed:** 55 bets, −$9.90, ROI −0.57% — h2h **−27.5%**,
handicap **−13.1%**, **totals +37.9% (+$209)**. The one market that made money is the one
market with a significant edge. Two independent lines of evidence, same answer.

**The filter is anti-selective.** "Only bet when the model disagrees by ≥ X":

| Threshold | Handicap ROI | Totals ROI |
|---|---:|---:|
| ≥0 (bet everything) | **+6.6%** | **+12.6%** |
| ≥10 | **+2.5%** | **+3.1%** |

Filtering to the biggest disagreements does not help and on handicap it hurts. The EV≥10%
gate selects the games where the model most disagrees with the market — no extra edge, far
more model risk. **PF1 is the perfect illustration:** the biggest disagreement of the season
is a broken input. Of 25 settled h2h/handicap bets matched to a priced game, **21 agreed with
the blend's direction and still returned −23.0%.**

**Implications:** the edge is in breadth not selectivity — more games, smaller, filter less;
totals is the proven market; h2h is the worst and should shrink or stop.

---

## 7. OWNER DIRECTION — 2027 AFL is a targeted rebuild

> *"next season's AFL is not a huge rebuild. Rebuild yes. But not full gut and replace."*

**KEEP** (measured, do not redesign): the hybrid split itself (margin/H2H/handicap → blend,
totals → rules), the T1–T9 tier stack, the 25/75 weights (**do not re-fit on one season**),
the Monte Carlo machinery, the data pipeline and the finals ELO-override pattern.

**REBUILD, short list:** (1) T5's mass-absence failure — top priority; (2) the anti-selective
EV≥10% staking filter; (3) the h2h book; (4) a testable T6 siege-mentality flag type; (5) the
Monte Carlo totals widening off the weaker ML head; (6) understand why rules is below
break-even ATS while being the best totals estimator.

**Nothing measured said the model is wrong in structure. One tier fails in an edge case, and
the staking layer loses more than the model wins.** Recorded in both CLAUDE.md backlogs.

---

## 8. NRL — the test was impossible, so the pipeline was rebuilt

### The blocker

Rules pricing covered R11–R27; the ML's feature file covered R1–R6 and stopped 2026-04-12.
**Zero overlap.** The 16 deployed shadow rows were the only true head-to-head and only 8 had
a result. **Maximum honest sample anywhere: 8 games.** Root cause: AFL writes rules and ML to
the *same* per-round CSV; NRL's ML was bolted on in August and writes to a separate table
nothing joins back.

### The rebuild

| File | Purpose |
|---|---|
| `scripts/build_nrl_results_history.py` | Canonical results from the nrl.com draw API, raw JSON cached; unmapped nicknames are a hard error |
| `scripts/build_nrl_features.py` | Point-in-time feature builder with a validation gate |
| `scripts/score_nrl_ml_vs_rules.py` | Runs the models, joins to rules pricing, reports the blend curve |

2026 went from **48 games to 208**. Feature table 3,469 → **3,629 rows**.

**The ELO rule was recovered, not guessed** — fitted to the spine's own `elo_diff` by grid
search: K=20, no margin multiplier, 25% season reversion.

**Validation gate:** travel, `prev_margin`, `win_streak` and `actual_margin` all reproduce at
**0.000**; `elo_diff` at **0.404 across 2025–26** (≈0.016 pts of margin). Three things found
rather than assumed: form and rest **reset** at each season boundary (fixing it took
win_streak from 74 mismatches to zero); travel is exactly constant per (team, venue), 0 of
424 pairs disagreeing, so it is looked up rather than recomputed from coordinates the DB does
not have; and the Las Vegas round is dated US-local by the spine and AEST by the API — same
fixtures, handled with a ±2-day key.

### Results — 92 games, R11–R25

ML runs **without tiers** (as deployed); rules carries the full T1–T10 stack.

| Margin | bias | MAE | sign | | Totals | bias | MAE |
|---|---:|---:|---:|---|---|---:|---:|
| **Rules** | +4.37 | 14.29 | **69.6%** | | Rules | +2.34 | 12.92 |
| ML | +4.22 | 14.51 | 65.2% | | ML | −4.04 | 12.22 |
| Blend 40% ML | — | 14.07 | 68.5% | | **Blend 50/50** | −0.85 | **11.94** |

H2H: rules 69.6% v ML classifier 60.9% / margin→prob 65.2%.

### The conclusion

**Debiasing the rules totals alone does not capture the gain** (−0.26, p=0.276) — it needs
the ML. And on margin, debiasing **hurts sign accuracy** (69.6% → 66.3%), the metric an H2H
or line bet depends on.

1. **Margin and H2H — leave the rules engine exactly as it is.** No blend, no debias.
2. **Totals — blend at a flat 50/50.** p=0.027, and 50/50 is a pre-specifiable weight, not
   the fitted optimum (0.6); implementing the fitted number would be curve-fitting.
3. **Do not carry this to AFL.** AFL is the mirror image. **Per-sport, per-market — there is
   no single house weight.**

⚠️ **We have shown the blend beats the rules model, NOT that it beats the market.** No 2026
NRL closing lines were assembled. In the AFL work the market beat every model variant on
almost every measure. **Assemble the closing lines before staking any of this.**

---

## 9. Faults found and fixed

1. `_export_afl_prices.py` crashed on `sqlite3.Row.get()` — `Row` has no `.get`.
2. **T7 printed a hardcoded `[tomorrow_io]`** whatever the real source. Every AFL run since
   the API key went missing printed "key not found" then claimed Tomorrow.io one line later
   while silently using open-meteo. Another green light over a dead component.
3. **afl.com.au returned the Hawthorn and Geelong injury blocks transposed.** The local
   scraper was right and the cross-check was wrong — confirmed a second way before acting.
4. **`monte_carlo_afl_finals.py` could not run at all** — hardcoded to a deleted market file.
   Now takes `--markets`, `--out`, `--home-bias`.
5. My own blend-validation table (§4) — the most consequential of the five.

---

## 10. Open

**AFL:** raise or override the T5 cap for 4+ outs (PF1 stays unpriceable otherwise); Thursday
team lists (McInerney/Amartey, Darcy/Walker/Cox, Scrimshaw/Reeves, Answerth); the ML H2H
classifier disagrees badly with the ML margin head; T2 refreshed but structurally cannot see
the Sydney problem (season aggregate, 22 of 24 games with the banned five).

**NRL:** R21/R23/R27 pricing CSVs have no `final_margin` (schema drift costing ~24 games,
92 → ~116); store the rules H2H probability so H2H can be scored on log loss; **assemble 2026
closing lines for the market/ATS/EV/CLV layer**; backfill R25 results and run
`ingest_actuals.py`; write rules and ML to the same per-round artefact.

**Both:** n is small everywhere — 55 real AFL bets, 86–95 AFL priced games, 92 NRL. Only two
results in the entire session reach significance (AFL totals rules-v-ML p=0.014; NRL totals
blend-v-rules p=0.027). **Do not rebuild anything on one season alone.**

---

## 11. Files changed

**New:** `scripts/build_nrl_results_history.py`, `scripts/build_nrl_features.py`,
`scripts/score_nrl_ml_vs_rules.py`, `ml/nrl/results/nrl_results_history.csv`,
`ml/nrl/results/features_nrl_extended.csv`, `outputs/results/nrl_ml_vs_rules_2026.csv`,
`outputs/results/afl_prelim_finals_pricing_2026.md`, `outputs/afl_round_prep/r27_2026/`,
`results/r27_afl_2026.csv`, `outputs/monte_carlo/afl_prelim_finals_2026_100k*.csv`,
`data/odds_snapshots/2026/2026-09-13_afl_prelim_finals_best.csv`, three handover diaries.

**Modified:** `scripts/prepare_afl_round.py` (R27 ELO override, T7 source label),
`scripts/_export_afl_prices.py` (Row.get fix), `scripts/monte_carlo_afl_finals.py`
(parameterised), `ml/afl/results/features_afl.csv`, `outputs/afl_weekly_review/historical/latest.xlsx`,
`data/footywire_snapshots.csv`, `CLAUDE.md`, `BettingEngine/CLAUDE.md`.

**Tests:** 244 pass, 3 pre-existing failures (2 NFL/fastparquet, 1 AFL round-detection test
that hardcodes a round number and goes stale weekly).
