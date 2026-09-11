# Is there a beatable O/U 2.5 signal in the Championship?

**Run:** 2026-09-10 · **Branch:** `research/efl-totals-signal`
**Driver:** `ml/football/backtest/efl_totals_signal_probe.py`
**Verdict: NO — not from anything currently in our data. Do not rebuild the totals model on these inputs.**

---

## Why this probe exists

GW7 pricing surfaced that the model rates Unders heavily. Diagnosis showed the lean
is created by the isotonic calibrator (6 distinct outputs, hard ceiling at 0.6042),
not by the raw model. The obvious next step is "rebuild the calibrator" — but that
only helps if the underlying signal has information. This probe tests that first.

## Data

| | |
|---|---|
| Matches, results + shots/SOT/corners/fouls/cards/referee | 6,693 (2014/15→), 100% coverage |
| Matches with opening **and** closing totals odds | **3,312** (2019/20–2024/25, Pinnacle `P>2.5`/`PC>2.5`) |
| Usable after rolling burn-in | 3,225 |
| Test rows across 4 walk-forward seasons | 2,153 |
| 2025/26 sealed vault | never touched |

Historical totals odds live in the **Pinnacle** columns. `Avg>2.5`/`AvgC>2.5` exist
only from 2026/27 — football-data changed its schema. Anything that reads the `Avg`
columns for a historical round silently gets NaN.

## Method

Strictly pre-match features (every rolling stat `shift(1)`-ed before the window, so a
match never sees itself), walk-forward by season, trained only on strictly earlier
seasons. Features: rolling 10-match sums of goals for+against, shots, shots on target,
corners, recent match totals, minimum rest days, and the referee's goals/game from
their prior matches only.

Three models compared against the de-vigged closing line: **features only**,
**market only** (a pure recalibration of the closing line), and **market + features**
— the last being the only test that matters, because it asks whether the features add
anything the market has not already used.

## Result

Log-loss, lower is better. "base" is a constant predictor at the training base rate.

| Season | n | actual | **CLOSE** | open | base | features | mkt-cal | mkt+feats | **prod D-C** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021/22 | 544 | .465 | **.6833** | .6853 | .6909 | .6888 | .6848 | .6882 | .7090 |
| 2022/23 | 545 | .442 | **.6841** | .6850 | .6886 | .6840 | .6837 | .6834 | .6853 |
| 2023/24 | 529 | .514 | **.6737** | .6811 | .6965 | .6895 | .6764 | .6755 | .6952 |
| 2024/25 | 535 | .439 | **.6835** | .6806 | .6884 | .6850 | .6827 | .6825 | .6809 |

Pooled out-of-sample (n=2,153):

```
market-only    0.68194
market+feats   0.68245     gain -0.00052   (worse)
LR chi2(7) = 0.00, p = 1.0000
closing line   0.68121     <- nothing beat this
```

## The probe is not broken

Three checks, because a null result is exactly what a broken harness produces:

1. **Plant a signal.** Inject the realised total as a feature → log-loss collapses to
   **0.027 / 0.019**. The harness detects signal when it is there.
2. **Do the features correlate with the outcome at all?** Yes, weakly but genuinely —
   shots on target r=+0.082 (p<0.0001), goals sum r=+0.068 (p=0.0001), recent totals
   r=+0.068. They are not noise. The market itself is r=+0.129.
3. **Has the market already used them?** Features explain **R² = 0.36** of the closing
   price. Yes.

That is the whole story: **the features carry real information about scoring, and the
market has already priced all of it.**

## What this says about the current production model

The D-C + isotonic totals model is **worse than the closing line in all four test
seasons**, and worse than a constant base-rate predictor in 2021/22 (.7090 vs .6909).
It beats the constant in the other three, so it is not worthless — but it has never
been competitive with the market, which is consistent with 2026/27's live record
(GW5 O/U 5/12, −2.04% CLV).

## Recommendation

