# 2026-09-13 — AFL Preliminary Finals priced (R27)

> **Part of a larger session.** The consolidated record covering both days —
> AFL prelims, the model validation and correction, the owner scope direction and
> the NRL rebuild — is [`2026-09-13_14_SESSION-RECORD_afl-prelims-model-validation-nrl-rebuild.md`](2026-09-13_14_SESSION-RECORD_afl-prelims-model-validation-nrl-rebuild.md).


**Ask:** mini price-up of next week's two prelims; ingest yesterday's scores into the ELO;
account for Hawthorn and Sydney having had a week off; follow the .py script; process all
tiers.

**Outcome: both games priced, all tiers processed, NO BET on either — and PF1 turns out not
to be priceable by this model at all.**

Full report: `BettingEngine/outputs/results/afl_prelim_finals_pricing_2026.md`
Prices: `BettingEngine/results/r27_afl_2026.csv` (+ `model.db`, T9 shadow rows)

---

## What was done

1. **Semi results ingested.** Fremantle 120 d Geelong 106; Brisbane 144 d Adelaide 91
   (Squiggle API, goals×6+behinds reconciled). Appended to `latest.xlsx`; **all 3,568
   pre-existing rows verified byte-identical** after the rewrite. Pre-append copy survives
   as `afl_20260908_094856.xlsx`, augmented copy as `latest_with_finals_wk2.xlsx`.
2. **ELO rebuilt** — `features_afl.csv` 1,068 → 1,070 rows. Post-semi ratings walked forward
   with `game_log.update_elo` and pinned as `FINALS_ELO_OVERRIDE[27]`:
   Sydney **1743.2**, Brisbane **1735.1**, Fremantle **1709.4**, Hawthorn **1704.9**.
   Method validated two ways — it reproduces the R26 overrides exactly, and Hawthorn/Sydney
   match the post-week-1 figures recorded independently in the semis report.
3. **Round prep built** at `outputs/afl_round_prep/r27_2026/` — fixture, hand-curated
   injuries (2 sources), and an explicit-zero emotional file with the rejected flags and
   reasons written down.
4. **Priced** via `scripts/prepare_afl_round.py --season 2026 --round 27`, exported, and
   `afl_matrix_confluence.py` run for T9.

## Prices

| Game | Rules | Primary (ML+tiers) | Market (20 books) |
|---|---|---|---|
| **Sydney v Fremantle** · SCG · Fri 18 Sep | Syd −15.2, 208.9 | Syd −32.4, 208.9 | **Fre −11.5**, 185.5 |
| **Hawthorn v Brisbane** · MCG · Sat 19 Sep | Haw −6.7, 196.6 | Haw −7.8, 196.6 | **Bri −1.5**, 184.5 |

## The finding — T5 cannot price a mass absence

Sydney are missing six of their best 22: **Heeney, Warner, Blakey, Jordon and Bice**
(club-suspended 19 Aug for the rest of the season) plus captain **Callum Mills** (ACL, late
Q1 of the QF on 5 Sep). T5 reads that as **−12.32** raw, **clamped to its ±8.0 cap**. To
reach the market, T5 would need **−34.7** (rules) or **−51.9** (primary). Short by 4×.

The `IMPACT_TABLE` maxes at −5.0 for one elite key forward and the cap exists to stop two or
three outs dominating a price. There is no representation for losing five players at once.

**The Championship "already in the ratings" lesson does not apply here** — that holds where
the rating was fitted with zero appearances from the player. Sydney's 1743 was built across
a full season *with* those players and has been moved by only two games since, both 53-pt
wins, which pushed it **up**. So the absence is neither in T5 nor in the ELO. The resulting
**+71% / +110% EV on Sydney** is the tell: a three-figure edge against 20 books is a broken
input, not a bet.

The counter-evidence is real and recorded: this depleted list beat full-strength Brisbane by
53 in the QF. But Sydney −32.4 is not that argument — it is a rating that still contains the
missing players.

