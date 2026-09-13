# AFL 2026 Preliminary Finals — Pricing Report

**Run date:** 2026-09-13
**Round label:** 27 (wildcard = 25, Finals Week 1 = 26 in Squiggle's numbering but priced
here as part of R26's ELO chain; semis = 26, prelims = 27 in `prepare_afl_round.py`'s scheme)
**Model:** `scripts/prepare_afl_round.py` — rules T1–T8 + ML (XGBoost) primary margin/H2H,
rules primary totals. T9 matrix confluence run as shadow.

---

## 1. Semi-final results brought in

Scores from the Squiggle API (`q=games;year=2026;round=27`), goals×6+behinds reconciled
against the final score for every row before writing.

| Final | Result | Total |
|---|---|---|
| SF1 | **Fremantle 18.12 (120) def. Geelong 16.10 (106)** — Optus, Fri 11 Sep | 226 |
| SF2 | **Brisbane 21.18 (144) def. Adelaide 13.13 (91)** — Gabba, Sat 12 Sep | 235 |

Appended to `outputs/afl_weekly_review/historical/latest.xlsx` (also kept as
`latest_with_finals_wk2.xlsx`; the pristine pre-append copy survives as
`afl_20260908_094856.xlsx`). **All 3,568 pre-existing rows verified byte-identical after
the append** — this workbook is rewritten wholesale, which is the failure mode that ate the
`week_ending` column out of the bet ledger in September.

