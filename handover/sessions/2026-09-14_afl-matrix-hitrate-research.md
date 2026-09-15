# 2026-09-14 — AFL matrices: the NRL hit-rate study, repeated

Branch `research/afl-totals-matrix-v2-hitrate` (pushed). Owner's ask: *"can we do
the same research we did on the nrl to the afl... i wanna see if the afl is better
at extracting value through matrices."*

**Short answer: not broadly — h2h and handicap lose reliably on AFL exactly as they
do on NRL. But AFL totals at HIGH confluence is the one place either sport shows a
walk-forward edge that survives, and it is strongest at the OPENING price, which is
the inverse of the NRL result.**

Full writeup with every figure:
`BettingEngine/outputs/results/AFL_TOTALS_MATRIX_V2_HITRATE.md`

## The framing that changed on contact with the data

The NRL v2 fix existed because NRL totals are **right-skewed** — a blowout moves the
mean without moving what a bet settles on, so 56% of v1 cells inherited a phantom
overs tilt. **AFL does not have that defect.** AFL mean total−line is −0.01 against a
median of +0.50 (NRL: +0.44 / −0.50), 200 games landed >20 over vs 208 >20 under
(NRL 66 vs 45), and v1's cells were already 380 overs / 382 unders. The two sports
are skewed in *opposite* directions.

**So on AFL the hit-rate metric earns its place for a different reason: resolution,
not de-tilting.** A hit rate almost never lands exactly on 50.0 where a mean total
often equals the mean line, so v2 emits far more directional cells. The practical
consequence is that **v1 cannot reach high confluence at all** — 34 bets at net +7
across nine seasons, 2 at net +10, against v2's 718 and 323. The headline result
below does not exist under v1.

## Results (9-season walk-forward, 4-season rolling window, each season out of sample)

| market | pooled ROI | n | 95% CI | seasons +ve |
|---|---|---|---|---|
| h2h net +7 | **−8.17%** | 498 | **[−15.9, −0.5]** | 3/9 |
| handicap net +7 | **−10.54%** | 425 | **[−19.5, −1.5]** | **0/9** |
| totals v2 net +10 close | +9.62% | 323 | [−1.2, +20.4] | 6/9 |
| totals v2 net +10 open | **+14.43%** | 323 | **[+4.5, +24.4]** | 7/9 |
| totals v2 net +12 open | **+25.38%** | 148 | **[+10.2, +39.5]** | 8/9 |

h2h and handicap CIs **exclude zero on the LOSING side** — that is evidence of a
reliable loss, not "no edge". Handicap is negative in nine seasons out of nine.

Totals shows a **monotonic dose-response across two independent axes** (confluence
threshold and per-cell edge floor), at both prices. That is what separates it from
the NRL 2026 result, which was a single good season that walk-forward destroyed.

⚠️ **This is the opposite of the standing AFL staking finding.** CLAUDE.md records the
EV≥10% filter as *anti-selective* (betting everything beat filtering). Matrix
confluence behaves the other way — more of it is better. Different filter, opposite
sign; both can be true.

## Why the open beats the close — and how it was checked

NRL found the reverse ("thinner at the open") with no line movement (−0.09 pts). AFL:

- **+1.687 pts** of favourable line movement at net +10; **64.2%** of moved lines went
  the pick's way (190 toward / 106 against / 27 flat).
- Holds **independently on both sides** — over 61.2%, under 66.3% — so it is not an
  artefact of a one-sided under tilt.
- **Opening odds are tighter, not richer** (mean 1.9057 open vs 1.9165 close;
  overround 104.97% vs 104.46%), so the open-price ROI is not a fatter-price artefact.

⚠️ I got the CLV sign backwards on the first pass and reported it to myself as −1.687
with 35.8% toward. For an OVER bet a *rising* line is favourable. Caught by working the
convention through a concrete example before trusting the number — DATA_INTEGRITY
LESSONS #6, the checking tool is also code. Per `feedback_roi_is_the_bar.md` the ROI is
the bar here; the line movement is the supporting mechanism, not the case.

## Like-for-like against NRL

Restricted to test seasons whose training windows are entirely bet365-era — **which is
also exactly NRL's 2023-26 window**:

| | AFL totals v2 net +10 | NRL totals v2 |
|---|---|---|
| open | **+17.01%** (n=144) **[+2.3, +31.7]**, 4/4 +ve | — |
| close | +16.01% (n=144) [−0.3, +32.5] | −7.93% (n=382) and −0.37% (n=230), all CIs straddling zero |

