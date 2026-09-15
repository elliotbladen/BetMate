# AFL matrices — the NRL hit-rate research, repeated on AFL

**Verdict: AFL is NOT broadly better at extracting value through matrices. H2H and
handicap lose reliably, exactly as NRL does. But AFL totals at HIGH CONFLUENCE is the
one place either sport shows a walk-forward edge that survives — and it is strongest
at the opening price, which is the inverse of the NRL finding.**

Companion to `NRL_TOTALS_MATRIX_V2_HITRATE.md`. Same rule, same thresholds, same
settlement, same bootstrap, so the numbers are directly comparable.

---

## 1. AFL does NOT have the defect the NRL v2 fix was built for

The NRL v1 metric was wrong because NRL totals are right-skewed: one blowout moves the
mean without moving what a bet settles on, so 56% of cells inherited a phantom overs
tilt. **AFL has no such skew.**

| measured on each sport's own 2022-25 window | NRL (n=840) | AFL (n=855) |
|---|---|---|
| MEAN total − line | **+0.44** | **−0.01** |
| MEDIAN total − line | −0.50 | +0.50 |
| over hit rate | 49.8% | 51.1% |
| games >20 over vs >20 under | 66 vs 45 | 200 vs 208 |
| v1 cells reading overs | **56%** (432/773) | **50%** (380/762) |
| v2 cells reading overs | 48% | 55% |

AFL totals sit ~168-178 points and are near-symmetric; NRL totals sit ~40 and are
right-skewed by blowouts. The two sports are skewed in *opposite* directions
(AFL mean < median, NRL mean > median).

**So the v2 change earns its place on AFL for a completely different reason.** Not
de-tilting — *resolution*. The hit-rate metric almost never lands exactly on 50.0,
where a mean total often equals the mean line, so v2 produces far more directional
cells. The practical effect is that **v1 cannot reach high confluence at all**: over
nine walk-forward seasons v1 produced **34 bets** at net +7 and **2** at net +10,
against v2's 718 and 323. The headline result below simply does not exist under v1.

---

## 2. Regression gates — all three builders are behaviour-preserving

The three AFL matrix builders had hardcoded machine-specific paths
(`/Users/elliotbladen/Downloads/afl (2) (1).xlsx`, output to `~/Betting_model/`), so
they could not run on another machine and wrote outside the repo. All three now take
`--seasons` / `--source` / `--out` and default to repo-relative paths.

Rebuilt from the original source with default seasons, against the shipped artefacts:

| builder | compared | differences |
|---|---|---|
| `afl_team_totals_matrix.py --metric mean` | 7,362 data cells | **0** |
| `afl_h2h_matrix.py` | 7,362 data cells | **0** |
| `afl_handicap_matrix.py` | 1,155 csv rows | **0** |

---

## 3. Walk-forward — 9 test seasons, 4-season rolling window, each strictly out of sample

AFL carries closing totals from 2014, so this is a **9-season** walk-forward where NRL
only had 4. Flat stakes, one unit per qualifying side, bootstrap 95% CI.

### H2H and handicap: reliably negative

| market | pooled ROI | n | 95% CI | seasons +ve |
|---|---|---|---|---|
| h2h, net +7 | **−8.17%** | 498 | **[−15.9, −0.5]** | 3/9 |
| h2h, net +10 | −10.54% | 162 | [−22.1, +1.5] | 4/9 |
| handicap, net +7 | **−10.54%** | 425 | **[−19.5, −1.5]** | **0/9** |
| handicap, net +10 | −8.32% | 146 | [−23.9, +7.2] | 4/9 |

Both CIs at net +7 **exclude zero on the losing side**. Handicap is negative in
**nine seasons out of nine**. These are not "no edge" results — they are evidence of a
reliable loss. Same direction as NRL (h2h −26.9%, handicap −5.0%), less extreme.

**Do not bet the AFL h2h or handicap matrix.**

### Totals v2: ROI rises monotonically with selectivity, at both prices

| config | CLOSE price | OPEN price |
|---|---|---|
| net +8, cells ≥5% | +1.51% (n=569) [−6.3, +9.5] | +7.04% (n=567) [−0.7, +14.8] |
| net +10, cells ≥3% | +6.37% (n=349) [−3.6, +16.5] | **+13.00%** (n=349) **[+3.1, +22.8]** |
| net +10, cells ≥5% | +9.62% (n=323) [−1.2, +20.4] | **+14.43%** (n=323) **[+4.5, +24.4]** |
| net +10, cells ≥8% | **+12.80%** (n=253) **[+1.1, +24.7]** | **+19.89%** (n=253) **[+8.6, +31.2]** |
| net +12, cells ≥5% | **+21.74%** (n=148) **[+5.9, +37.4]** | **+25.38%** (n=148) **[+10.2, +39.5]** |