## PF2 is the honest no-bet

Rules has Hawthorn +6.7 v market −1.5. Strip the model's **own measured +5.62 home bias**
(95 priced 2026 games) and it is **+1.1 v −1.5** — a 2.6-pt gap, **+8.5% EV**, under the 10%
gate, and squarely the "rules and ML both above the market on the home side" pattern already
tested at 4–8 ATS. T9's 6-way confluence for Hawthorn is partly one fact counted twice
(three cells are `vs Brisbane` / `vs Hawthorn` H2H history).

## Week off — a boundary artefact worth knowing

Hawthorn 16 days → `bye` → **+1.5**. Sydney 13 days → `long` → **+1.0**. Same structural
week off, different credit, purely because Sydney's prelim is Friday and Hawthorn's is
Saturday: `_classify_rest` sets the `bye` band at *>13* days. Worth 0.5 pts, decides nothing
here, but **a Friday host will always be scored a notch below a Saturday host after an
identical bye.**

## Model scored — the market is still better

95 priced 2026 games with results:

| | bias | MAE |
|---|---:|---:|
| Market close — total | +0.49 | **21.53** |
| Rules — total | **−5.81** | 22.52 |
| Market close — margin | +1.17 | **24.68** |
| Rules — margin | **+5.62** | 25.94 |

The market beats the model on both markets on both measures. That is why a big
model-vs-market gap reads as the model being wrong.

Last week's semis: market closest on the Freo margin, ML closest on the Brisbane margin,
**rules closest on both totals** (actuals 226 and 235 v market 178.5 / 182.5).

## Three faults found and fixed

1. **`_export_afl_prices.py` crashed** on `sqlite3.Row.get()` — `Row` has no `.get`. CSV was
   already written, but the console summary never printed. Fixed.
2. **T7 printed a hardcoded `[tomorrow_io]` label** whatever the real source. Every AFL run
   since the Tomorrow.io key went missing has printed `TOMORROW_API_KEY not found` and then
   claimed `[tomorrow_io]` one line later while silently using open-meteo. The stored
   `weather_source` column was always correct — only the display lied. Now prints the real
   `data_source`. *(Another green light over a dead component.)*
3. **afl.com.au's injury list came back with the Hawthorn and Geelong blocks transposed** —
   Worpel/Stanley/Conway/Barker listed under Hawthorn (all Geelong), Nash/Reeves/Scrimshaw/
   Anderson under Geelong (all Hawthorn). **The local scraper was right and the cross-check
   was wrong** — confirmed a second way before acting on it.

## Tier coverage

8 of 9 genuinely populated. T6 is a reasoned explicit zero (the Sydney `club_drama` flag was
considered and rejected as a double-count of T5, with the reasoning written into the prep
file). **T2 is stale — R23 snapshot, 4 rounds behind.**

## Next

1. **Raise or override the T5 cap for 4+ outs**, or PF1 stays unpriceable.
2. `scripts/scrape_footywire_round_snapshot.py` — T2 is 4 rounds old.
3. Team lists land Thursday: McInerney, Amartey (Syd); Darcy, Walker, Cox (Fre) all unresolved.
4. The ML H2H classifier and ML margin head disagree badly on PF2 (74.5% v a raw +3.0 line);
   the ML totals head reads 163.0 / 146.8 against rules 208.9 / 196.6 — a ~48-pt internal
   split with the market sitting between them.

---

# Addendum — combined 25/75 model, T2 refresh, T6 research

**Ask:** run the combined model (25% rules / 75% ML), refresh the stale inputs off the
internet, research whether any emotional tier should be priced in, then rework.

## 1. T2 refreshed off Footywire

`scripts/scrape_footywire_round_snapshot.py --season 2026 --round 27` — 18 teams, now
24–25 games each including finals (was R23 / 22 games). Effect on the prices was small:
PF1 T2 was **already at its +4.0 cap** so it could not move; PF2 went −0.2 → +0.3. Rules
margin PF2 6.7 → **7.1**, primary 7.8 → **8.3**, PF1 unchanged at 15.2 / 32.4.

