# NFL Step 8B — live T2/T3 shadow framework

## Outcome

The live T2/T3 contract and scorer are implemented. No Week 1 player data was
invented: all 16 games remain explicitly unresolved and produce no tier score.
The official frozen T1 prices are unchanged and staking remains disabled.

## T2 quarterback

Live T2 requires a named starter, named backup, a timestamped starter
probability and pregame profiles for both players. Each QB metric is mixed using
that probability rather than treating an uncertain starter as confirmed. The
model-derived QB contribution is emitted separately in home-margin points.

Historical actual starters were used to estimate the shadow coefficient ceiling
through 2024. They are an oracle and may not populate a live forecast. A missing
starter probability, player ID or profile fails validation.

## T2 availability

The template captures injury burden, players out, questionable players and
report coverage. These fields remain diagnostic and apply zero points. The
historical audit showed that simple position-weighted injury reports added
little and weakened the comparison with the closing spread when bundled with
the stronger QB signal.

## T3 continuity

The live contract accepts weekly roster continuity and returning roster,
offensive-line and receiver shares. Its model contribution remains a separate
shadow output. Missing continuity data prevents a complete shadow score rather
than silently becoming a neutral zero.

## Safety rules

- `as_of_utc`, kickoff and all source timestamps must be timezone-aware.
- No source may be newer than the prediction cutoff.
- Every record must be frozen before kickoff.
- Starter probabilities must be between zero and one.
- A populated probability requires both player IDs and both QB profiles.
- The scorer never overwrites T1 and labels its combined output uncapped and
  unapproved.
- Tier caps are deliberately not frozen yet.

## Artefacts

- `ml/nfl/step8_live_tiers.py`
- `ml/nfl/reports/step8_live_tier_model.json`
- `data/nfl/live_tiers/2026_week01_input_template.json`
- `tests/test_nfl_step8_live.py`

The focused NFL suite passes 28 tests. The next decision is the source used to
populate live starter probabilities and player profiles, followed by review of
observed shadow contribution sizes before selecting safety caps.
