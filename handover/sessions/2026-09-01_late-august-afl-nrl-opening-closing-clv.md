# Late-August AFL/NRL opening and closing market review

Date: 1 September 2026

## Scope

The requested review concerns only the completed late-August weekend, not the
entire historical archive. The market source is AusSportsBetting. AFL covers
the two wildcard games on 29 August; NRL covers all eight official Round 26
games from 27–30 August.

Football-Data had not yet published the corresponding EPL/Championship weekend:
EPL stopped at 24 August and Championship at 23 August. Do not substitute the
previous football weekend. Refresh the source after it updates.

## Saved inputs and outputs

- `data/odds/weekends/2026-08-27/afl.csv`
- `data/odds/weekends/2026-08-27/nrl.csv`
- `BettingEngine/results/r27_pricing_2026.csv`
- `BettingEngine/outputs/results/afl_wildcard_pricing_2026.md`
- `BettingEngine/outputs/results/late_august_2026_model_vs_open_close.csv`
- `BettingEngine/outputs/results/late_august_2026_model_vs_open_close.md`

Price CLV is calculated on the model-preferred side as opening odds divided by
closing odds minus one. Model edge against opening and closing is calculated
using no-vig two-way market probabilities. Handicap and total comparisons are
kept separate from price CLV.

## NRL result

- Model-preferred H2H side won 6/8 games.
- Flat one-unit staking at opening prices returned +0.76u (+9.5% ROI).
- Positive price CLV occurred in 5/8 games; mean CLV was +6.1%.
- The closing handicap moved closer to the model in 6/8 games.
- Margin MAE was 13.4 points.
- The closing total moved closer to the model in only 1/8 games.
- Total MAE was 15.5 points; the model was generally too low.

Applying the proposed **minimum 10% opening-EV rule** produced six qualifiers:
five had positive CLV, mean CLV was +8.4%, five won, and flat opening-price P/L
was +1.51u (+25.2% ROI). This is encouraging evidence for the rule, but it is a
single-round sample and must not be presented as proof of long-run profitability.

The clearest market agreement was Melbourne Storm: model probability 70.0%,
opening $1.97, closing $1.54, price CLV +27.9%; Storm won 46–20.

## AFL result

- Model-aligned H2H sides were Carlton and Western Bulldogs.
- Both won and both shortened: Carlton $2.05 to $1.90 (+7.9% CLV), Bulldogs
  $1.95 to $1.80 (+8.3% CLV).
- Combined opening-price result was +2.00u, but neither was recorded as an
  official strong H2H bet in the published wildcard report.
- Handicap market moved closer to the published model in 0/2 games.
- Margin MAE was 14.0 points and total MAE was 37.5 points.

The AFL report contained the known internal conflict: blended H2H correctly
leaned Bulldogs/Carlton, while the published rules margins favoured
Collingwood/Melbourne. Do not use the raw AFL ML margin values retrospectively;
the source report explicitly says they overcook margins.

## Going-forward decision

- Preserve the normal production model as the historical comparison source.
- For NRL H2H, test the 10% opening-EV gate across the full season and against
  closing no-vig probabilities before promoting it as a staking rule.
- Treat NRL totals as requiring recalibration; do not infer health from H2H CLV.
- Retain the planned AFL NFL/EPL-style half-rebuild, incorporating the useful
  H2H features but resolving H2H/margin incoherence and weak totals calibration.
- Keep opening edge, closing edge, price CLV, line movement and realised result
  as separate evaluation fields.