⚠️ **The refresh does not fix the Sydney blind spot and structurally cannot.** The snapshot
is a *season aggregate* and 22 of Sydney's 24 games were played with the banned five —
their contested-possession rating moved 138.6 → 138.9, i.e. it still describes a
full-strength Sydney and reinforces the same error.

## 2. T6 researched — six angles found, all rejected, still zero

Full reasoning in `outputs/afl_round_prep/r27_2026/emotional_r27_2026.json`.

| Team | Angle | Verdict |
|---|---|---|
| Sydney | five-player season ban (19 Aug) | rejected twice — double-counts T5 (at its cap), and the direction is contradicted: two 53-pt wins since, Cox said being written off motivated them |
| Sydney | McInerney + Amartey fit to return | rejected — T5 already has both as available, so the baseline plays them |
| Sydney | written-off / siege mentality | **unpriceable — no such flag type exists**; `shame_blowout` needs a heavy defeat and they won by 53 |
| Fremantle | first prelim since 2015; Longmuir claiming underdog status | rejected — symmetric; no drought/occasion flag (T3's 3E is ANZAC-only) |
| Hawthorn | first prelim since the 2015 flag | rejected — and it cancels: *both* prelims are a first-since-2015 return for the home side |
| Brisbane | three-peat chase; Fagan questioned mentality after the 53-pt QF loss | rejected — **already spent**, they answered with a 144–91 semi win the ELO has absorbed |

No retirements/farewells at any of the four clubs (Tex Walker — Adelaide; Liberatore —
Bulldogs, both eliminated). No milestones found, but treat that as "not found" — there is no
reliable milestone feed for finals week.

**The biggest emotional story of the round — Sydney's siege mentality — has no
representation in T6 at all, and it points opposite to the market.**

## 3. The combined model (25% rules / 75% ML)

`monte_carlo_afl_finals.py --round 27 --sims 100000 --seed 20260913`, bootstrapped 2025
out-of-sample residuals (n=216), disagreement-widened, Thursday selection risk simulated.
**The spec is 25/75 on margin only — totals are rules-only and H2H is derived from the
simulated margin.**

| | Blend margin | Home | Fair | Market | EV | Line cover | Over |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Syd v Fre** frozen | Syd −28.1 | 77.2% | $1.30 | $2.58 | +99.2% | 85.4% (+62.3%) | 74.0% (+40.7%) |
| **Syd v Fre** bias-adj | Syd −22.4 | 72.5% | $1.38 | $2.58 | +87.0% | 81.7% (+55.3%) | 74.0% (+40.7%) |
| **Haw v Bri** frozen | Haw −8.0 | 60.8% | $1.65 | $2.12 | +28.9% | 62.3% (+24.6%) | 63.4% (+20.5%) |
| **Haw v Bri** bias-adj | Haw −2.3 | 53.2% | $1.88 | $2.12 | **+12.8%** | 55.6% (+11.3%) | 63.4% (+20.5%) |

⚠️ **The blend makes PF1 worse.** It moves Sydney from −15.2 to −28.1 because 75% of the
weight goes on the head that is *most* blind to the missing six — the ML margin regressor
takes ELO/EMA/opp-adjusted form and has **no injury input at all**. T5 is added on top of a
full-strength-Sydney baseline. Blending amplifies an input fault, it cannot fix one.
Implied T5 needed to reach the market on the blend: **−41.5**.

## 4. Is the blend actually better? Measured on 95 priced 2026 games

| Margin estimator | bias | MAE | RMSE | sign acc |
|---|---:|---:|---:|---:|
| Rules (T1+tiers) | +5.62 | 25.94 | 34.13 | **69.5%** |
| ML head + tiers | +5.83 | 26.03 | 34.34 | 67.4% |
| **BLEND 25/75** | **+5.70** | **25.73** | **33.84** | 66.3% |
| Market close | **+1.17** | **24.68** | **31.68** | **69.5%** |

**The blend is the best of the three models on MAE and RMSE — so the spec is justified — but
by 0.2 pts, and its sign accuracy is the worst of the four.** That matters because an H2H bet
is a bet on the sign. The market still wins on every measure.

Where the +5.70 comes from: the *raw* ML margin head is biased the other way (−4.00 on 215
unseen 2026 games; −2.55 on the 2025 holdout), so the two baselines partly cancel — but the
T2–T8 stack is itself strongly home-weighted (T3 travel, T4 fortress) and pushes the finished
blend back to +5.70.

## 5. What changed in the read

**PF1 — unchanged, still no bet.** The blend moves it further from the market, not closer.

**PF2 — this is the one that moved.** Rules alone was +9.6% after bias correction (under the
gate). The blend gives **+12.8%** (over it). Genuinely marginal:
- *For:* best model on MAE/RMSE; rules and ML agree on direction (alignment rule satisfied);
  ML H2H classifier independently 74.5%; T9 6-way handicap confluence; Hawthorn have the
  full 16-day bye v Brisbane's 7 days plus travel.
- *Against:* the blend's sign accuracy is its **weakest** attribute and the market beats it
  on all four measures; the whole shape is the documented 4–8 ATS pattern; three of T9's six
  cells are the same H2H fact twice; and the edge exists only because of the −5.70
  correction (uncorrected it reads +28.9%, which is not credible).
- *Read:* if taken at all, **Hawthorn +1.5 at $2.00 (+11.3%)** rather than the H2H, small,
  and only after Thursday's teams.

## 6. Fourth fault fixed

`monte_carlo_afl_finals.py` **could not run at all** — its market snapshot path was hardcoded
to `2026-09-02_afl_finals_week2_sportsbet.csv`, deleted since, and the output filename was
hardcoded too. Now takes `--markets`, `--out` and `--home-bias` (default 0.0 so the frozen
spec is untouched), with R27 `UNCERTAIN_AVAILABILITY` added. Market file built at
`data/odds_snapshots/2026/2026-09-13_afl_prelim_finals_best.csv` (best of 20 books, exchange
lay quotes excluded).

## 7. Still open

- T5 cannot price a mass absence — PF1 stays unpriceable until the cap is addressed.
- T6 has no siege-mentality flag type; adding one needs a testable definition and a backtest.
- The blend's sign accuracy needs explaining before it is used for H2H rather than handicap.
- Thursday teams: McInerney/Amartey (Syd), Darcy/Walker/Cox (Fre), Scrimshaw/Reeves (Haw),
  Answerth (Bri).

---

# Correction — the blend validation table was wrong

The user challenged the §8b table, saying they had previously been told the blend beats
rules on H2H and handicap. **They were right and the table was wrong. Two separate errors.**

## Error 1 — double-counted tiers in the reconstruction

`primary_margin` is only stored for 4 rows, so the season-long comparison reconstructed it as
`ml_margin + (t2+t3+t4+t5+t6+t8)`. But the stored `ml_margin` **already contains t2, t5, t6
and t8** (`prepare_afl_round.py:2312`). Those four tiers were added twice.

A `+1.95` offset fitted from those 4 observations then absorbed most of the resulting error,
so the reconstruction looked right to within ~2 pts. Classic DATA_INTEGRITY_LESSONS shape:
**a fudge factor fitted to a handful of points masked a structural error.**

Exact identity, verified to 0.03 pts on every row where the stored value exists:
`primary_margin = ml_margin + t3_hcp + t4_hcp`.

## Error 2 — scored the wrong model for the H2H claim

The table scored the **sign of the ML margin regressor** and called it the ML H2H result.
The project's "ML wins H2H" finding is about the separate **H2H classifier** (`ml_h2h`,
stored for 101 games), which the table never touched. DATA_INTEGRITY_LESSONS #3 — gating a
thing on a metric for a different thing.

