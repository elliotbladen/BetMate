# EPL GW3 + EFL Championship GW5 — saved selections graded vs the closing line

**Graded:** 2026-09-08
**Sources:** `outputs/football/epl/gw3_10pct_ev_candidates_2026-09-03.csv` (7 rows)
and `outputs/football/championship/gw5_bets_injury_adjusted_2026-09-03.csv`
(5 rows, `status = active_saved_selection`).

**Conventions** (same as the 2026-09-02 football CLV work): closing odds are the
**average closing** columns (`AvgCH/AvgCD/AvgCA`, `AvgC>2.5`) from
football-data.co.uk; stake is the `stake_units` on the saved row; a losing bet
returns zero; `CLV% = saved_price / closing_odds − 1`.

Driver: `scripts/score_football_saved_bets.py`.

---

## EPL GW3

| Match | Selection | Took | Close | CLV | Score | Result | P&L |
|---|---|---:|---:|---:|---:|:--:|---:|
| Ipswich v Liverpool | Ipswich win | 5.50 | 4.86 | +13.17% | 0–2 | ❌ | −1.00 |
| Brentford v Sunderland | Sunderland win | 5.50 | 4.89 | +12.47% | 1–1 | ❌ | −1.00 |
| Hull v Aston Villa | Hull win | 4.10 | 3.92 | +4.59% | 0–0 | ❌ | −1.00 |
| Everton v Man United | Everton win | 3.10 | 3.65 | **−15.07%** | 2–2 | ❌ | −1.00 |
| Newcastle v Bournemouth | Over 2.5 | 1.57 | 1.58 | −0.63% | 2–2 | ✅ | +0.57 |
| Everton v Man United | Over 2.5 | 1.70 | 1.57 | +8.28% | 2–2 | ✅ | +0.70 |
| Arsenal v Chelsea | Over 2.5 | 2.00 | 1.71 | +16.96% | 2–1 | ✅ | +1.00 |

**7 bets · 3W-4L (42.9%) · staked 7.00u · P&L −1.73u · ROI −24.71% · avg CLV +5.68% · beat close 5/7**

## EFL Championship GW5

| Match | Selection | Took | Close | CLV | Score | Result | P&L |
|---|---|---:|---:|---:|---:|:--:|---:|
| Stoke v Charlton | Charlton win | 3.48 | 3.86 | −9.84% | 4–0 | ❌ | −1.00 |
| Millwall v Bolton | Bolton win | 6.00 | 3.78 | **+58.73%** | 4–0 | ❌ | −1.00 |
| Sheffield United v Norwich | Sheff Utd win (1.5u, +6 matrix) | 2.50 | 2.56 | −2.34% | 1–3 | ❌ | −1.50 |
| Swansea v Wrexham | Swansea win | 2.50 | 2.24 | +11.61% | 0–0 | ❌ | −1.00 |
| Birmingham v Wolves | Birmingham win | 2.99 | 2.85 | +4.91% | 2–2 | ❌ | −1.00 |

**5 bets · 0W-5L · staked 5.50u · P&L −5.50u · ROI −100.00% · avg CLV +12.61% · beat close 3/5**

## Combined

| | Value |
|---|---:|
| Bets | 12 |
| Record | 3W-9L (25.0%) |
| Staked | 12.50u |
| P&L | **−7.23u** |
| **ROI** | **−57.84%** |
| **Average CLV** | **+8.57%** |
| Beat the close | 8/12 (66.7%) |

---

## Read

**The market agreed with us and we still lost.** +8.57% average CLV and beating
the close on two-thirds of the card is a genuinely good price-capture week; a
−57.84% ROI on the same card is a bad one. Over 12 bets that divergence is noise,
not a contradiction — but it is worth recording which of the two signals the
project trusts, because they point in opposite directions here.

**The 1X2 engine went 0-for-9, and five of those nine ended in a draw.**

| Match | Selection | Score |
|---|---|---|
| Brentford v Sunderland | Sunderland win | 1–1 |
| Hull v Aston Villa | Hull win | 0–0 |
| Everton v Man United | Everton win | 2–2 |
| Swansea v Wrexham | Swansea win | 0–0 |
| Birmingham v Wolves | Birmingham win | 2–2 |

Every 1X2 selection on the card was a win-side bet; none was a draw. Backing nine
win sides and having five drawn is the signature of a model under-weighting the
draw, and `ml/football/leagues/championship.yaml` already carries an open note on
exactly this parameter: `rho: -0.13  # start at EPL value; revisit vs ~33% draw
rate`. Dixon-Coles `rho` governs low-score draw inflation and has never been
refit for the Championship. This weekend is one round of evidence pointing at it,
not proof — but it is the first place to look.

**O/U 2.5 went 3-for-3** (+8.20% avg CLV). The totals side of the engine was the
only thing that worked, which is the mirror image of the AFL model, where totals
are the weakest market.

**Two prices worth noting individually.** Bolton drifted our way hard — taken at
6.00, closed 3.78, +58.7% CLV — and lost 0–4, so the market's move was simply
wrong. Everton went the other way, taken at 3.10 and closing 3.65 (−15.1%), the
only materially negative capture on the card, and drew. The Sheffield United bet
was the one carrying a 1.5u stake on a +6 matrix confluence and lost 1–3, so the
matrix upweighting cost an extra half unit.

