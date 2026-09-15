# NFL shadow-component architecture

These four tracks run beside the official EPA model. They produce diagnostic
increments only; the live price and staking path remain unchanged.

## Pipeline

1. Build point-in-time team aggregates from play-by-play and special-teams data.
2. Fit each component as a residual against the relevant base model target.
3. Evaluate rolling-origin by season, retaining the 2025 vault for the final check.
4. Apply fixed research caps only when producing shadow prices.
5. Compare base versus shadow on score error, opening/closing market distance,
   CLV and a pre-registered ROI rule.

## Components

| Component | Market | Main question | Initial cap |
|---|---|---|---:|
| Drive/red-zone residual | Total | Does possession and scoring opportunity explain totals beyond EPA? | 3.0 |
| Bayesian TD/field-goal regression | Total | Are finishing rates above/below a shrunk league prior? | 3.0 |
| Turnover-luck residual | Margin | Is turnover margin likely to regress from process indicators? | 1.5 |
| Special-teams field position | Margin | Do punts, kickoffs, returns and kicking create repeatable field-position value? | 1.5 |

Touchdowns are used through opportunity and finishing rates, never as raw points.
Each component has a separate target and feature family so the same signal cannot
be added twice. Promotion requires a stable out-of-sample gain and positive mean
CLV; a single profitable sample is insufficient.