## Corrected results (n=86 priced 2026 games, exact series)

**Margin**

| Estimator | bias | MAE | RMSE | sign acc |
|---|---:|---:|---:|---:|
| Rules (T1+tiers) | +5.30 | 26.75 | 35.01 | 68.6% |
| ML + tiers | +4.61 | 25.19 | 32.49 | **72.1%** |
| **Blend 25/75** | +4.78 | **24.94** | **32.49** | 67.4% |
| Market close | **+1.10** | 25.14 | 32.34 | 67.4% |

**Handicap — picked the side that covered the closing line**

| Estimator | ATS | record |
|---|---:|---:|
| Rules | **47.7%** | 41–45 |
| ML + tiers | 52.3% | 45–41 |
| **Blend 25/75** | **57.0%** | **49–37** |

**H2H — probabilities scored properly (using the classifier)**

| Estimator | acc | log loss | Brier |
|---|---:|---:|---:|
| Rules | 68.6% | 0.5920 | 0.2059 |
| ML H2H classifier | 67.4% | 0.5801 | 0.2017 |
| **Blend 25/75** | **69.8%** | **0.5607** | **0.1931** |
| Market close | 68.6% | 0.5618 | 0.1933 |

**The blend has the lowest margin MAE of anything including the market, the best log loss and
Brier on H2H, and the only positive ATS record. The rules model is below the 52.4%
break-even on the spread.** The prior project finding stands and my table had inverted it.

