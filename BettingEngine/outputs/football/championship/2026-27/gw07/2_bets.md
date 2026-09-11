# EFL Championship GW7 — EV screen and bet decision

**Built:** 2026-09-10 · Prices from the Odds API snapshot 2026-09-10 13:29 UTC
**Entry rule:** ≥10% EV at the best available price
**Screen:** `_supporting/ev_screen.csv` · **Matrix:** `2_bets_matrix.md`
**Tracked slate:** `2_bets.csv` (see "Saved for grading" at the foot of this file)

## Recommendation: **no bets**

Ten selections clear the 10% EV rule. None survives scrutiny. The reasons are
model-side and specific, not general caution — they are set out below.

---

## The candidates

EV at the best non-exchange price. "T5 off" re-runs the same fixture with the
injury tier empty. "Shadow" is the player-layer comparison model.

### 1X2

| Selection | Best | Book | Model p | Mkt no-vig | EV | EV T5-off | EV shadow | Matrix | Reset club |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| Wrexham (at West Ham) | 5.50 | betfred | .308 | .182 | **+69.6%** | +60.6% | +82.7% | ±0 | West Ham |
| Sheffield United (v Wolves) | 3.10 | betano | .487 | .320 | **+51.0%** | +51.0% | +50.7% | **+7** | Wolves |
| Derby (v Birmingham) | 3.30 | leovegas | .417 | .291 | **+37.6%** | +37.6% | +35.3% | **−2** | — |
| Draw — West Ham v Wrexham | 4.33 | sport888 | .292 | .226 | **+26.3%** | +23.0% | +30.4% | n/a | West Ham |
| Watford (v Stoke) | 2.45 | betvictor | .475 | .395 | **+16.4%** | +8.6% | +16.4% | +3 | — |
| Draw — Bolton v Cardiff | 3.80 | virginbet | .291 | .260 | **+10.7%** | +10.5% | +8.9% | n/a | Bolton, Cardiff |

### Over/Under 2.5

| Selection | Best | Model p | Mkt no-vig | EV | EV T5-off | EV shadow | Reset club |
|---|---:|---:|---:|---:|---:|---:|---|
| Under 2.5 — Bolton v Cardiff | 2.30 | .550 | .423 | **+26.6%** | +26.6% | +28.3% | Bolton, Cardiff |
| Under 2.5 — West Ham v Wrexham | 2.25 | .550 | .419 | **+23.9%** | +18.0% | +30.6% | West Ham |
| Under 2.5 — Middlesbrough v Norwich | 2.35 | .524 | .414 | **+23.2%** | +23.2% | +21.4% | — |
| Under 2.5 — West Brom v QPR | 2.12 | .550 | .464 | **+16.7%** | +16.7% | +17.9% | — |

---

## Why none of them is a bet

### Every O/U selection is one calibrator plateau, not a read on the fixture

All four qualifying Unders come from just two model numbers: 0.550 (= 1 − 0.4495)
and 0.524. Eight of the twelve fixtures share the identical model P(Over) of 0.4495,
because the isotonic totals calibrator maps the whole raw band 0.34–0.48 to a single
value and is censored at 0.6042 (see `1_model.md`, fault 1). The ordering of these
four selections is therefore **entirely the market's price ordering** — the model
contributes no fixture-specific information to it, and cannot: it is structurally
incapable of pricing an Over, so its totals signal is always Under.

Two of the four (Bolton v Cardiff, West Ham v Wrexham) are additionally on fixtures
where the new-team reset suppresses the expected total by 0.12–0.30 goals, biasing
them further toward Under.

The prior evidence agrees: GW5's O/U picks were 10 Unders and 2 Overs, went 5/12,
and returned −2.04% CLV.

**Do not bet the Championship O/U 2.5 market on this spine.** This is the same class
of finding as the EPL totals problem in CLAUDE.md but a different cause — EPL has an
xG scale-break; Championship is goals-fed and instead has a calibrator with no
resolution. It needs its own fix.

### The three biggest 1X2 edges are rating lag

Wrexham +69.6%, Sheffield United +51.0% and Derby +37.6% are 13–19 percentage-point
disagreements with a 28-book consensus. In each case the model's view traces to a
rating that has not caught up with the season:

* **Wrexham at West Ham** — West Ham are 9th on 11 points with 14 goals for, and are
  forced to att = def = 1.00 by the reset. The model has them 40.0% at home against
  a market 59.2%. The edge is a rating that is a constant, not an estimate.
* **Sheffield United v Wolves** — Wolves are the division's top scorers (13 GF) and
  are also reset to league average. The matrix scores this +7, but all seven cells
  are Sheffield United base-rate splits ("All games +8.7pp", "Home games +9.8pp",
  "September +25.9pp" over n=12) — one fact counted seven times, not seven signals.
* **Derby v Birmingham** — Derby are 21st on 4 points with 5 GF and 11 GA, and the
  raw fit rates them 10th of 24; Birmingham are 11th and rated 23rd. The matrix
  *opposes* at −2 (Derby short rest ≤3 days −11.7pp over n=41; Derby as a
  competitive-priced side −12.3pp over n=46).

