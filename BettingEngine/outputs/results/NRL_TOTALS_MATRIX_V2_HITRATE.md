# NRL totals matrix v2 — hit rate instead of mean points

**Verdict: the fix is correct and the rule is still not profitable. Do not promote to v2 for 2027.**

## The defect in v1

Every cell in `nrl_team_totals_matrix.xlsx` compares **mean actual total** to **mean
closing line**, then calls the gap an "overs/unders edge". A totals bet settles on a
**hit rate**, not on a mean, and the total-minus-line distribution is right-skewed —
one 70-point blowout moves the mean without moving what you get paid on.

Measured over v1's own 2022–25 training window (n=840):

```
MEAN   total - line = +0.44 pts    <- what v1 reads
MEDIAN total - line = -0.50 pts
hit rate             49.8% over / 50.2% under   <- what a bet settles on
66 games landed >20 over the line   vs   45 games >20 under
```

The market was a true coin flip on hit rate, but the skew reads as an overs bias, and
**432 of 773 cells (56%) inherit it**. At net +10 on 2026, 4 of 4 signals were OVER.

## The v2 change

`scripts/nrl_team_totals_matrix.py --metric hitrate` scores each cell as over/under
strike rate against the flat 50% the line represents — the same shape the handicap
matrix already uses. Pushes are excluded from the denominator. Everything else
(sections, row labels, sample floor, 15% relative flag) is unchanged.

The tilt goes away: **v2 is 355 overs / 392 unders (48%)** against v1's 56%.

Regression: `--metric mean` reproduces the archived v1 workbook across all 1255 cells
with zero differences, so the refactor is behaviour-preserving.

## Result on 2026 alone — looked excellent, and was misleading

All 12 threshold configurations flipped positive, +5.7% to +24.0% ROI. v2 also beat
the direction-matched baseline on **both** sides (over picks 55.0% vs a 44.1% blind
baseline; under picks 68.0% vs 55.9%), so it was not merely riding an under-heavy
season. On one season it looked like a real fix that also made money.

## Walk-forward says otherwise

Rolling 4-season training window, each test season strictly out of sample, closing price:

| cells ≥5%, net +5 | 2023 | 2024 | 2025 | 2026 | pooled |
|---|---|---|---|---|---|
| v1 | −13.0% | +16.6% | −6.6% | +3.6% | +1.0% (n=252) |
| v2 | −15.4% | +3.3% | −21.6% | +7.0% | −7.9% (n=382) |

| cells ≥3%, net +7 | 2023 | 2024 | 2025 | 2026 | pooled |
|---|---|---|---|---|---|
| v1 | −33.2% | +29.8% | −19.0% | −0.1% | −4.4% (n=211) |
| v2 | −10.1% | +19.7% | −24.0% | +24.0% | −0.4% (n=230) |

Pooled ROI with bootstrap 95% CI, every configuration straddling zero:

```
cells>=5% net+5  v1 +1.02% [-10.8,+12.9]   v2 -7.93% [-17.5, +1.5]
cells>=5% net+7  v1 -5.95% [-24.8,+12.8]   v2 -3.96% [-16.5, +8.7]
cells>=3% net+5  v1 -2.44% [-12.4, +7.5]   v2 -4.26% [-13.8, +5.6]
cells>=3% net+7  v1 -4.35% [-17.1, +8.8]   v2 -0.37% [-12.7,+12.2]
```

v2 beats v1 in two configs and loses in two. Season ROI swings from −24% to +24% with
no persistence. 2026 was the good draw, not the new normal.

## Conclusion

The v1 metric was genuinely wrong and v2 is the right way to compute the sheet — keep
the `--metric` flag. But correcting it does not create an edge, because there was never
an edge to uncover: the closing line already prices these buckets to a coin flip. This
matches the H2H (−26.9%) and handicap (−5.0%) findings from the same 2026 test.

Do not stake the totals matrix in 2027 on either metric.

Reproduce:
```
NRL_HISTORICAL_XLSX=outputs/nrl_weekly_review/historical/latest.xlsx \
  python scripts/nrl_team_totals_matrix.py --metric hitrate
python scripts/backtest_nrl_matrix_net7_2026.py --markets totals --net 7 --totals-version v2
```

---

# 2026 single-season test (owner's criterion) and the 2027 build

The owner's decision is to judge v2 on 2026 ROI and, if it passes, carry it into 2027
retrained with 2026 included. It passes. Recorded here with the caveats attached.

