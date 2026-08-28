# Collateral revision and campaign/layoff handover

Date: 2026-08-28

Implemented `racing_engine/collateral_revision_v2.py` and
`racing_engine/horse_ability_campaign_v2.py`.

The collateral build uses 25% of the generic handicap component at race time.
Later form can create an effective-dated revision in
`v2_achieved_run_revisions`; it cannot alter earlier chronological predictions.
Gringotts' Doncaster is 103.15 initially and 109.62 from the 22 August WFA
rematch. Revised current ability is Gringotts 110.87 versus Sheza Alibi 110.83;
initial-only current ability is Sheza Alibi 110.83 versus Gringotts 110.28.

The next Horse Ability step tested post-layoff decay. Training selected no
decay (2.34058 log loss) over slow (2.34152), medium (2.34198), and fast
(2.34252). Do not reduce base ability for absence. Treat layoff as uncertainty
or a current-condition scenario, but note that the present probability scorer
does not yet consume uncertainty.

Both candidates remain shadow-only and accepted production ratings are
unchanged. Next: distance/going suitability, followed by the final Horse
Ability validation gate.