## Error 3 — treated a non-significant bias as established

Home bias is **not significant for any estimator** at n=86 (SE ±3.5 pts): rules +5.30
(CI −2.05/+12.66), blend +4.78 (−2.05/+11.62), market +1.10 (−5.77/+7.98). Applying a −5.70
"correction" as though it were a fix was an overreach. The frozen spec is now the primary
read and the bias-adjusted run is a sensitivity.

Nor is the blend's advantage significant: blend v rules paired abs error p=0.106, blend v
market p=0.866, ATS v 50% p=0.235. **Directionally consistent across three separate measures,
statistically thin on each.**

## What changed in the output

**The R27 prices themselves never changed** — the Monte Carlo uses stored `rules_margin` and
`primary_margin` for R27, not the reconstruction. Only the validation table and the bias
figure were wrong.

Re-run with the corrected bias (4.78 instead of 5.70):

| | Frozen spec | Bias sensitivity (−4.78) |
|---|---|---|
| Syd v Fre | Syd −28.1, EV +99.2% | Syd −23.3, EV +89.0% |
| Haw v Bri | Haw −8.0, **EV +28.9%** | Haw −3.2, **EV +16.1%** |

**PF2 verdict upgraded from "marginal" to a live selection.** Hawthorn clears the 10% gate on
both runs, and the estimator behind it is the only one with a positive ATS record. The old
"both heads above the market on the home side = 4–8 ATS" caution was measured on the *rules*
model — the one that is actually below break-even — so it is weaker evidence against a blend
selection than it looked. Preferred expression: **Hawthorn +1.5 @ $2.00**, small, after
Thursday's teams.

**PF1 unchanged: no bet.** Nothing in this correction touches the T5 cap fault.

## New finding worth its own look

**The rules model is below break-even ATS in 2026 (47.7%, 41–45).** It is still the primary
for totals and the audit line for everything else.

---

# Totals test — the user was right again

**Ask:** test totals; the recollection was that rules+tiers is the best, close to the market,
and beats ML and the blend. **Confirmed on all three counts, and this is the only result in
the whole session that reaches statistical significance.**

Series validated first this time (after the margin reconstruction error): `ml_total` =
`ml_total_raw` + bias + (t2,t5,t6,t7,t8), residual a per-round constant with sd 0.03;
`rules_total` = `t1_total` + all seven tier totals, exact on 110/112 rows; `primary_total` ==
`rules_total` on every stored row.

## Accuracy — 86 priced 2026 games