## 2026 result, v2

| net | bets | W-L | strike | ROI @ close | ROI @ open |
|-----|------|-----|--------|-------------|------------|
| +10 | 12 | 7-5 | 58.3% | **+18.92%** | +16.08% |
| +8 | 32 | 18-14 | 56.2% | **+12.06%** | +4.22% |
| +7 | 43 | 23-20 | 53.5% | +5.70% | −0.37% |
| +5 | 76 | 41-35 | 53.9% | +7.03% | +3.04% |

Cells ≥5% edge (the production confluence threshold). Positive at every threshold at
the close; much thinner at the open, which is where bets actually get placed.

**Closing-line value is negative at every threshold** (−1.34% to −1.60%) and the line
does not move toward the picks (avg −0.09 pts at net +8). The 2026 profit came from
results, not from the market agreeing. ROI is the bar here, not CLV, so this does not
disqualify it — but it means there is no second, independent signal supporting it.

Month ROI at net +8 swings +49% / +10% / −5% / +3% / −31% / +6% / +107%.

## 2027 matrix — BUILT, then DELETED 2026-09-14 (owner's call)

⚠️ **`outputs/nrl_team_totals_matrix_v2_2027.xlsx` HAS BEEN DELETED.** Once the net+10/+12
walk-forward below showed no edge at any threshold, the owner's call was that a sheet
which does not produce an edge is not worth carrying. Recoverable from git history if
ever needed; rebuild command is below. The record of what it contained is kept here.

It was trained on a rolling 4-season window
**2023–2026**, metric `hitrate`. Sheet titles are now dynamic and carry the window and
metric, so a matrix can no longer silently claim the wrong training seasons.

**1. It must be rebuilt after the 2026 grand final.** The source file holds 204 games
for 2026, last dated 6 Sep, against 213 in each of 2023–25 — the finals series is still
being played. The current build is missing roughly nine games.

```
NRL_HISTORICAL_XLSX=outputs/nrl_weekly_review/historical/latest.xlsx \
  python scripts/nrl_team_totals_matrix.py --metric hitrate \
  --seasons 2023,2024,2025,2026 --out outputs/nrl_team_totals_matrix_v2_2027.xlsx
```

**2. Adding 2026 tilts the sheet hard toward UNDER.** The 2023–26 window is
**278 overs / 458 unders (38% overs)**, against 48% for 2022–25. 2026 was the most
under-heavy season in the file (55.9% unders, versus 44.8–52.6% in the seven prior
seasons), so that tilt is inherited from one outlier year. This is the same shape as
the v1 defect being fixed here — a structural lean absorbed from the training window
rather than measured from an edge — and it is the first thing to check if 2027 runs
badly.

## Standing caveat

Walk-forward over 2023–26 pools between −7.9% and −0.4% with every CI straddling zero,
and 2026 is the only clearly positive season. The 2026 figures above are the basis for
the decision to proceed; they are not evidence that the pooled result is wrong.
Recommend tracking 2027 selections paper-only until the season has enough bets to
compare against these numbers.

---

# ADDENDUM 2026-09-14 — net +10 and +12 WERE never walk-forwarded. Now they are.

The walk-forward above stops at **net +7**. The +18.92% at net +10 in the 2026 table
was **one season, 12 bets**. The AFL repeat of this study
(`AFL_TOTALS_MATRIX_V2_HITRATE.md`) found AFL's edge living specifically at net >=10
and *climbing* with selectivity, so the untested threshold was worth closing out.

Driver: `scripts/walkforward_nrl_matrix.py`, which shells out to the unmodified
`backtest_nrl_matrix_net7_2026.py`. **Validated first** by reproducing the published
cells>=5%/net+5 row exactly: −15.3 / +3.3 / −21.6 / +7.0, pooled −7.93%, n=382.

Rolling 4-season window, **10 test seasons 2017-2026** (NRL carries closing totals
from 2013), v2/hitrate:

| config | pooled ROI | n | 95% CI | seasons +ve |
|---|---|---|---|---|
| net +8, open | +0.99% | 446 | [−7.7, +10.0] | 5/10 |
| net +10, close | −3.49% | 209 | [−16.4, +9.1] | 5/10 |
| net +10, open | −1.34% | 209 | [−14.2, +11.2] | 5/10 |
| net +10, cells ≥8%, open | −7.60% | 157 | [−22.4, +7.6] | 5/10 |
| net +12, open | +6.36% | 70 | [−15.8, +28.5] | 6/10 |

