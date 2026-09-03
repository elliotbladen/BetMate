# NFL final research readiness — 31 August 2026

## Outcome

The model framework is ready for its prospective shadow, but it is not ready to
bet. The frozen Week 1 card contains 16 games and its prediction hash still
matches the sealed manifest. T1 prices can be displayed as paper estimates;
every betting decision is currently ABSTAIN and staking remains disabled.

## Consolidated historical result

Across 1,599 walk-forward development games, T1 margin MAE was 10.309 points.
Adding T2 quarterback/personnel and T3 continuity reduced it to 10.104, a 0.204
point gain that appeared in all six tested seasons. T4 spread, T5 schedule and
T7 matchup were rejected. T6 weather remains a totals-only shadow. T8 and T9
show promising closing-line direction but have not passed prospective testing.

T9's retrospectively discovered spread rule was 67–55–2 with +1.79 points mean
CLV. This is a hypothesis to test, not permission to bet. Its thresholds are now
frozen.

## Current blockers

- No valid timestamped market quote has been archived; the Odds API is expired.
- The 16-game quarterback starter/backup review is blank.
- Available 2026 rosters are pre-cut and fail the continuity quality gate.
- The official 2026 injury dataset is not published in the checked source.
- Stadium coordinates remain unverified, so no weather forecasts were captured.

These are missing live inputs, not failed historical models. The system fails
closed until they are resolved.

## Promotion standard

No tier can become active from this study alone. Promotion requires at least 500
frozen predictions across two seasons, 90% market coverage, audited obtainable
openers and prices, positive mean CLV, positive opening-line beat rate, genuine
out-of-sample score improvement and no retrospective threshold changes.