---

## Caveats

- **12 bets is far too small to conclude anything.** Treat the draw pattern as a
  hypothesis to test against the full season, not a finding.
- Closing odds are market-average, not the price actually available at the close
  at any one book, so CLV here is a consensus measure.
- The EFL card is the **injury-adjusted** file (5 selections). The earlier
  pre-injury file held 6 — Lincoln v Southampton dropped out of the active set,
  and it finished 1–1, which would have been a sixth losing draw.

---

## Price capture — vs OPEN as well as vs CLOSE

`vs OPEN = saved_price / opening_odds − 1` — did the price we took beat the
opening consensus? `Market drift = closing / opening − 1` — which way the market
then moved. Opening odds are football-data `AvgH/AvgD/AvgA` and `Avg>2.5`.

### EPL GW3

| Match | Selection | Open | Took | Close | vs OPEN | vs CLOSE | Market drift | Result | P&L |
|---|---|---:|---:|---:|---:|---:|---:|:--:|---:|
| Ipswich v Liverpool | Ipswich win | 5.48 | 5.50 | 4.86 | +0.36% | +13.17% | -11.31% | ❌ | -1.00 |
| Brentford v Sunderland | Sunderland win | 5.29 | 5.50 | 4.89 | +3.97% | +12.47% | -7.56% | ❌ | -1.00 |
| Hull v Aston Villa | Hull win | 4.04 | 4.10 | 3.92 | +1.49% | +4.59% | -2.97% | ❌ | -1.00 |
| Everton v Man United | Everton win | 3.21 | 3.10 | 3.65 | -3.43% | -15.07% | +13.71% | ❌ | -1.00 |
| Newcastle v Bournemouth | Over 2.5 | 1.55 | 1.57 | 1.58 | +1.29% | -0.63% | +1.94% | ✅ | +0.57 |
| Everton v Man United | Over 2.5 | 1.67 | 1.70 | 1.57 | +1.80% | +8.28% | -5.99% | ✅ | +0.70 |
| Arsenal v Chelsea | Over 2.5 | 1.73 | 2.00 | 1.71 | +15.61% | +16.96% | -1.16% | ✅ | +1.00 |

| Measure | Value |
|---|---:|
| Bets | 7 (3W / 4L, 42.9%) |
| Staked / P&L | 7.00u / **-1.73u** |
| ROI | **-24.71%** |
| **vs OPEN** | **+3.01%** — beat the open 6/7 |
| **vs CLOSE (CLV)** | **+5.68%** — beat the close 5/7 |

### EFL Championship GW5

| Match | Selection | Open | Took | Close | vs OPEN | vs CLOSE | Market drift | Result | P&L |
|---|---|---:|---:|---:|---:|---:|---:|:--:|---:|
| Stoke v Charlton | Charlton win | 3.49 | 3.48 | 3.86 | -0.29% | -9.84% | +10.60% | ❌ | -1.00 |
| Millwall v Bolton | Bolton win | 4.19 | 6.00 | 3.78 | +43.20% | +58.73% | -9.79% | ❌ | -1.00 |
| Sheffield United v Norwich | Sheffield United win (+6 matrix) | 2.53 | 2.50 | 2.56 | -1.19% | -2.34% | +1.19% | ❌ | -1.50 |
| Swansea v Wrexham | Swansea win | 2.17 | 2.50 | 2.24 | +15.21% | +11.61% | +3.23% | ❌ | -1.00 |
| Birmingham v Wolves | Birmingham win | 2.87 | 2.99 | 2.85 | +4.18% | +4.91% | -0.70% | ❌ | -1.00 |

| Measure | Value |
|---|---:|
| Bets | 5 (0W / 5L, 0.0%) |
| Staked / P&L | 5.50u / **-5.50u** |
| ROI | **-100.00%** |
| **vs OPEN** | **+12.22%** — beat the open 3/5 |
| **vs CLOSE (CLV)** | **+12.61%** — beat the close 3/5 |

### Combined


| Measure | Value |
|---|---:|
| Bets | 12 (3W / 9L, 25.0%) |
| Staked / P&L | 12.50u / **-7.23u** |
| ROI | **-57.84%** |
| **vs OPEN** | **+6.85%** — beat the open 9/12 |
| **vs CLOSE (CLV)** | **+8.57%** — beat the close 8/12 |

**Read.** We beat the open on **9 of 12** and the close on **8 of 12**, averaging
**+6.85% vs open** and **+8.57% vs close**. Both are positive, and the close figure
being the larger of the two means the market on balance moved *toward* our
selections after we took them — the definition of good timing.

Two bets carried the average: **Millwall/Bolton** (took 6.00 against a 4.19 open,
+43.2%) and **Arsenal/Chelsea Over 2.5** (2.00 against 1.73, +15.6%). Both look like
a genuinely better book price rather than an early-market edge. Strip those two out
and the remaining ten average roughly **+0.4% vs open** — i.e. we were taking
consensus prices, not beating the market.

**Everton win is the one clear timing loss:** taken at 3.10 against a 3.21 open, and
it drifted out to 3.65. Worse than the open *and* worse than the close, on a bet
that then drew. Stoke/Charlton is the same shape, smaller.
