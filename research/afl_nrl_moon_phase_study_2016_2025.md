# AFL/NRL full-moon and new-moon study

This study uses the ten completed seasons **2016–2025** from the historical
odds workbooks:

- `data/afl/historical/raw/afl_20260915.xlsx`
- `data/nrl/historical/raw/nrl_20260915.xlsx`

For each match, a full moon or new moon is the astronomical date plus or minus
one calendar day. Totals use the recorded total score and the closing total
line. H2H uses the closing home/away prices. Handicap line beat is calculated
as `home margin + closing home line`; positive values cover. Flat ROI assumes a
$1 stake at the recorded closing decimal odds. These are exploratory
comparisons, not a staking rule.

## AFL

### Totals

| Window | Games | Average total | Median | Over rate | Over ROI |
|---|---:|---:|---:|---:|---:|
| Full moon ±1 day | 222 | 167.18 | 169.5 | 53.15% | +1.38% |
| Other games | 1,830 | 163.97 | 163.5 | 48.14% | −8.00% |
| New moon ±1 day | 198 | 165.25 | 167.0 | 48.99% | −6.17% |
| Other games | 1,854 | 164.22 | 164.0 | 48.65% | −7.07% |

Full moon was **+3.21 points** versus other games (Welch p=0.158; Mann–Whitney
p=0.066). New moon was **+1.03 points** (Welch p=0.661; Mann–Whitney p=0.493).

### Home H2H favourites

| Window | Games | Wins | Win rate | Flat ROI |
|---|---:|---:|---:|---:|
| Full moon ±1 day | 137 | 99 | 72.26% | +0.46% |
| Other games | 1,110 | 782 | 70.45% | −2.51% |
| New moon ±1 day | 124 | 89 | 71.77% | +1.41% |
| Other games | 1,123 | 792 | 70.53% | −2.59% |

Neither phase showed a meaningful difference in the home-favourite subset.

### Home handicap favourites

This section restricts to negative closing home lines (the home team laying
points).

| Window | Games | Average line beat | ATS rate | Flat ROI |
|---|---:|---:|---:|---:|
| Full moon ±1 day | 137 | +1.38 | 50.36% | −3.52% |
| Other games | 1,121 | −1.35 | 48.26% | −7.30% |
| New moon ±1 day | 124 | +0.82 | 54.03% | +3.76% |
| Other games | 1,134 | −1.25 | 47.88% | −8.05% |

Mean line-beat tests were inconclusive (full p=0.346; new p=0.510).

## NRL

### Totals

| Window | Games | Average total | Median | Over rate | Over ROI |
|---|---:|---:|---:|---:|---:|
| Full moon ±1 day | 202 | 43.94 | 42.0 | 47.52% | −9.19% |
| Other games | 1,812 | 43.21 | 42.0 | 49.06% | −6.07% |
| New moon ±1 day | 203 | 41.21 | 40.0 | 41.38% | −21.16% |
| Other games | 1,811 | 43.52 | 42.0 | 49.75% | −4.72% |

Full moon was **+0.73 points** (Welch p=0.473; Mann–Whitney p=0.678). New moon
was **−2.31 points** (Welch p=0.027; Mann–Whitney p=0.008). New-moon unders
won 118/203 (58.13%) for +11.28% flat ROI, compared with 49.86% and −4.30% on
other days.

### Home H2H favourites

| Window | Games | Wins | Win rate | Flat ROI |
|---|---:|---:|---:|---:|
| Full moon ±1 day | 105 | 72 | 68.57% | −0.92% |
| Other games | 886 | 635 | 71.67% | +1.56% |
| New moon ±1 day | 107 | 80 | 74.77% | +8.20% |
| Other games | 884 | 627 | 70.93% | +0.46% |

The phase comparisons were not statistically conclusive (full Fisher p=0.496;
new Fisher p=0.431).

### Home handicap favourites

Negative closing home lines only.

| Window | Games | Average line beat | ATS rate | Flat ROI |
|---|---:|---:|---:|---:|
| Full moon ±1 day | 105 | −1.71 | 44.76% | −11.48% |
| Other games | 896 | +0.66 | 49.11% | −4.77% |
| New moon ±1 day | 106 | +2.31 | 57.55% | +11.15% |
| Other games | 895 | +0.19 | 47.60% | −7.44% |

Mean line-beat tests were inconclusive (full p=0.156; new p=0.208).

The strongest exploratory result is the NRL new-moon totals/under pattern. It
requires a time-split out-of-sample test and controls for season, venue, market
line and rule changes before being used operationally.