**Conclusion unchanged, now tested at every threshold: there is no edge at any level of
confluence.** The series wobbles around zero (+0.99 → −1.34 → −7.60 → +6.36) with every
CI straddling zero and roughly 5 of 10 seasons positive throughout — a coin flip.

**Critically, NRL shows NO dose-response.** AFL's ROI climbs monotonically with
selectivity (+7.0 → +13.0 → +14.4 → +19.9 → +25.4 at the open); NRL's does not move in
any direction. That is a **negative control passing**: the same harness, run on NRL,
manufactures nothing. It makes the AFL result more credible, not less.

2026's +18.92% reproduces exactly and sits inside a series swinging +45.6% to −45.8%.
It was a good draw, as this document already concluded.

---

# END-OF-SEASON REVIEW 2026 — ALL THREE NRL MARKETS WALK-FORWARDED, MATRICES RETIRED

The addendum above closed the totals threshold gap. This closes the remaining one:
**h2h and handicap had never been walk-forwarded at all.** Their published figures
(−26.9% and −5.0%) were **2026 alone**. The AFL study held every market to a 9-season
walk-forward before concluding, so NRL is brought to the same standard before any
decision is taken.

## ⚠️ A data gap found on the way, which changed the numbers

The NRL history is **missing H2H and LINE-ODDS closing prices for 70% of 2024
(64/213) and 99.5% of 2025 (1/213)**. Totals coverage is complete in every season.

On the first run those seasons entered as **silent zeros** — 2025 produced 0 bets and
reported "+0.00% ROI", which reads as a flat season rather than as no data. This is
DATA_INTEGRITY_LESSONS #8 (silent coverage gaps) landing in a live analysis.
`--skip-seasons` was added and **every h2h/handicap figure below excludes 2024-25.**
Totals is unaffected and still uses all 10 seasons.

## Results — rolling 4-season window, each test season out of sample

| market | net | pooled ROI | n | 95% CI | seasons +ve |
|---|---|---|---|---|---|
| h2h | +7 | −4.95% | 449 | [−12.4, +2.7] | 2/8 |
| h2h | +10 | +0.26% | 161 | [−11.5, +12.5] | 5/8 |
| **handicap** | **+7** | **−12.52%** | 419 | **[−21.7, −3.4]** | **0/8** |
| handicap | +10 | −11.96% | 136 | [−27.6, +4.4] | 2/8 |
| totals | +8 open | +0.99% | 446 | [−7.7, +10.0] | 5/10 |
| totals | +10 open | −1.34% | 209 | [−14.2, +11.2] | 5/10 |
| totals | +12 open | +6.36% | 70 | [−15.8, +28.5] | 6/10 |

**Handicap loses significantly** — its CI excludes zero and it is negative in eight
seasons out of eight. h2h and totals sit on zero. **No market shows a dose-response**
at any threshold, which is the specific property AFL totals does show.

## Decision (owner, 2026-09-14): RETIRED FROM PRODUCTION

Removed from the pipeline:

- `prepare_round.py` — Step 8 (regenerate matrices) and Step 9 (push to Supabase),
  their helpers, and the `--skip-matrices` flag. An in-place comment records the
  measured reason so it is not re-added without the numbers.
- `push_matrices_to_supabase.py` — deleted (NRL-only).
- `matrix_confluence.py` — retirement banner, kept as research tooling only.
- Web: `app/api/ev-signals/route.ts`, `lib/matrixEV.ts` and the GameCard value-edge
  badges, which were fed exclusively by these matrices.

**Kept:** the builders, the backtest and `walkforward_nrl_matrix.py`, so the question
can be re-opened with evidence rather than rebuilt from scratch. `--validate`
reproduces the published totals row and exits non-zero on mismatch.

⚠️ **AFL IS UNAFFECTED.** AFL totals at net ≥10 is the one matrix result that survived
walk-forward in either sport — see `AFL_TOTALS_MATRIX_V2_HITRATE.md`.

Reproduce:
```
python scripts/walkforward_nrl_matrix.py --validate
python scripts/walkforward_nrl_matrix.py --market h2h      --net 7 --skip-seasons 2024,2025
python scripts/walkforward_nrl_matrix.py --market handicap --net 7 --skip-seasons 2024,2025
python scripts/walkforward_nrl_matrix.py --market totals   --net 10 --price open
```