| Estimator | bias | MAE | RMSE |
|---|---:|---:|---:|
| **Rules (T1+tiers)** | −4.95 | **22.36** | **28.38** |
| ML + tiers | −14.70 | 27.87 | 37.18 |
| Blend 25/75 | −12.26 | 25.62 | 33.70 |
| Market close | **+0.50** | 21.52 | 27.96 |

## O/U against the closing line

| Estimator | acc | record | picks Over |
|---|---:|---:|---:|
| **Rules** | **55.8%** | **48–38** | 39.5% |
| ML + tiers | 50.0% | 43–43 | 19.8% |
| Blend 25/75 | 51.2% | 44–42 | 16.3% |

Break-even $1.91 = 52.4%. **Rules is the only totals estimator above it.**

## Significance — the one test that lands

| Comparison | difference | p |
|---|---:|---:|
| Rules v ML+tiers | rules better by **5.52 pts** | **0.014** |
| Rules v blend | rules better by 3.26 pts | 0.062 |
| Rules v market | rules worse by 0.83 pts | 0.593 |

**Rules+tiers is significantly better than ML on totals, better than the blend, and
statistically indistinguishable from the market.** Blending *hurts* on totals — the exact
inverse of the margin result. The frozen spec's "rules-only for totals" is now backed by a
significant test rather than an assertion.

Removing the −4.95 low bias: O/U 56.8% → 57.9%, and it fixes the Under skew (picks Over
37.9% → 47.4% v an actual 44.2%). Coherent, not significant.

## Why this week is still a no-bet on totals

**The readings sit outside the range the model has ever been right in.** The rules total
normally sits *below* the market — mean −6.3, median −7.3, p90 +10.8. This week it is
**+23.7 (PF1)** and **+12.2 (PF2)** *above*. Only 9 of 95 games all season went beyond +12.

| Rules − market | n | model right |
|---|---:|---:|
| −99 to −20 | 18 | 61.1% |
| −20 to −10 | 24 | 58.3% |
| −10 to −5 | 8 | 75.0% |
| −5 to 0 | 9 | 44.4% |
| 0 to +5 | 13 | 53.8% |
| +5 to +12 | 14 | 50.0% |
| **+12 and above** | **9** | **55.6%** |

**The 55.8% is earned almost entirely on the Under side.** On the Over side — where it is
this week — it is a coin flip.

Magnitude v track record, and they disagree by a factor of ten:

| | PF1 P(Over) | EV @$1.90 | PF2 P(Over) | EV @$1.90 |
|---|---:|---:|---:|---:|
| Magnitude, empirical RMSE 28.4 | 79.8% | +51.7% | 66.6% | +26.6% |
| Magnitude, bias-corrected | 84.4% | +60.3% | 72.7% | +38.2% |
| **Track record, edge >+12** | **55.6%** | **+5.6%** | **55.6%** | **+5.6%** |

That 55.6% is 5–4 from nine games, 95% CI **25% to 83%**. **Trust the track record over the
magnitude** — a big number is not evidence when the error distribution is 28 points wide.

Also: **PF1's Over is contaminated by the same fault as its margin** — the rules total is fed
by team scoring rates, and Sydney's include 141 and 123 from a side that no longer exists.

## New issue found

**The Monte Carlo widens totals uncertainty using the rules-v-ML gap** (45.9 / 49.8 pts),
which is why it reports 74.0% / 63.4% instead of the ~80% / ~67% the point estimate implies.
ML totals are now measured as significantly worse, so widening on that head's disagreement is
inflating uncertainty from the weaker estimator. Needs revisiting; here it happens to push
toward caution.

## Where the three tests leave the engine

| | best estimator | v market |
|---|---|---|
| Margin | Blend 25/75 (MAE 24.94) | level/ahead |
| Handicap ATS | Blend 25/75 (57.0%) | above break-even |
| H2H probs | Blend 25/75 (LL 0.5607) | ahead |
| **Totals** | **Rules+tiers (MAE 22.36, 55.8% O/U)** | level, only one above break-even |