This is a **dose-response across two independent parameter axes** (confluence
threshold and per-cell edge floor), consistent at both prices. That is a very different
object from a single threshold that happened to print a good number, which is what the
NRL 2026 result turned out to be.

⚠️ **This is the exact opposite of the standing AFL staking finding.** CLAUDE.md
records that the EV≥10% filter is *anti-selective* — betting everything returned more
than filtering. That is a different filter (model-vs-market disagreement); **matrix
confluence behaves the opposite way, and more of it is better.**

---

## 4. Why the OPEN beats the CLOSE — the line moves toward the picks

NRL's writeup found the reverse ("much thinner at the open") and no line movement
(**−0.09 pts** at net +8). AFL moves the other way, and it is not a pricing artefact:

- **Opening odds are not richer.** Mean O/U price 2014+ is **1.9057 at the open vs
  1.9165 at the close** (overround 104.97% vs 104.46%). The open is *tighter*, so the
  open-price advantage is not coming from a fatter price.
- **The line moves toward the picks: +1.687 pts on average**, with **64.2%** of moved
  lines going the pick's way (190 toward / 106 against / 27 flat, n=323 at net +10).
- It holds **independently on both sides** — over picks 61.2% toward, under picks
  66.3% — so it is not an artefact of a one-sided under tilt.

Two measurements of the same phenomenon agreeing: betting at the open captures a line
the market subsequently moves in your favour.

⚠️ Recorded per `feedback_roi_is_the_bar.md`: **ROI is the bar, not CLV.** The ROI at
the open clears it on its own (+14.43%, CI excluding zero); the line movement is the
supporting mechanism, not the case.

---

## 5. Clean-data subset — and the like-for-like NRL comparison

⚠️ **The odds source changes on 2 April 2018** (header: *"Pinnacle odds until April 2,
2018. bet365 odds from then on"*), and 2018 was the best single season. Restricting to
test seasons whose training windows are entirely bet365-era — **which is also exactly
NRL's 2023-26 test window**:

| | AFL totals v2, net +10 | NRL totals v2 |
|---|---|---|
| open price | **+17.01%** (n=144) **[+2.3, +31.7]**, 4/4 seasons +ve | — |
| close price | +16.01% (n=144) [−0.3, +32.5] | **−7.93%** (n=382) [−17.5, +1.5] at ≥5%/net+5 |
| | | **−0.37%** (n=230) [−12.7, +12.2] at ≥3%/net+7 |

**In the identical window, AFL is positive with a CI excluding zero; NRL straddles zero
in every configuration.** That is the answer to "is AFL better at extracting value
through matrices" — on totals at high confluence, yes.

---

## 6. 2026 alone, out of sample against the shipped 2022-25 matrices

| market | bets | strike | ROI @ close |
|---|---|---|---|
| h2h, net +7 | 63 | 61.9% | −13.23% |
| handicap, net +7 | 47 | 51.1% | −3.36% |
| totals v2, net +7 | 69 | 59.4% | +18.07% |
| totals v2, net +10 | 32 | 59.4% | **+23.09%** |

2026 is the *fourth* consecutive positive totals season, not a lone good draw — which
is the specific thing that made the NRL 2026 result untrustworthy.

---

## 7. What limits this

1. **Multiple comparisons.** Many configurations were run. The defence is not one
   good cell but the monotonic dose-response across two axes and both prices, plus
   consistency across two independent windows (9-season and bet365-only).
2. **n=148 at net +12**, n=144 in the clean-era subset. Thin.
3. **2020 was COVID-shortened** (mean total 121.2 vs 160-180). The market tracked it
   (close 122.4) so a relative metric is not distorted, but any window containing 2020
   is flagged in the walk-forward output.
4. **2026 is incomplete** — 207 home-and-away + 8 finals; the two prelims and the grand
   final are unplayed. **Do not build a 2027 matrix until the season finishes.**
5. **v1 vs v2 is not a fair contest at net ≥10** — v1 cannot reach that threshold at
   all. The claim is "v2 makes high confluence possible and high confluence pays", not
   "v2 beats v1 bet-for-bet".
6. **Nothing here is staked evidence.** These are modelled settlements at recorded
   open/close prices, not a real ledger.

---

## Recommendation

- **Stop** betting the AFL h2h and handicap matrices — both are significantly negative
  over nine seasons, handicap in 9/9.
- **Paper-track** AFL totals v2 at **net ≥10, cells ≥5%, taken at the open** for 2027
  before staking. Rebuild the matrix after the 2026 grand final.
- Keep the `--metric` flag. On AFL it buys resolution, not de-tilting.

Reproduce:
```
python scripts/afl_team_totals_matrix.py --metric hitrate
python scripts/backtest_afl_matrix_2026.py --markets totals --totals-version v2 --net 10
python scripts/walkforward_afl_matrix.py --market totals --net 10 --price open
python scripts/walkforward_afl_matrix.py --market h2h --net 7
python scripts/walkforward_afl_matrix.py --market handicap --net 7
```
