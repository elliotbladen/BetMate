# 2026-08-24 — AFL ML vs Rules Model Backtest

## What happened

Full-season backtest comparing the AFL ML shadow model vs the rules model across all three markets (H2H, handicap, totals). $1 flat bet on every game R11-R24 where model had >=10% EV vs closing line.

This was a continuation of a larger investigation into why AFL betting has been unprofitable. Earlier in the session (before context compaction), we established:
- AFL H2H user bets: +4.32u (user's gut instincts work)
- AFL handicap model bets: 7-10 (41%), -1.38u (rules model broken)
- AFL totals: 7-9, -3.23u (user stopped checking model)
- Full rules model backtest: H2H -31.5% ROI (broken), handicap -3.0% (marginal), totals +7.7% (works)

Then user asked to run the same backtest with the ML shadow model columns from the pricing CSVs.

## Results — ML vs Rules

| Market | Model | Bets | Strike | P&L | ROI |
|--------|-------|------|--------|-----|-----|
| H2H | ML | 56 | 50% | -$0.01 | -0.0% |
| H2H | Rules | 41 | 46% | -$8.76 | -21.4% |
| Handicap | ML | 44 | 57% | +$3.50 | +8.0% |
| Handicap | Rules | 42 | 50% | -$2.10 | -5.0% |
| Totals | ML | 57 | 47% | -$5.70 | -10.0% |
| Totals | Rules | 54 | 57% | +$4.90 | +9.1% |

## Key findings

1. **ML model is clearly better for H2H**: $8.75 swing over ~50 bets. ML breaks even where rules loses 21%.
2. **ML model is clearly better for handicap**: +8.0% ROI vs -5.0%. The rules model's linear ELO->margin overcooking is the root cause.
3. **Rules model is better for totals**: +9.1% vs -10.0%. The ML total predictions run systematically low (heavy UNDER bias).
4. **The play going forward**: Use ML for H2H + handicap, rules for totals.

## Technical notes

- AFL pricing CSVs (`results/r*_afl_2026.csv`) contain both model outputs: `rules_margin/rules_total/rules_home_odds` AND `ml_margin/ml_total/ml_h2h`
- R23 has empty ML columns (skipped in backtest)
- 80 games matched out of 99 priced (some couldn't match to xlsx due to date mismatches or R20 gap)
- Handicap EV calculated via normal CDF with sigma=38.0
- H2H EV: `(model_probability * closing_odds) - 1`

## What's next

- Wire the ML model into the actual betting workflow for H2H and handicap markets
- Keep rules model for totals
- NRL ML shadow backtest still pending — check if NRL pricing CSVs have ML shadow columns or if model.db has the data
- Consider whether the "model alignment required" rule (both rules + ML must agree) should be updated now that we know which model is better per market

## Data locations

- Backtest was run inline (Python script in bash), not saved as a file
- AFL pricing CSVs: `results/r*_afl_2026.csv` (13 files, R11-R24)
- AFL closing lines: `outputs/afl_weekly_review/historical/latest.xlsx`