**Margin/H2H/handicap → blend. Totals → rules. That is exactly what the engine already does,
and it is now measured rather than assumed.**

**Round verdict unchanged: no bet on PF1 (any market), Hawthorn +1.5 @ $2.00 live in PF2, no
totals bet on either.**

---

# "Would I have been profitable knowing this at the start of the season?"

Tested rather than assumed. **Short answer: probably not dramatically — and the thing that
cost money was not the model, it was the selection filter.**

## What betting every game would have returned (flat stakes, $1.91)

| Strategy | n | record | hit | ROI | 95% CI (bootstrap) |
|---|---:|---:|---:|---:|---|
| Handicap, blend, **vs closing line** | 86 | 49–37 | 57.0% | +8.83% | [−11.2%, +28.8%] |
| Handicap, blend, **vs opening line** | 86 | 48–38 | 55.8% | +6.60% | [−13.4%, +26.6%] |
| Totals, rules+tiers, **vs closing** | 95 | 54–41 | 56.8% | +8.57% | [−9.5%, +26.7%] |
| Totals, rules+tiers, **vs opening** | 95 | 56–39 | 58.9% | **+12.59%** | [−7.5%, +30.7%] |

The edges survive at the opening line — which matters, because that is the price actually
available. Totals improve at the open.

**But every interval spans zero comfortably.** Power to distinguish these from break-even:
~350 bets for the totals edge, ~700 for the handicap edge vs the close, ~1,300 vs the open.
An AFL season is ~207 games. **That is 2–6 seasons of betting every game.**

These are genuine walk-forward numbers — the CSVs were written at pricing time each week,
before results — but the engine changed mid-season (T5 table revised 2026-06-10,
`POINTS_PER_ELO`, `T2_MAX`, AFL ML retrained), so the series is not one constant model.

## The actual 2026 AFL ledger — and it already agrees

55 settled bets, $1,733 staked, **−$9.90, ROI −0.57%**.

| Market | n | staked | P&L | ROI |
|---|---:|---:|---:|---:|
| h2h | 16 | $448.63 | −$123.35 | **−27.5%** |
| handicap | 24 | $733.05 | −$95.82 | **−13.1%** |
| **totals** | 15 | $551.45 | **+$209.27** | **+37.9%** |

**The one market that made money is the one market the measurement says the engine has a
significant edge in.** Two independent lines of evidence — a season of real staked bets, and
a paired significance test on 86 priced games — landing on the same answer. That is the most
solid thing to come out of today.

## The real leak: the selection filter is anti-selective

"Only bet when the model disagrees with the market by at least X":

| Threshold | Handicap n / hit / ROI | Totals n / hit / ROI |
|---|---|---|
| ≥ 0 (bet everything) | 86 / 55.8% / **+6.6%** | 95 / 58.9% / **+12.6%** |
| ≥ 5 | 65 / 55.4% / +5.8% | 76 / 59.2% / +13.1% |
| ≥ 8 | 51 / 54.9% / +4.9% | 61 / 57.4% / +9.6% |
| ≥ 10 | 41 / 53.7% / **+2.5%** | 50 / 54.0% / **+3.1%** |
| ≥ 15 | 20 / 55.0% / +5.1% | 33 / 57.6% / +10.0% |

**Filtering to the biggest disagreements does not improve returns — on handicap it degrades
them.** The EV≥10% gate selects precisely for the games where the model most disagrees with
the market, and those carry no extra edge and far more model risk. **PF1 this week is the
perfect illustration**: the biggest disagreement of the season (+44 pts) is a broken input,
not an opportunity. Same shape as the totals bucket analysis in §8a, where the >+12 bucket
hits only 55.6%.

Of the 25 settled h2h/handicap bets that matched a priced game, **21 agreed with the blend's
direction and still returned −23.0%**. The direction was not the problem.

## What this actually implies