## Repo fixes that came with it

All three AFL matrix builders had **hardcoded machine-specific paths**
(`/Users/elliotbladen/Downloads/afl (2) (1).xlsx`, output to `~/Betting_model/`) — they
could not run on the other machine and wrote outside the repo. All three now take
`--seasons` / `--source` / `--out` and default to repo-relative paths, with
`AFL_HISTORICAL_XLSX` honoured.

**Regression-gated, rebuilt from the original source against the shipped artefacts:**
totals 7,362 data cells, h2h 7,362 data cells, handicap 1,155 csv rows — **zero
differences each.**

Also: the AFL totals builder silently fell back from Total-Score-Close to
Total-Score-Open when the close was missing (lesson #7). It now counts and reports that
fallback. On the current file it never fires.

## Data checks worth keeping

- ⚠️ **AFL column layout is NOT the NRL layout.** AFL carries Goals/Behinds in I-L where
  NRL carries Over Time, so every market column sits **+2** on the NRL index from "Home
  Odds Open" on. Verified off the header row, not derived. `backtest_afl_matrix_2026.py`
  asserts the layout on load and exits if it shifts.
- ⚠️ **Odds source changes 2 April 2018** (Pinnacle → bet365) — and 2018 was the best
  single season. The bet365-only subset is still positive, which is why it is reported.
- ⚠️ **2020 was COVID-shortened**, mean total 121.2 vs 160-180. The market tracked it
  (close 122.4) so a relative metric is not distorted, but windows containing 2020 are
  flagged in the walk-forward output.
- Row-label coverage was verified before trusting any ROI: 18/18 team sheets matched,
  hit rates 92.5% (h2h), 98.4% (handicap), 89.7% (totals v2). A silent name mismatch
  would have produced plausible ROI from almost no cells.

## Limits

n=148 at net +12 and n=144 in the clean-era subset — thin. Many configurations were
run, so the defence is the dose-response and the two-window consistency, not any single
cell. **2026 is incomplete** (207 H&A + 8 finals; both prelims and the GF unplayed) —
**do not build a 2027 matrix until the season finishes.** Nothing here is staked
evidence; these are modelled settlements at recorded prices.

## Recommendation

1. **Stop** betting the AFL h2h and handicap matrices.
2. **Paper-track** AFL totals v2 at **net ≥10, cells ≥5%, taken at the open** through
   2027 before staking. Rebuild the matrix after the 2026 grand final.
3. Keep `--metric`. On AFL it buys resolution, not de-tilting.

## Follow-up in the same session — the NRL threshold that was never tested

Owner asked whether NRL had actually been positive. It had been, on **2026 alone**
(+18.92% at net +10, 12 bets) — and the published NRL walk-forward **stopped at net
+7**, so net +10 had never been tested across seasons.

`scripts/walkforward_nrl_matrix.py` closes that out, driving the **unmodified**
`backtest_nrl_matrix_net7_2026.py`. Validated first by reproducing the published
cells>=5%/net+5 row exactly (−15.3 / +3.3 / −21.6 / +7.0, pooled −7.93%, n=382).

Over **10 test seasons (2017-2026)**: net+8 open +0.99% (n=446); net+10 close −3.49%
(n=209); net+10 open −1.34% (n=209); net+10 cells>=8% −7.60% (n=157); net+12 open
+6.36% (n=70). **Every CI straddles zero, ~5/10 seasons positive throughout.**

**NRL shows NO dose-response** where AFL climbs monotonically with selectivity. Same
harness, nothing manufactured on NRL — **a negative control passing**, which
strengthens the AFL result rather than weakening it. Addendum appended to
`NRL_TOTALS_MATRIX_V2_HITRATE.md` so the next reader does not re-form the old
impression from the 2026 row.

**Owner's call: AFL matrices are for TOTALS ONLY.** Branch merged to main.

## Next

- Port the NRL local viewer (`_nrl_totals_v2_viewer.py`) to AFL if the sheets want
  browsing — not done, purely cosmetic.
- The h2h/handicap builders are now parameterised but their **matrices have not been
  rebuilt** in `outputs/` — the shipped 2022-25 artefacts are untouched and still
  reproduce byte-identically.
- 255 tests: 244 pass, same 3 pre-existing pyarrow failures as before this work.
