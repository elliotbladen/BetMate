# NRL halftime H2H and handicap v3 — active

## Decision

H2H and handicap now come from one coherent final-margin distribution in
`scripts/nrl_ht_margin_v3.py`. The handicap is the negative distribution median
(home betting convention), while H2H probabilities are the distribution mass
on either side of zero. They can no longer contradict one another.

After research review, the first v3 baseline was corrected. Points already on
the scoreboard no longer regress toward the pregame final margin. The active
baseline is `current scoreboard margin + pregame margin × remaining game
fraction`. At halftime, only 50% of the original pregame expected margin is
assigned to the remaining half before capped live-process evidence is applied.

The previous implementation displayed an adjusted expected margin but generated
H2H probability from a separate score simulation that ignored that adjusted
margin. On the Manly–Dolphins replay it showed Manly at 5.0% despite an expected
margin of only -3.9. The first v3 replay exposed a second issue: a fixed 55/45
blend treated the eight-point halftime deficit as if it could regress away.
Corrected v3 produces Manly 21.8%, Dolphins 78.2%, and Manly +8.3 from the same
empirical distribution. The saved market was Manly +11.5 to +12.5.

## Model

- Baseline: current margin plus the remaining-time share of the pregame
  expected full-game margin.
- Execution layer: error and completion differentials.
- Opportunity layer: inside-20s when genuine, line breaks, forced dropouts and
  set-restart differentials.
- Physical/defensive layer: run metres, tackle breaks and missed tackles.
- Conversion regression: first-half kicks relative to a 75% expectation.
- Correlated features are averaged inside layers; missing data is ignored.
- Coverage shrinks the total live adjustment; adjustment cap is five points.
- Historical conditional second-half margin outcomes provide the distribution.

Legacy component calculations remain printed as explicitly inactive diagnostics
during forward comparison. They do not set H2H odds or the handicap.

## Validation and boundary

- Five margin-engine tests pass, plus the existing totals/scraper tests.
- Both saved Round 24 matches replay through the corrected active engine.
- Full historical process-weight backtesting remains impossible because the
  historical archive has no deep halftime stats and no rules-engine pregame
  handicap field. The empirical margin distribution is historical; process
  weights remain forward-calibration priors and are capped accordingly.