1. **The edge is in breadth, not selectivity.** Bet more games, smaller, filter less.
2. **Totals is the proven market.** It is where the significance is (p=0.014 v ML,
   indistinguishable from the market) and where the real money was made (+37.9%).
3. **h2h is the worst market** (−27.5% real, and the blend's weakest metric is sign accuracy).
   Shrink or stop it.
4. Nothing here is established at n=55–95. Two more seasons before any of it is provable.

---

# OWNER DIRECTION (2026-09-14) — 2027 AFL is a TARGETED REBUILD, not a gut-and-replace

**Recorded at the owner's instruction. Treat this as the scope constraint for the AFL
off-season, not a suggestion.**

> Next season's AFL work is a **rebuild, yes — but not a full gut and replace.**

The engine's core architecture was measured this session and it holds up. Do not throw it
out and start again.

## KEEP — measured and working, do not touch the design

- **The hybrid split itself.** Margin / H2H / handicap → 25/75 blend; totals → rules+tiers.
  That is what the engine already does and all three tests independently confirmed it:
  blend best on margin MAE (24.94, better than the market's 25.14), best ATS (57.0%), best
  H2H log loss (0.5607, better than the market); rules significantly best on totals
  (p=0.014 v ML, indistinguishable from the market, the only estimator above break-even).
- **The tier stack T1–T9.** No tier was shown to be broken. T2/T3/T4/T7/T8 all behaved
  sensibly, and the T4 venue profile was spot-checked against 2026 data and is sound.
- **The 25/75 weights.** No evidence they are wrong. Do not re-fit them on one season.
- **The Monte Carlo residual/disagreement machinery.** Sound in principle.
- **The data pipeline** — Squiggle, footywire snapshots, AusSportsBetting xlsx, ELO walk-
  forward in `game_log.py`. All worked. The ELO override pattern for finals weeks works and
  reproduced independently.

## REBUILD — the short, specific list

1. **T5 cannot price a mass absence.** ±8 cap and a table topping out at −5.0 for one elite
   key forward. It broke completely on Sydney (needed ~−35, delivered −8). Needs a
   documented scale for 4+ outs. **This is the number-one item.**
2. **The selection filter is anti-selective.** EV≥10% returns *less* than betting everything
   (handicap +2.5% v +6.6%; totals +3.1% v +12.6%). The gate selects the games where the
   model most disagrees with the market, which carry no extra edge and more model risk.
   Rework staking toward breadth: more games, smaller, looser filter.
3. **The h2h book.** −27.5% ROI on 16 real bets, and sign accuracy is the blend's weakest
   metric. Shrink it or stop it. This is a staking decision, not a model change.
4. **T6 has no siege-mentality / written-off flag type** — the biggest emotional factor of
   the 2026 prelims had no representation at all. Needs a testable definition and a
   backtest before it goes anywhere near a price.
5. **Monte Carlo totals widening** uses the rules-v-ML gap, but ML totals are now measured as
   significantly worse. Stop inflating uncertainty from the weaker head.
6. **The rules model is below break-even ATS (47.7%, 41–45)** while being the best totals
   estimator. Worth understanding, not worth rewriting.

## Already banked from earlier, still in scope, still not a rewrite

- Sigmoid ELO→margin rescale (replacing linear `POINTS_PER_ELO`) — backlogged since
  2026-06-10.
- xScore ELO inputs (scoring shots × 3.70) — pre-season 2026 item, data already in the xlsx.
- Set-shot conversion tracker.

## The framing to carry into the off-season

Nothing measured this season said the model is wrong in structure. What it said is that
**one tier fails in an edge case, and the staking layer on top of the model is losing more
than the model is winning.** That is a rebuild of T5 and the bet-selection rules — not of the
engine.

⚠️ And the honest caveat that belongs beside all of it: n=55 real bets, 86–95 priced games,
and nothing except the totals result reaches significance. **Do not rebuild anything on the
strength of one season's numbers alone** — that is exactly how a plausible-but-wrong
conclusion gets baked into the engine.
