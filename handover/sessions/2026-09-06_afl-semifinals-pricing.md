# AFL 2026 Semi Finals — scores in + pricing

Date: 2026-09-06
Scope: BettingEngine AFL only. No frontend, no football, no racing.

## What was done

1. **Brought in AFL Finals Week 1 results** (were not in `latest.xlsx`, max date
   was 2026-08-29 wildcard):
   - Hawthorn 72 d Fremantle 40 (QF1, Optus)
   - Geelong 107 d Carlton 74 (EF1, MCG)
   - Sydney 141 d Brisbane 88 (QF2, SCG)
   - Adelaide 90 d Western Bulldogs 68 (EF2, Adelaide Oval)
   - Appended to a copy: `outputs/afl_weekly_review/historical/latest_with_finals_wk1.xlsx`
     (canonical `latest.xlsx` left untouched — AusSportsBetting will refresh it).
   - `features_afl.csv` rebuilt via `game_log.py --xlsx latest_with_finals_wk1.xlsx`
     (1068 rows, max date 2026-09-05).

2. **Priced the two Semi Finals** (round label 26):
   - SF1 Fremantle v Geelong — Optus, Fri 11 Sep
   - SF2 Brisbane v Adelaide — Gabba, Sat 12 Sep
   - Report: `BettingEngine/outputs/results/afl_semifinals_pricing_2026.md`
   - Prices CSV: `BettingEngine/results/r26_afl_2026.csv`
   - Monte Carlo: `BettingEngine/outputs/monte_carlo/afl_semis_2026_100k.csv`
   - DB: `afl_shadow_predictions` + `afl_t9_form_shadow` season=2026 round=26

## Code changes (uncommitted)

- `scripts/prepare_afl_round.py`:
  - `FIXTURE[26]` + `INJURIES[26]` added (semi finals).
  - New `FINALS_ELO_OVERRIDE` dict + a hook in `main()` right after
    `get_current_elo()`. Reason: `get_current_elo()` reads each team's PRE-match
    ELO from their latest row, so it lags one game. Tolerable in the H&A season
    (season calibration absorbs it) but not across a finals week with three
    30–53 pt upsets. Post-FW1 ratings computed with `game_log.update_elo`
    (K=72 finals): Freo 1681, Geelong 1748, Brisbane 1706, Adelaide 1659.
- `.venv`: **installed `xgboost` 3.4.1** — it was missing, so the first
  pricing run silently fell back to rules-only. ML shadow works now.

## Model output (summary)

| Game | Rules margin | ML/primary margin | MC H2H | ML total |
|---|---|---|---|---|
| Freo v Geelong | Freo −3.0 | Freo −4.0 | Freo 52.8% / Geel 47.2% | 161 |
| Brisbane v Adelaide | Bris −15.8 | Bris −25.8 (◆10pt divergence) | Bris 73.9% / Adel 26.1% | 153 |

Rules totals came out 184 / 207 — 22 and 55 pts above ML totals. AFL totals model
is the known weak spot (2026 review −3.82u); ignore totals this week.

## Value verdict

**No disciplined bet right now.** Odds API is down and no live semi-final market
is published yet, so EVs were computed against *estimated* lines only.
- SF1 is a real model-vs-market disagreement (model = coin flip, market will make
  Freo a clear fav) but it's the "rules+ML both under the market favourite" shape
  that already backtested 4–8 ATS. Small Geelong-with-points lean at best.
- SF2: model likes Brisbane to cover a mid-teens line at the Gabba; paper EV
  ~+10% but only against a soft market estimate and with the 10pt rules/ML split.
  Expect the real line to sit near the model (≈ −18) and kill it.
- **Watch Brisbane's opening handicap** — at ≤ −14.5 it becomes live.

## Follow-ups

- Re-check both games against real opening odds (Sun night / Mon).
- T2 Footywire snapshot is R23 (3 rounds stale).
- T7 applied a −4.5 "light rain" totals penalty on 0.1–0.3 mm trace forecasts —
  the tier is over-twitchy at the bottom of its precip scale.
- Odds API key still needs rotating (redacted from history 3 Sep) before any
  live snapshot / EV work.
- When `latest.xlsx` refreshes with FW1 + the semis, delete the
  `latest_with_finals_wk1.xlsx` scratch copy and re-run cleanly.
