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

## 2027 matrix — BUILT, with two conditions

`outputs/nrl_team_totals_matrix_v2_2027.xlsx`, trained on a rolling 4-season window
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