1. **Do not rebuild the totals model on these inputs.** Recalibrating a signal with no
   incremental information produces a tidier copy of the market at best.
2. **Stop pricing Championship O/U 2.5 as a bettable market** — or keep emitting a
   price but exclude it from the EV screen so it cannot generate selections.
3. **The only route back in is genuinely new information**, not better use of the same
   data. Candidates, in rough order of promise:
   - **Real xG.** `HxG`/`AxG` are now published in the live E1 file (60 matches so far,
     accumulating every round). This is the same feed the EPL xG fix needs, so one
     piece of work serves both leagues.
   - **Confirmed lineups** at kickoff — the player layer already exists.
   - **Weather** — wind and rain at kickoff; not in any football tier today.
   None of these are in the 3,312-match sample, so this probe says nothing about them.
   It only rules out what we currently have.
4. **Re-run this probe** once xG has accumulated a season, using the same harness. The
   sealed 2025/26 vault stays reserved for final validation of whatever replaces this.

## Caveats

- Linear/logistic models only. A tree ensemble might extract interaction effects, but
  with r≈0.08 raw correlations and R²=0.36 already absorbed by the market, the ceiling
  is low. Worth one attempt before closing the question for good.
- The probe measures probabilistic accuracy, not staking ROI. A model can be worse on
  log-loss and still profitable on a narrow selective rule — but with no incremental
  information over the close, there is no principled place for such a rule to come from.
- 2019/20 and 2020/21 include COVID crowd-less matches, which changed home advantage
  and scoring. They are in training, not in the test seasons.


---

# Addendum — measured against the OPENING line (2026-09-10)

The probe above benchmarks the closing line. The operative question for this account
is the **opening** line, which is where bets actually get placed. Re-measured with the
isotonic calibrator refitted on **prior seasons only** (the earlier in-sample figures
were optimistic; 2021/22 drops out for want of a prior season).

## Log-loss vs the open

| Season | n | OPEN | CLOSE | model (cal) | vs open |
|---|---:|---:|---:|---:|---:|
| 2022/23 | 552 | .6850 | .6835 | .6862 | +.0012 level |
| 2023/24 | 550 | .6818 | .6749 | .7003 | +.0185 open better |
| 2024/25 | 550 | .6800 | .6826 | .6840 | +.0040 open better |
| **Pooled** | 1652 | **.6823** | .6803 | .6902 | open better |

One season level, two worse, none better.

## Staking simulation at the opening Pinnacle price, flat 1u

| Threshold | Bets | % Under | Strike | P&L | ROI | **CLV** |
|---|---:|---:|---:|---:|---:|---:|
| EV >= 5% | 773 | 70% | 44.9% | -19.00u | -2.46% | **-1.24%** |
| EV >= 10% | 480 | 76% | 41.9% | -28.49u | -5.94% | **-1.28%** |
| EV >= 20% | 198 | 83% | 40.4% | -7.64u | -3.86% | **-1.91%** |

**CLV is negative at every threshold.** Betting at the open, a model with genuine
information should see the line drift toward it. This drifts away, consistently, over
480 bets and three seasons. Combined with 70-83% of selections being Unders, the
selection is being driven by the calibrator's structural lean rather than by the
fixtures.

## Decision (user, 2026-09-10)

Parked for ~a month. On return:

1. **Re-run this probe with real xG.** `HxG`/`AxG` now ship in the live E1 file
   (60 matches at time of writing, accumulating each round). Same harness. This is the
   one input plausibly not fully in the price, and it is shared with the EPL xG fix.
2. **Re-test the mean-reversion question at GW12-15.** As of GW6 the within-season
   decline (3.028 -> 2.606 goals/game) is p=0.23, and the season mean is not
   significantly above the long-run mean at all (z=1.48, p=0.14) - though the
   over-rate is (p=0.008). Historical check: Championship seasons do NOT systematically
   start hot (mean first-69 vs rest = -0.021 g/g, only 5/12 hotter), so there is no
   general reversion effect to lean on. Closest comparator is 2023/24, which opened at
   an identical 2.826 and settled to 2.660 - it came down, but stayed the highest full
   season on record.
