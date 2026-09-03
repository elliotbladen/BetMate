# Current UCL versus EPL/EFL engine comparison

## Finding

The UCL core is now upgraded to the shared production-style stack: time-weighted Dixon-Coles, a 30% ClubElo blend, and leakage-safe form/rest adjustments. The refreshed walk-forward run covers 1,872 matches from 2012/13 through 2025/26: RPS 0.2074, Brier 0.5743, log loss 0.9673, and accuracy 56.41%.

## Shared with EPL/EFL

- Same Dixon-Coles likelihood, low-score correction, and scoreline matrix.
- Chronological walk-forward fitting with no future leakage.
- Active ClubElo blend and supported form/rest context adjustments.
- UCL-specific league-phase and knockout layers remain separate from match pricing.

## Deliberate limitations

UCL historical files do not provide consistent dated PPDA, player injuries, referee, set-piece, or manager-change coverage. Those layers remain shadow/diagnostic until reliable history is imported; activating them without that evidence would create false precision. xG also uses a goals fallback where provider xG is absent.

## Conclusion

The match engine is now structurally comparable to EPL/EFL while remaining format-aware for Champions League football. Further gains require better historical inputs and calibration, not a different core model.