Rank correlation between model net strength and current-season points per game is
0.33. Six games barely move a rating at `decay_rate: 0.001`.

### Watford fails the robustness test

+16.4% with T5, +8.6% without it. The whole edge is Stoke losing Gallagher and Lawal.
A selection that only exists because of an injury input is exactly the pattern that
prompted the T5 cap to be cut from 0.25 to 0.15 on 2026-09-06.

### The season record points the same way

Championship model selections graded so far in 2026/27 are **0W–8L, −100% ROI**
(W3 3 bets, GW5 5 bets — paper, not staked). CLV was **positive** at +6.67%, which
is the tell: the prices were good relative to the close, and the selections still
lost every time. That is what a model with a mis-specified probability but decent
price discipline looks like. At GW5 the model's 1X2 RPS was 0.2286 against a closing
market at 0.1915, and it beat the close in 3 of 12.

Eight losses is a small sample and does not on its own prove the model is unprofitable.
Combined with three independently identified faults that all point the same way, it is
enough to hold fire this round.

---

## What would change the answer

1. **Fix the new-team handling.** Fit clubs new to the division on current-season data
   rather than forcing league average — or enable a live ClubElo feed so T8 has a real
   prior instead of static preseason guesses. This unlocks 5 of 12 fixtures.
2. **Rebuild the totals calibrator.** Isotonic on a raw signal with no discrimination
   produces a step function. Either give the raw totals model real inputs (shots,
   corners, the E1 `HxG`/`AxG` columns — non-null for all 60 published 2026/27
   matches) or drop the O/U 2.5 market for this league until it has measured edge.
3. **Shorten the decay, or add a current-season blend.** A rank correlation of 0.33
   with the live table is too low to be betting 13-point disagreements against a
   28-book consensus.

Items 2 and 3 overlap with the EPL xG work already flagged as the top football
priority — the `HxG`/`AxG` columns now present in the live E1 file would feed both.

## Also worth doing before GW8

* **T6 referees** — appointments were not published at build time; re-run once they are.
* **PPDA** — `ppda_dated.csv` still holds only matchweek-1 2026/27 rows.
* **GW6 rows** — re-run `fetch_results.py --league championship --live-merge` once
  football-data publishes 8–9 Sep, so the ESPN supplement is replaced by the official
  rows (with odds).


---

# Saved for grading — GW7 tracked slate

Saved 2026-09-10 at the user's request so the round can be judged next week.
**These are tracked selections, not staked bets** — the engine recommendation for
GW7 remains NO BET for the reasons above. `status = tracked_selection_not_staked`.

Slate = the seven selections at **≥20% EV** on the best available price. Stakes follow
the frozen matrix rule (1.0u, 1.5u at net ≥ +6). Total 7.5u.

| # | Match | Market | Selection | Price | EV | Matrix net | Stake |
|---|---|---|---|---:|---:|---:|---:|
| 1 | West Ham v Wrexham | 1X2 | Wrexham win | 5.50 | +69.6% | +0 | 1.0u |
| 2 | Sheffield United v Wolves | 1X2 | Sheffield United win | 3.10 | +51.0% | **+7** | **1.5u** |
| 3 | Derby v Birmingham | 1X2 | Derby win | 3.30 | +37.6% | −2 | 1.0u |
| 4 | Bolton v Cardiff | O/U 2.5 | Under 2.5 | 2.30 | +26.6% | +0 | 1.0u |
| 5 | West Ham v Wrexham | 1X2 | Draw | 4.33 | +26.3% | n/a | 1.0u |
| 6 | West Ham v Wrexham | O/U 2.5 | Under 2.5 | 2.25 | +23.9% | +0 | 1.0u |
| 7 | Middlesbrough v Norwich | O/U 2.5 | Under 2.5 | 2.35 | +23.2% | −1 | 1.0u |

Only one selection carries matrix support (Sheffield United, +7). Four of the seven
sit on a club whose D-C rating is forced to league average, and the three Unders all
share the calibrator plateau.

## To grade next week

```
python scripts/grade_gameweek_saved_bets.py     --bets outputs/football/championship/2026-27/gw07/2_bets.csv     --league championship
```

Run `python ml/football/fetch/fetch_results.py --league championship --live-merge`
first so the 11–13 Sep results and closing odds are present. Output lands at
`4_review_bets.csv`.

### Grader bug fixed while saving this slate

`score_football_saved_bets.py` could not grade a **Draw** or an **Under**: draws were
scored as losses against the away odds column, and unders were graded *backwards*
against the over odds column. Four of these seven selections would have been graded
wrong. Fixed there, and `scripts/grade_gameweek_saved_bets.py` is the reusable entry
point — validated by re-grading GW5 and reproducing its published figures exactly
(0W-5L, −5.50u, −100% ROI, +12.61% CLV, beat close 3/5).

The candidate rejection screen that was previously `2_bets.csv` is now at
`_supporting/candidate_screen.csv`.
