# Weekly Review — $1 Flat-Stake ROI + CLV on Every Model Pick
**NRL R19 (Jul 10–12) + AFL R18 (Jul 9–12)**
**Generated:** 2026-07-16

## Method

This is a hypothetical "$1 on every model pick" backtest, not a report on actually-placed bets
(see `data/bets/actual_bets_2026.csv` / `data/clv/running/` for real wagers). For every game in
last week's round, the model's pick in each of the three markets (H2H, handicap, totals) was
graded as a $1 flat stake:

- **Selection logic matches house convention exactly** (`scripts/nrl_weekly_clv_report.py`):
  H2H picks the side with the lower model fair odds; handicap picks whichever side the model's
  margin clears the **opening** line by; totals picks over/under vs the **opening** total line.
- **Stake price = opening odds/line** (the price that would have been available when this engine
  actually priced the round, days before kickoff).
- **Bet grading (win/loss/push) is against the opening line**, not the closing line — this is
  "would this bet have won," not "did the market end up agreeing with the model."
- **CLV** = how the opening price moved to the closing price on the specific selection taken.
  H2H CLV is a **%** (`open_odds / close_odds − 1`); handicap and totals CLV are **raw points**
  (`open_line − close_line` for the side taken), not percentages — these are different units,
  don't compare them directly.
- Source: `data/nrl/historical/raw/nrl_20260714.xlsx` and
  `BettingEngine/outputs/afl_weekly_review/historical/latest.xlsx` (aussportsbetting.com closing-line
  downloads) — a completely separate data source from the still-dead Odds API, unaffected by that outage.

Per-bet detail saved to:
- `BettingEngine/outputs/nrl_weekly_review/reports/r19_nrl_flatbet_roi_clv_2026.csv`
- `BettingEngine/outputs/afl_weekly_review/reports/r18_afl_flatbet_roi_clv_2026.csv`

---

## NRL R19 — 21 bets ($7 per market)

| Market | W-L-P | ROI | Profit | Avg CLV |
|--------|-------|-----|--------|---------|
| H2H | 5-2-0 | **+19.4%** | +$1.36 | -0.18% |
| Handicap | 5-2-0 | **+31.4%** | +$2.20 | +0.43 pts |
| Total | 5-2-0 | **+45.0%** | +$3.15 | +0.43 pts |
| **Overall** | 15-6-0 | **+31.95%** | **+$6.71** | — |

Every NRL market finished positive. Totals was the standout (+45% ROI) — the model's over/under
calls held up well against where lines closed.

## AFL R18 — 27 bets ($9 per market)

| Market | W-L-P | ROI | Profit | Avg CLV |
|--------|-------|-----|--------|---------|
| H2H | 8-1-0 | **+17.8%** | +$1.60 | -0.04% |
| Handicap | 3-6-0 | **-36.7%** | -$3.30 | -1.22 pts |
| Total | 5-4-0 | **+3.9%** | +$0.35 | +0.00 pts |
| **Overall** | 16-11-0 | **-5.00%** | **-$1.35** | — |

AFL's H2H picking was excellent (8/9), but handicap was the round's real loser (-36.7% ROI,
3/9). This lines up exactly with the model-accuracy check done earlier this session: every AFL
handicap miss was the model being **too conservative** on a blowout that ran bigger in real life
(Lions +55.3 model vs +90 actual; Crows +26.9 vs +79; Demons +39.0 vs +46) — the same
extreme-ELO-gap undercook pattern already flagged as an open item (sigmoid ELO rescale, still
backlogged). Good winner-picking doesn't help the handicap line if the model's margin ceiling is
structurally too low on the biggest mismatches.

## Combined — 48 bets

| Sport | Bets | Profit | ROI |
|-------|------|--------|-----|
| NRL | 21 | +$6.71 | +31.95% |
| AFL | 27 | -$1.35 | -5.00% |
| **Total** | **48** | **+$5.36** | **+11.17%** |

## Caveats

- **n=7 (NRL) and n=9 (AFL) games is a tiny sample** — a single result swings these ROI/CLV
  numbers hard (e.g. NRL's Dolphins 0-66 loss to Cronulla drove most of that market's CLV
  variance). Do not treat one round's ROI as a validated edge in either direction.
- This is a **backtest against real closing lines**, not a live-money result — no actual bets were
  placed. It answers "how would flat-staking every model pick have gone," which is a useful
  calibration check but not the same as the `actual_bets_2026.csv` ledger.
- AFL handicap CLV (-1.22 pts average) moving against the model's picks is consistent with, but
  not proof of, the known margin-ceiling issue — worth re-running this same backtest across more
  rounds before treating it as confirmed.
