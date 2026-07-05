# 2026-05-06 - AFL/NRL CLV Automation Handover

## What Was Set Up

Built the AFL equivalent of the NRL weekly CLV process and added a combined running CLV summary.

The workflow now covers:

- AFL historical results/odds workbook download from AusSportsBetting.
- AFL weekly CLV comparison between:
  - normal/rules engine
  - ML shadow engine
  - market open-to-close move
- NRL weekly CLV comparison already remains in place.
- Combined NRL/AFL running CLV summary.

## New/Updated Scripts

- `scripts/fetch_aussportsbetting_nrl.py`
  - Generalised enough to also download AFL workbooks.
  - Fixed Playwright fallback after FortiGuard/content-filter proceed.
  - Added cookie banner acceptance.
  - Fixed relative output path handling.

- `scripts/afl_weekly_ml_clv_report.py`
  - Reads `outputs/afl_weekly_review/historical/latest.xlsx`.
  - Reads AFL normal + ML prices from `data/model.db`, table `afl_shadow_predictions`.
  - Auto-detects latest completed AFL round by checking workbook scores.
  - Writes one CSV row per game/market/signal.

- `scripts/rolling_clv_summary.py`
  - Reads NRL and AFL weekly comparison CSVs.
  - Outputs round-by-round CLV plus cumulative running average.
  - User clarified this should be cumulative average, not rolling 3-round window.

- `scripts/install_aussportsbetting_afl_task.ps1`
  - Installs Tuesday AFL workbook download.

- `scripts/install_afl_weekly_ml_clv_task.ps1`
  - Installs Tuesday AFL normal-vs-ML-vs-market CLV report.

- `scripts/install_rolling_clv_summary_task.ps1`
  - Installs Tuesday combined running CLV summary.

## Scheduled Tasks

Installed and verified:

- `BettingEngine AusSportsBetting AFL Download`
  - Tuesday 09:02
  - Downloads AFL workbook to `outputs/afl_weekly_review/historical/latest.xlsx`.

- `BettingEngine AFL Weekly ML CLV Report`
  - Tuesday 09:10
  - Writes `outputs/afl_weekly_review/reports/r{round}_afl_ml_clv_comparison_2026.csv`.

- `BettingEngine Running CLV Summary`
  - Tuesday 09:15
  - Writes `outputs/clv_running/running_clv_summary.csv`.

Existing NRL tasks from prior work:

- `BettingEngine AusSportsBetting NRL Download`
  - Tuesday 09:00

- `BettingEngine NRL Weekly CLV Report`
  - Tuesday 09:05

- `BettingEngine NRL Weekly ML CLV Report`
  - Tuesday 09:07

## Current Outputs

Downloaded AFL workbook:

- `outputs/afl_weekly_review/historical/latest.xlsx`
- `outputs/afl_weekly_review/historical/afl_20260506_105434.xlsx`
- `outputs/afl_weekly_review/historical/latest.json`

AFL CLV report test run:

- `outputs/afl_weekly_review/reports/r8_afl_ml_clv_comparison_2026.csv`

Running CLV summary:

- `outputs/clv_running/running_clv_summary.csv`

## Current Running CLV Snapshot

Normal engine:

| Sport | Round | H2H | Handicap | Total |
|---|---:|---:|---:|---:|
| AFL | R8 | -0.005 | +1.4444 pts | -2.6667 pts |
| NRL | R10 | +0.075 | +1.5000 pts | +0.7500 pts |

Interpretation agreed with user:

- H2H CLV is odds/decimal CLV.
- Handicap and total CLV are line points.
- AFL handicap +1.44 pts is good, but not elite.
- AFL mature target discussed: +2 pts good, +3 strong, +4.5 excellent.

## AFL R9 Pricing Context

Fresh AFL R9 prices exported:

- `outputs/afl_round_prep/r9_2026/afl_r9_pricing_2026.csv`

Normal engine highlights:

- Fremantle -4.6, total 184.8
- Brisbane -60.8, total 183.6
- Bulldogs -14.8, total 172.1
- Sydney -21.6, total 203.0
- GWS -45.2, total 174.3
- Gold Coast -48.9, total 180.2
- Geelong -23.2, total 174.8
- Melbourne -45.2, total 167.2
- Adelaide -52.9, total 150.0

ML shadow key disagreement:

- Port Adelaide vs Western Bulldogs:
  - normal: Bulldogs by 14.8
  - ML: Port by 18.1
  - H2H/handicap matrices also leaned Port.

## Matrix Research Notes

For AFL R9, venue-specific research was tightened after user pushed back.

Best side matrix spots:

- Port Adelaide vs Western Bulldogs at Adelaide Oval
  - Bulldogs at Adelaide Oval H2H: 100% opposing, n=5
  - Bulldogs at Adelaide Oval handicap: 100% fades, n=5
  - Port vs Bulldogs handicap: 60% Port covers, n=5
  - Lean: Port side/handicap, but note normal engine disagrees.

- Gold Coast vs St Kilda at TIO Stadium
  - Gold Coast at TIO H2H: 62.3% backing, n=8
  - Gold Coast at TIO handicap: 75% covers, n=8
  - Lean: Gold Coast side/handicap.

- Fremantle vs Hawthorn at Optus Stadium
  - Hawthorn at Optus H2H: 35.9% opposing, n=4
  - Fremantle vs Hawthorn H2H: 26.2% backing, n=5
  - Lean: Fremantle, lower confidence due sample.

Totals matrix:

- Gold Coast vs St Kilda under was the only direct 15-20% totals matrix.
  - H2H totals under: 16.4%, n=5.
  - St Kilda May under: 7.4%, n=16.
  - St Kilda Saturday under: 7.3%, n=37.
  - Caution: Gold Coast at TIO historically leaned over.

## Important Caveats

- Market CLV is naturally positive when the market signal is defined as the side of the open-to-close move. Use it as a benchmark, not as proof the market "picked" correctly.
- AFL R8 is just one round. The cumulative running average only becomes meaningful after several rounds.
- `outputs/~$afl_h2h_matrix.xlsx` and `outputs/~$afl_handicap_matrix.xlsx` are Excel temp/lock files. They were not touched.
- Worktree has unrelated dirty files (`CLAUDE.md`, `results/r11_pricing_2026.csv`, etc.). Do not revert them unless explicitly asked.

## Suggested Next Session

After next Tuesday:

1. Check `outputs/afl_weekly_review/reports/r9_afl_ml_clv_comparison_2026.csv`.
2. Check `outputs/clv_running/running_clv_summary.csv`.
3. Review AFL normal handicap CLV and totals CLV specifically.
4. Compare NRL R11 and AFL R9 running averages once both reports exist.
