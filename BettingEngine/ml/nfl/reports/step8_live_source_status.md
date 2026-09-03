# NFL Step 8D — first live roster/depth capture

## Source status

Official nflverse release assets were checked on 31 August 2026. The 2026 weekly
roster and depth-chart files were available and last updated on 30 August. The
2026 injury release returned 404 and is not yet available.

The depth chart contains all 32 teams at timestamp `2026-08-30T12:30:54Z`.
QB1 and QB2 candidates were extracted for Week 1 without assigning starter
probabilities. All 32 QB1 candidates and 28 of 32 QB2 candidates have a prior
historical profile. The four missing QB2 profiles must use a rookie/no-history
prior if they become relevant; they may not be silently treated as average.

## Continuity rejection

The 2026 weekly roster contains 2,852 ACT rows, approximately 89 per team. This
is a preseason roster, not a comparable post-cut game roster. Direct comparison
with the final 2025 roster produced returning shares of only 0.33–0.53, which is
an artefact of the larger denominator.

Those continuity values are retained as a pre-cut diagnostic but are explicitly
ineligible for T3 scoring. T3 remains unresolved until a post-cut roster with no
more than 60 active/inactive players per team is captured and validated.

## Current readiness

- QB depth candidates: available, probability review required.
- Historical QB profiles: available.
- Week 1 official injury/practice reports: unavailable.
- T3 comparable continuity: unavailable until final cuts.
- Market prices: unavailable while the Odds API subscription is inactive.
- Official price changes and staking: disabled.

Sources: nflverse weekly-roster and depth-chart GitHub release assets. nflverse
documents that rosters, depth charts and injury reports are maintained by its
automated roster pipeline.