Odds on the two new rows: h2h open/close = cross-book mean from `data/odds_snapshots`
(matching AusSportsBetting's consensus convention), line/total = sportsbet. **"Open" is the
first captured snapshot (2026-09-09 17:45 UTC), not the true book open** — recorded in the
row's Notes field rather than passed off as an open.

`features_afl.csv` rebuilt via `ml/afl/game_log.py`: 1,068 → 1,070 rows.

### Post-semi ELO

`get_current_elo()` reads each team's *pre*-match rating off their most recent row, so it
lags one game — tolerable in the H&A season, not across a finals week. Ratings were walked
forward with `game_log.update_elo` (K=72 finals) and applied as `FINALS_ELO_OVERRIDE[27]`.

| Team | Last game | Pre | **Post** |
|---|---|---:|---:|
| Sydney Swans | won QF2 141–88 v Brisbane | 1704.3 | **1743.2** |
| Brisbane Lions | won SF2 144–91 v Adelaide | 1706.3 | **1735.1** |
| Fremantle Dockers | won SF1 120–106 v Geelong | 1680.8 | **1709.4** |
| Hawthorn Hawks | won QF1 72–40 at Fremantle | 1654.0 | **1704.9** |

Two independent checks passed: the same method reproduces the R26 overrides exactly, and
Hawthorn 1704.9 / Sydney 1743.2 match the post-week-1 figures recorded separately in
`afl_semifinals_pricing_2026.md`.

---

## 2. The week off — what the model actually did with it

| Team | Last game | Days to prelim | T3 rest class | 3A credit |
|---|---|---:|---|---:|
| Hawthorn | 3 Sep (QF1) | **16** | `bye` | **+1.5** |
| Sydney | 5 Sep (QF2) | **13** | `long` | **+1.0** |
| Fremantle | 11 Sep (SF1) | 7 | `normal` | — |
| Brisbane | 12 Sep (SF2) | 7 | `normal` | — |

Both hosts had the same structural week off. **They are credited differently — 1.5 vs 1.0 —
purely because Sydney's prelim is on the Friday and Hawthorn's on the Saturday.**
`_classify_rest` sets the `bye` band at *>13* days and Sydney land on exactly 13. It is
worth 0.5 pts and changes no decision here, but it is a boundary artefact, not a judgement:
a Friday host will always be scored a notch below a Saturday host after an identical bye.

Both hosts also take a *negative* 3D form signal — the "flat-spot after a big win" angle
fires on Sydney (won by 53) and on Brisbane (won by 53).

---

## 3. Tier coverage — R27 (mandatory report)

| Tier | Status | Detail |
|---|---|---|
| T1 ELO / scoring | ✅ real | rebuilt today, post-semi override applied |
| T2 style | ✅ **refreshed 13 Sep** | Footywire re-scraped to R27 — 18 teams, 24–25 games each, finals included |
| T3 situational | ✅ real | rest / travel / form from rebuilt features |
| T4 venue | ✅ real | fortress + venue scoring profile |
| T5 injuries | ✅ real, hand-curated | 2 sources cross-checked — **but see §5, the cap binds** |
| T6 emotional | ⛔ **researched zero** | 6 angles found and assessed; all rejected with reasons — see §6c |
| T7 weather | ✅ real | open-meteo (Tomorrow.io key absent); SCG clear/calm, MCG 20.7 km/h `moderate_wind` |
| T8 kicking | ✅ real | 18 teams above the shot threshold, league avg 52.6% |
| T9 matrix | ✅ real (shadow) | 6-way handicap + 4-way H2H confluence on both games |
| ML models | ✅ loaded | pickle/sklearn version warnings only |

**8 of 9 tiers genuinely populated on current data; T6 is a researched zero.** Clears the
75% bar. Three source faults were found and fixed while checking (see §7).

---

## 4. Prices

### PF1 — Sydney Swans v Fremantle Dockers · SCG · Fri 18 Sep 19:40 AEST

| Metric | Rules | Primary (ML+tiers) | **Market** (20 books, 13 Sep 09:00) |
|---|---|---|---|
| Margin | Sydney **−15.2** | Sydney **−32.4** | **Fremantle −11.5** |
| H2H | Syd 66.4% / $1.51 | Syd 81.6% / $1.25 | Syd 38.0% / **$2.49** (best 2.58), Fre **$1.53** (best 1.55) |
| Total | 209.2 | 209.2 | **185.5** |

Tier stack: T1 +11.5 · T2 +4.0 (capped) · T3 +3.0 · T4 +3.0 · **T5 −8.0** · T6 0 · T7 0 · T8 +1.7.

### PF2 — Hawthorn Hawks v Brisbane Lions · MCG · Sat 19 Sep 17:15 AEST

| Metric | Rules | Primary (ML+tiers) | **Market** |
|---|---|---|---|
| Margin | Hawthorn **−7.1** | Hawthorn **−8.3** | **Brisbane −1.5** |
| H2H | Haw 57.9% / $1.73 | Haw 59.1% / $1.34* | Haw 47.8% / **$1.99** (best 2.12), Bri **$1.82** (best 1.86) |
| Total | 196.7 | 196.7 | **184.5** |

*The ML classifier's 74.5% H2H is a separate head from the ML margin regressor, and the two
are badly inconsistent: the raw ML margin is Hawthorn **+3.5** (+8.3 after tiers), and a
3.5-pt favourite is not a 74.5% chance. Use the margin-derived 59.1%. Tier stack:
T1 +2.9 · T2 +0.3 · T3 +4.8 · T4 0 · T5 +0.5 · T6 0 · **T7 −3.1** · T8 −1.3.

---

## 4b. THE COMBINED MODEL — 25% rules / 75% ML (the frozen finals spec)

`scripts/monte_carlo_afl_finals.py --round 27 --sims 100000 --seed 20260913`, 100,000 sims,
paired bootstrapped 2025 out-of-sample residuals (n=216), disagreement-widened, with
Thursday selection risk simulated. **The spec is 25/75 on margin only — totals are
rules-only, and H2H is derived from the simulated margin rather than blended separately.**
Prices are best-available across 20 books (exchange lay quotes excluded).

Two runs: the frozen spec as-is, and a sensitivity with the blend's measured **+4.78 pt**
home-favouritism removed. ⚠️ **That bias is not statistically significant at n=86** (95% CI
−2.05 to +11.62), so the frozen spec is the primary read and the corrected row is a
sensitivity — see §8b.

### PF1 — Sydney v Fremantle · market: Fremantle −11.5, Syd $2.58 / Fre $1.55, total 185.5

| | Blend margin | Sydney | Fair | EV @ $2.58 | Syd +11.5 cover | Over 185.5 |
|---|---:|---:|---:|---:|---:|---:|
| **Frozen spec (primary read)** | Syd **−28.1** | 77.2% | $1.30 | **+99.2%** | 85.4% (+62.3%) | 74.0% (+40.7%) |
| Bias sensitivity (−4.78) | Syd **−23.3** | 73.3% | $1.37 | **+89.0%** | 82.4% (+56.5%) | 74.0% (+40.7%) |

### PF2 — Hawthorn v Brisbane · market: Brisbane −1.5, Haw $2.12 / Bri $1.86, total 184.5

| | Blend margin | Hawthorn | Fair | EV @ $2.12 | Haw +1.5 cover | Over 184.5 |
|---|---:|---:|---:|---:|---:|---:|
| **Frozen spec (primary read)** | Haw **−8.0** | 60.8% | $1.65 | **+28.9%** | 62.3% (+24.6%) | 63.4% (+20.5%) |
| Bias sensitivity (−4.78) | Haw **−3.2** | 54.8% | $1.83 | **+16.1%** | 56.8% (+13.7%) | 63.4% (+20.5%) |

**⚠️ The blend makes PF1 worse, not better.** It shifts Sydney from −15.2 (rules) to −28.1,
because it puts 75% of the weight on the head that is *most* blind to the missing six: the
ML margin regressor's inputs are ELO, EMA form and opponent-adjusted margin, and it has no
injury input at all. T5 is added on top of it, but the baseline it is added to is a
full-strength Sydney. **Blending cannot fix an input fault — it amplifies it.**

**PF2 is where the blend earns its keep.** Rules +7.1 and ML +8.3 are nearly identical, so
the blend adds little of its own here, but it is the estimator with the record behind it:
**57.0% ATS against the closing line v the rules model's 47.7%** (§8b). Hawthorn reads
**+28.9% EV** on the frozen spec and **+16.1%** on the bias sensitivity — over the 10% gate
either way. That is the one live selection in the round; §6b weighs it.

---

## 5. ⚠️ PF1 is not priceable by this model

Sydney are without **six** players who would otherwise be in their best 22:

- **Isaac Heeney, Chad Warner, Nick Blakey, James Jordon, Riley Bice** — suspended by the
  club on 19 Aug for the rest of the season, including finals.
- **Callum Mills** (captain) — ruptured his ACL late in the first quarter of the QF on 5 Sep.

T5's raw read on that is **−12.32** for Sydney, −11.32 net of Fremantle's outs, **clamped to
the tier's ±8.0 cap**. To reconcile the model with the market, T5 would need to be **−34.7**
(rules) or **−51.9** (primary) — **−41.5 on the 25/75 blend**. The tier is short by a factor of four.

That is not a tuning problem. The `IMPACT_TABLE` tops out at −5.0 for a single elite key
forward and the cap was set to stop two or three outs overwhelming a price. It has no
representation for a team losing five of its best players at once, and the ±8 cap is doing
exactly the job it was designed for while producing a number that is nowhere near right.

**The Championship "absentees are already in the ratings" lesson does not rescue it either.**
That lesson applies where a rating was fitted with zero appearances from the player. Sydney's
1743 was built across a full season *with* Heeney, Warner and Blakey and has been moved by
only two subsequent games — and both of those were 53-point wins (v North Melbourne, and the
QF v Brisbane), which pushed the rating **up**. So the absence is neither priced by T5 nor
absorbed by ELO.

The two 53-point wins are the one genuine argument on the model's side, and they are not
nothing — this depleted list beat a full-strength Brisbane by 53. But the model's Sydney
−32.4 is not that argument being made; it is a rating that still contains the missing players.

The resulting EVs — **+71% on Sydney (rules), +110% (primary)** — are the tell. A three-figure
edge against 20 books is a broken input, not a bet.

---

## 6. Value check against real market prices

Market captured 2026-09-13 09:00 UTC, 20 bookmakers, overrounds +5.6% / +5.0%.
"Bias-adj" applies the **+5.62 pt home-favouritism** measured on the rules model across 95
priced 2026 games (see §8).

| Selection | Best price | Model prob | Bias-adj prob | Market no-vig | Bias-adj EV | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Sydney H2H | $2.58 | 66.3% | 60.5% | 38.0% | **+56%** (blend **+87%**) | **NO BET** — §5, model can't see six outs |
| Sydney +11.5 | $1.90 | — | — | — | — | **NO BET** — same input fault |
| Fremantle H2H | $1.55 | 33.6% | 39.5% | 62.0% | −39% | avoid on the model; the model is the thing that's wrong |
| **Hawthorn H2H** | **$2.12** | 57.9% | **51.7%** | 47.8% | **+9.6%** | rules alone: under the gate. **Blend: +28.9% / +16.1% — LIVE, see §6b** |
| Hawthorn +1.5 | $1.85–2.00 | — | ~51% | — | ~+2% | no |
| Brisbane H2H | $1.86 | 42.6% | 48.8% | 52.2% | −9.2% | avoid |
| Over 185.5 (PF1) | $1.90 | 55.6% (track record) | — | — | **+5.6%** | **NO BET** — §8a, and contaminated by the same Sydney fault |
| Over 184.5 (PF2) | $1.90 | 55.6% (track record) | — | — | **+5.6%** | **NO BET** — §8a; the more defensible of the two, revisit if the line drifts to 190 |

**No bet on PF1. Hawthorn in PF2 is a live selection — see §6b.**

- **PF1** — the only number the model produces is one it is not equipped to produce.
- **PF2** — moved once the blend was run, and moved again once the blend was measured
  correctly. Rules alone: +9.6%, under the gate. The 25/75 blend: **+28.9%** frozen,
  **+16.1%** on the bias sensitivity. Weighed in full in §6b.

T9 confluence (shadow, not priced): PF1 6-way handicap + 4-way H2H → home; PF2 6-way
handicap + 4-way H2H → home, 5-way totals → over.

---

## 6b. The one live selection — Hawthorn, PF2

| | Blend | Fair | Best market | EV |
|---|---:|---:|---:|---:|
| Hawthorn H2H, frozen spec | 60.8% | $1.65 | **$2.12** | **+28.9%** |
| Hawthorn H2H, bias sensitivity | 54.8% | $1.83 | $2.12 | **+16.1%** |
| Hawthorn +1.5, frozen spec | 62.3% | — | $2.00 | +24.6% |
| Hawthorn +1.5, bias sensitivity | 56.8% | — | $2.00 | +13.7% |

**Clears the 10% gate on every version.** On the rules model alone it was +9.6% and did not
— so this selection exists *because* of the blend.

**For it:** the blend is the best estimator I can measure — lowest MAE of anything including
the market (24.94 v 25.14), best log loss and Brier on H2H (0.5607 / 0.1931, both better
than the market), and **57.0% ATS against the closing line (49–37) where the rules model is
47.7% and below break-even** (§8b). Rules (+7.1) and ML (+8.3) agree on direction, so the
model-alignment rule is satisfied. The ML H2H classifier independently reads 74.5%. T9 flags
a 6-way handicap and 4-way H2H confluence for Hawthorn. Hawthorn have the full 16-day bye
against Brisbane's 7 days plus travel.

**Against it:** none of the blend's advantages are statistically significant at n=86 —
blend v market on error is p=0.87, the ATS edge is p=0.24. Three of T9's six confluence
cells are `vs Brisbane` / `vs Hawthorn` H2H history, i.e. one fact counted twice. Brisbane
are two-time defending premiers in their fourth straight prelim, which no tier captures.
And the older "both heads above the market on the home side" caution (4–8 ATS) was measured
on the *rules* model, which is the one that is actually below break-even — so it is weaker
evidence against a blend selection than it first appears.

**Read: this is a live bet, and the best-supported one of the round.** The blend is the only
estimator here with a positive ATS record, and the price clears the gate on both the frozen
spec and the conservative sensitivity. Size it small — the supporting sample is 86 games and
nothing in it reaches significance — and confirm after Thursday's teams. **Hawthorn +1.5 at
$2.00 is the cleaner expression than the H2H**, because the blend's edge is strongest on the
spread (57.0% ATS) and weakest on raw sign accuracy (67.4%).

---

## 6c. T6 emotional — researched, and still zero

Six angles were found and each tested against the flag types `AFL_T6_CONFIG` actually
supports. Full reasoning in `outputs/afl_round_prep/r27_2026/emotional_r27_2026.json`.

| Team | Angle | Candidate flag | Verdict |
|---|---|---|---|
| Sydney | Five players banned for the season (19 Aug) | `club_drama` major (−3.0) | **Rejected twice over** — double-counts T5 (already at its cap), *and* the direction is contradicted: since the ban Sydney have won both games by 53, and Cox said being written off was part of the motivation |
| Sydney | McInerney + Amartey fit to return | `star_return` (+3.5) | **Rejected** — T5 already treats both as available, so the baseline has them playing; paying a return bonus counts them twice |
| Sydney | Written-off / siege mentality | none exists | **Unpriceable** — no such flag type; `shame_blowout` requires a heavy *defeat* and Sydney won by 53. Recorded as a known unmodelled positive for Sydney |
| Fremantle | First prelim since 2015; Longmuir publicly claiming underdog status | `must_win` / occasion | **Rejected** — symmetric, and no drought/occasion flag exists (T3's 3E is ANZAC-only) |
| Hawthorn | First prelim since the 2015 premiership | `must_win` / occasion | **Rejected** — and it cancels especially cleanly: *both* prelims are a first-since-2015 return for one side |
| Brisbane | Three-peat chase; Fagan questioned the group's mentality after the 53-pt QF loss | `shame_blowout` (+1.5) | **Rejected — already spent.** The response game happened and was rewarded: they answered with a 144–91 semi win. Applying it now double-counts what the ELO has absorbed |

Checked and absent: no retirements or farewells at any of the four clubs (Taylor Walker —
Adelaide, and Tom Liberatore — Western Bulldogs, are both at eliminated clubs); no
new coach; no derby; no personal tragedy. **Milestones are a weak negative** — none found,
but there is no reliable milestone feed for finals week, so read that as "not found", not
"none exist".

**The honest summary: the biggest emotional story in the round — Sydney's siege mentality,
which is the mechanism behind a 53-point QF upset — has no representation in this tier at
all.** That is a gap in T6, and it points the opposite way to the market.

---

## 7. Faults found and fixed this run

1. **`scripts/_export_afl_prices.py` crashed** on `sqlite3.Row.get()` — `Row` supports
   `__getitem__` but not `.get`. The CSV was written before the crash so no output was lost,
   but the console summary never printed. Fixed.
2. **T7 printed a hardcoded `[tomorrow_io]` label** regardless of the real source. Every AFL
   run since the Tomorrow.io key went missing has reported `[tomorrow_io]` one line after
   printing `TOMORROW_API_KEY not found` and silently falling back to open-meteo. The stored
   `weather_source` column was always correct — only the display lied. Fixed to print the
   actual `data_source`.
3. **afl.com.au's injury list returned the Hawthorn and Geelong blocks transposed** (Worpel,
   Stanley, Conway, Barker under Hawthorn — all Geelong 2026 players; Nash, Reeves,
   Scrimshaw, Anderson under Geelong — all Hawthorn). Undoing the swap, it agrees with the
   local scraper on all four clubs. **The local scraper was right; the cross-check was wrong.**
4. **`monte_carlo_afl_finals.py` could not run at all** — its market snapshot path was
   hardcoded to `2026-09-02_afl_finals_week2_sportsbet.csv`, which no longer exists, and its
   output filename was hardcoded too. Parameterised: `--markets`, `--out` and `--home-bias`
   (default 0.0, so the frozen spec is unchanged), plus R27 `UNCERTAIN_AVAILABILITY` entries.

---

## 8. Totals — rules+tiers is the best model here, and it is not close

Series validated before use, after the margin reconstruction error (§8b):

1. `ml_total` = `ml_total_raw` + bias + (t2,t5,t6,t7,t8) — residual is a per-round constant,
   sd 0.03 within round. Confirmed.
2. `rules_total` = `t1_total` + all seven tier totals — exact on **110 of 112** rows (the two
   exceptions are R11/R12 floor cases).
3. `primary_total` == `rules_total` on every stored row. Rules is the primary for totals by
   design, and the code does what the design says.

So "ML + tiers" for totals = `ml_total + t3_tot + t4_tot`, the same shape as the margin.

**Totals accuracy — 86 priced 2026 games**

| Estimator | bias | MAE | RMSE |
|---|---:|---:|---:|
| **Rules (T1+tiers)** | −4.95 | **22.36** | **28.38** |
| ML + tiers | −14.70 | 27.87 | 37.18 |
| Blend 25/75 | −12.26 | 25.62 | 33.70 |
| Market close | **+0.50** | 21.52 | 27.96 |

**O/U against the closing line — did it pick the right side?**

| Estimator | acc | record | picks Over | p vs 50% |
|---|---:|---:|---:|---:|
| **Rules (T1+tiers)** | **55.8%** | **48–38** | 39.5% | 0.33 |
| ML + tiers | 50.0% | 43–43 | 19.8% | 1.00 |
| Blend 25/75 | 51.2% | 44–42 | 16.3% | 0.91 |

Break-even at $1.91 is 52.4%; the actual over-rate against the close was 44.2%.

**Paired absolute-error tests — and this is the one result in the whole exercise that
reaches significance:**

| Comparison | difference | p |
|---|---:|---:|
| Rules v ML+tiers | rules better by **5.52 pts** | **0.014** |
| Rules v blend | rules better by 3.26 pts | 0.062 |
| Rules v market | rules worse by 0.83 pts | 0.593 |

**Rules+tiers is significantly better than ML on totals, better than the blend, and
statistically indistinguishable from the market close.** It is also the only totals
estimator above the betting break-even. Blending *hurts* here — exactly the inverse of the
margin result — which is precisely why the frozen spec uses rules-only for totals. That
design decision is now backed by a significant test rather than an assertion.

Removing the model's −4.95 low bias nudges it further: 56.8% → 57.9% O/U, and it fixes the
Under skew (picks Over 37.9% → 47.4% against an actual 44.2%). Not significant, but coherent.

### 8a. So why is this week still a no-bet on totals?

Because **this week's readings sit outside the range the model has ever been right in.**

The rules total normally sits *below* the market: mean **−6.3**, median −7.3, 90th percentile
+10.8. This week it is **+23.7 (PF1)** and **+12.2 (PF2)** *above* it. Only **9 of 95** games
all season put the model more than +12 over the market, and only 6 more than +20.

| Rules total − market | n | actual over-rate | model right |
|---|---:|---:|---:|
| −99 to −20 | 18 | 38.9% | 61.1% |
| −20 to −10 | 24 | 41.7% | 58.3% |
| −10 to −5 | 8 | 25.0% | 75.0% |
| −5 to 0 | 9 | 55.6% | 44.4% |
| 0 to +5 | 13 | 53.8% | 53.8% |
| +5 to +12 | 14 | 50.0% | 50.0% |
| **+12 and above** | **9** | 55.6% | **55.6%** |

The model earns its 55.8% overall almost entirely on the **Under** side, where it sits well
below the market. On the Over side — where it is this week — it is a coin flip.

**Two readings of the same number, and they disagree by a factor of ten:**

| | PF1 P(Over 185.5) | EV @ $1.90 | PF2 P(Over 184.5) | EV @ $1.90 |
|---|---:|---:|---:|---:|
| Magnitude, `TOTAL_STD` 22.7 | 85.2% | +61.8% | 70.5% | +33.9% |
| Magnitude, empirical RMSE 28.4 | 79.8% | +51.7% | 66.6% | +26.6% |
| Magnitude, bias-corrected | 84.4% | +60.3% | 72.7% | +38.2% |
| **Track record when the edge is >+12** | **55.6%** | **+5.6%** | **55.6%** | **+5.6%** |

The magnitude says these are enormous bets. The model's own hit rate when it has been this
far above the market says +5.6%, under the gate — and that 55.6% is 5–4 from nine games,
95% CI **25% to 83%**. There is no honest edge in either direction.

**Trust the track record over the magnitude.** That is the entire lesson of §8b: a number
that looks big is not evidence, and this model's error distribution is 28 points wide.

Two further reasons to leave it alone:

- **PF1's Over is contaminated by the same fault as its margin.** The rules total is fed by
  team scoring rates, and Sydney's include 141 and 123 from a side that no longer exists.
  The Over signal there is not independent evidence — it is the same broken input again.
- **The Monte Carlo widens totals uncertainty using the rules-v-ML gap** (45.9 and 49.8 pts),
  which is why it reports 74.0% / 63.4% rather than the ~80% / ~67% the point estimate
  implies. Given ML is now measured as *significantly worse* on totals, widening on its
  disagreement is questionable — it is inflating uncertainty from a head we know is the
  weaker one. Worth revisiting, and it happens to push toward caution here.

**No totals bet, on both games — but for a much better reason than last time.** PF2's Over
is the more defensible of the two and would become interesting if the line drifts toward 190.

### 8b. Is the 25/75 blend actually better? Measured — CORRECTED 2026-09-13

> ⚠️ **The first version of this table was wrong and has been replaced.** It reconstructed
> the ML+tiers series as `ml_margin + (t2+t3+t4+t5+t6+t8)`, but the stored `ml_margin`
> **already contains t2, t5, t6 and t8** — so those four tiers were added twice. A `+1.95`
> offset fitted from four observations then happened to absorb most of the error, which is
> why the reconstruction looked plausible. The exact identity is
> `primary_margin = ml_margin + t3_hcp + t4_hcp`, verified to 0.03 pts on every row where
> the stored value exists. Everything below uses the exact series.
>
> The wrong table made the blend look no better than the rules model. **It is better, and
> the earlier project finding that ML beats rules on H2H and handicap stands.** The R27
> prices themselves were never affected — they use stored values, not the reconstruction.

**Margin — 86 priced 2026 games with results**

| Estimator | bias | MAE | RMSE | sign acc |
|---|---:|---:|---:|---:|
| Rules (T1+tiers) | +5.30 | 26.75 | 35.01 | 68.6% |
| ML + tiers (primary) | +4.61 | 25.19 | 32.49 | **72.1%** |
| **Blend 25/75** | +4.78 | **24.94** | **32.49** | 67.4% |
| Market close | **+1.10** | 25.14 | 32.34 | 67.4% |

**The blend has the lowest MAE of anything here, the market included** (24.94 v 25.14), and
ties the market on RMSE. The ML head has the best sign accuracy at 72.1%.

**Handicap — did the model pick the side that covered the closing line?**

| Estimator | ATS | record | vs 50% |
|---|---:|---:|---:|
| Rules (T1+tiers) | 47.7% | 41–45 | p=0.75 |
| ML + tiers | 52.3% | 45–41 | p=0.75 |
| **Blend 25/75** | **57.0%** | **49–37** | p=0.24 |

Break-even at $1.91 is 52.4%. **The rules model is below break-even on the spread; the blend
is 4.6pp above it.** This is the clearest separation in the whole exercise and it is exactly
the direction the project already had on record.

**H2H — 86 games, probabilities scored properly**

| Estimator | acc | log loss | Brier |
|---|---:|---:|---:|
| Rules (T1+tiers) | 68.6% | 0.5920 | 0.2059 |
| ML H2H classifier | 67.4% | 0.5801 | 0.2017 |
| **Blend 25/75 (probs)** | **69.8%** | **0.5607** | **0.1931** |
| Market close | 68.6% | 0.5618 | 0.1933 |

**The blend beats the market on log loss and Brier and matches it on accuracy.** Note this
uses `ml_h2h`, the separate H2H *classifier* — the earlier version of this report scored the
sign of the margin regressor instead, which is a different model and the wrong test for an
H2H claim.

**How much of this is real? Honest answer: directionally yes, statistically thin.**

| Comparison | difference | p |
|---|---:|---:|
| Blend v rules, paired abs error | −1.81 pts | 0.106 |
| Blend v market, paired abs error | −0.20 pts | 0.866 |
| Blend v ML+tiers, paired abs error | −0.25 pts | 0.534 |
| Blend ATS v 50% | +7.0pp | 0.235 |

⚠️ **And the home bias is NOT statistically significant for any estimator** — rules +5.30
(95% CI −2.05 to +12.66), blend +4.78 (−2.05 to +11.62), market +1.10 (−5.77 to +7.98). At
n=86 the standard error on a bias is ±3.5 pts. Treating the bias correction as an
established fact was an overreach; it is a sensitivity, not a fix. **The frozen spec is the
primary read and the corrected row is the sensitivity**, not the other way round.

The one thing that is solid: **the blend is the best model on every headline measure, and on
margin error it is level with the market rather than behind it.** That is a stronger position
than the rules model alone, which loses to the market on MAE and is below break-even ATS.

### Last week's model, scored

| Game | Rules | ML | Market close | Actual | Closest |
|---|---:|---:|---:|---:|---|
| Fremantle v Geelong — margin | +3.0 | +4.0 | +11.5 | **+14** | market |
| — total | 183.7 | 183.7 | 178.5 | **226** | rules |
| Brisbane v Adelaide — margin | +15.8 | +25.8 | +20.5 | **+53** | ML |
| — total | 207.5 | 207.5 | 182.5 | **235** | rules |

---

## 9. Outstanding before these prices are worth anything

1. **T5 cannot price a mass absence.** Either raise the cap with a documented scale for 4+
   outs, or add an explicit "decimated list" override. Until then PF1 has no model price.
2. **T2 is now current but structurally can't see the Sydney problem** — the style snapshot
   is a *season aggregate*, and 22 of Sydney's 24 games were played with the banned five.
   Refreshing it moved Sydney's contested-possession rating 138.6 → 138.9.
3. **Team lists land Thursday.** Sydney's McInerney (hamstring, test) and Amartey, and
   Fremantle's Darcy (knee, test) / Walker (ankle, test) / Cox are all unresolved.
4. The ML H2H classifier and ML margin head disagree materially on PF2 (74.5% v a 3.5-pt
   raw line). Worth a look before the classifier is trusted anywhere.
5. **The Monte Carlo widens totals uncertainty on the rules-v-ML gap**, but ML totals are
   now measured as significantly worse (p=0.014). Widening on the weaker head's disagreement
   needs revisiting — it is currently inflating totals uncertainty on both prelims.
6. **T6 has no siege-mentality / written-off flag type**, which is the single biggest
   emotional factor in this round and the mechanism behind Sydney's QF upset. Adding one is
   a research job, not a round job — it needs a testable definition and a backtest.
7. **The rules model is below break-even ATS in 2026 (47.7%, 41–45)** — even though it is
   the best totals estimator there is. Margin and totals point in opposite directions on
   which head to trust, and the engine already reflects that. Worth a formal review. That is a bigger
   finding than anything in this round and deserves its own review — the rules margin is
   still the primary for totals and the audit line for everything else.