3. **Grade GW7** via `scripts/grade_gameweek_saved_bets.py`.

Scope reminder: this rules out goals, shots, shots on target, corners, rest and
referee. It says nothing about xG, confirmed lineups or weather - none of which were
in the 3,312-match sample.

---

# Addendum 2 — the two remaining questions, answered (2026-09-10 PM)

The caveats section above left exactly two things undone: a tree ensemble ("worth one
attempt before closing the question for good"), and the "routes back in" list. Both are
now settled. **Neither reopens the market. The question is closed.**

Nothing here touches the vault — `load()` drops 2025/26 before anything else runs, and
the market-anchored line stays closed per its pre-registration.

## 1. Tree ensemble — no interactions to find

`ml/football/backtest/efl_totals_tree_probe.py`. Design frozen in the docstring before
running: the de-vigged close enters as an XGBoost **`base_margin`**, so the trees can
only learn residual structure; rounds chosen by early stopping on the last *training*
season; one conservative hyper-parameter set, no grid.

Two pre-specified feature sets, because symmetric sums are precisely what would destroy
an interaction: **A** = the same 7 aggregates the linear probe used, **B** = all 21 raw
per-team rolling stats.

| Season | n | CLOSE | mkt-cal | mkt+linear | **treeA** | **treeB** | trees only |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021/22 | 544 | .6833 | .6848 | .6882 | .6854 | .6836 | .6896 |
| 2022/23 | 545 | .6841 | .6837 | .6834 | .6839 | .6845 | .6880 |
| 2023/24 | 529 | .6737 | .6764 | .6755 | .6724 | .6733 | .7001 |
| 2024/25 | 535 | .6835 | .6827 | .6825 | .6848 | .6832 | .6911 |

Pooled, n=2,153:

```
market-only          0.68194   <- the baseline
market+linear        0.68245   gain -0.00052  (worse)
market+treeA (agg)   0.68167   gain +0.00027   1/4 seasons   95% CI [-0.0027, +0.0033]
market+treeB (raw)   0.68119   gain +0.00075   2/4 seasons   95% CI [-0.0011, +0.0026]
trees only, no mkt   0.69214   gain -0.01020  (worse)
closing line         0.68121   <- treeB lands on top of it, to 5 decimal places
```

Both confidence intervals straddle zero and neither model beats market-only in more than
half the seasons. The most telling number is the last one: the best tree configuration
reproduces the closing line to within 0.00002. **That is what "a tidier copy of the
market" looks like when you measure it.** Given the market as a base margin, the trees
found nothing to add and correctly declined to move — early stopping picked 4 to 37
rounds in three of four seasons.

Trees without the market are worse than the market by 0.0102, comfortably the largest
effect in the table, and in the wrong direction.

**Harness self-tests** (`--selftest`), because a null result is what a broken harness
produces:

```
[1] base_margin wiring: 0 rounds vs market, max abs diff 5.68e-08   PASS
[2] planted realised total: log-loss 0.0189 vs market 0.6835       PASS
```

Check 1 matters most: if the base margin were not wired up, every "gain" in the table
would be measured against the wrong base.

## 2. Confirmed lineups — priced already

`ml/football/backtest/efl_totals_lineup_probe.py`. ESPN confirmed XIs, 2023/24 + 2024/25
(2025/26 has 525 matches of starters and is deliberately not loaded — it is the spent
vault). 851 matches join to football-data with opening and closing odds; all 24 team
names map cleanly, and the 958→851 loss is the per-team 5-match burn-in.

Features are what tonight's XI actually did in that team's **prior** 10 matches: summed
per-90 shots, shots on target and goals, plus minutes-share continuity.

Two things reframe this test relative to the earlier ones, and both cut against it:

* The XI is known ~1h before kickoff, so the honest benchmark is the **closing** line,
  not the open. Anything found here is only bettable after lineups drop, into the
  hardest price of the day — and this account bets at the open.
* The vault is spent, so there is no sealed season left to confirm on. The primary test
  is therefore a **powered correlation on all 851 matches**, not an under-powered
  one-season walk-forward.

**Primary: does the XI explain what the closing line got wrong?**

| feature | r vs over25 | p | **r vs market residual** | p |
|---|---:|---:|---:|---:|
| xi_shots90_sum | +0.0557 | .105 | **+0.0004** | .992 |
| xi_sot90_sum | +0.0616 | .072 | +0.0205 | .550 |
| xi_goals90_sum | +0.0528 | .123 | +0.0203 | .554 |
| xi_minshare_sum | +0.0243 | .479 | +0.0360 | .294 |
| xi_minshare_min | +0.0024 | .944 | +0.0118 | .732 |
| *(the close itself)* | *+0.1675* | *<.0001* | — | — |

n=851 detects |r| ≥ 0.096 at 80% power. The XI's attacking capability correlates with
the outcome at roughly the same weak magnitude as the goals and shots features already
tested (+0.05 to +0.06, none significant here) — and its correlation with the market
residual is **+0.0004, p=0.99**. The market has priced it.

Secondary walk-forward (train 2023/24 → test 2024/25, 464 rows, under-powered by
design): close .68399, market-only .68717, market+XI **.69465** — worse by 0.0075.

Self-check: planting the realised total against the residual returns r=+0.79,
p=6e-184, so the residual test detects signal when it is there.

## 3. Real xG — blocked for longer than the parked plan assumed

The parked decision said "re-run this probe with real xG" on return in ~a month. That is
not available. Verified today by fetching the football-data headers directly:

| Season | E0 (EPL) | E1 (Championship) |
|---|---|---|
| 2022/23 – 2025/26 | no HxG/AxG | no HxG/AxG |
| 2026/27 | **present** | **present** |

football-data publishes xG **from 2026/27 only**. Local coverage today: Championship
60/69 matches, EPL 30/30, and zero in every prior season. A 552-match Championship
season means a usable sample arrives around **May 2027**, not October 2026.

Alternative sources were checked, not assumed:

* **Understat** — still dead, and worse than the 2025-05-25 note recorded. The league
  pages now return HTTP 200 with the correct title but **no embedded data payload at
  all** (18KB, adsense blob only, no `datesData`/`teamsData`) — for *historical* seasons
  too, not just recent ones. It is not a route back for the EPL scale-break fix either.
* **FBref/StatsBomb** — returns 403 to a plain client. Plausible but unverified; it would
  need a proper client or a paid feed, and that is a source-evaluation job, not a
  probe re-run.

## Where this leaves the question

The original verdict was "no signal beyond the market **in the data we hold**". That
qualifier is now much smaller than it was:

| Route | Status |
|---|---|
| Goals, shots, SOT, corners, rest, referee — linear | Ruled out (Addendum 1) |
| The same, with interactions | **Ruled out — trees find nothing over the market** |
| Confirmed starting XIs | **Ruled out — r=+0.0004 against the market residual** |
| Real xG | Blocked to ~May 2027 on football-data; no working alternative source today |
| Weather at kickoff | Untested. Not in any football tier, needs a historical backfill |

**Recommendation, unchanged and now better supported: do not price Championship
O/U 2.5 as a bettable market, and do not spend more time modelling it.** Three
independent classes of input have now been tested and all three are already in the
price. The remaining two both require acquiring data we do not have, and only one of
them (xG) has a known arrival date.

If anything is worth doing here, it is the **source-evaluation job** — get real xG for
both leagues from something other than football-data — because that one piece of work
also unblocks the EPL totals scale break, which is a live model fault rather than a
speculative edge. That is a data-acquisition task, not a modelling one.
