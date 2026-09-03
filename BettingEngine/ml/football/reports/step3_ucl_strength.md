# Champions League Step 3 — cross-league strength engine

The first strength layer is now implemented. It estimates club attack and
defence from domestic evidence, applies a learned country/league adjustment and
shrinks sparse samples toward a five-season UEFA coefficient prior. Shrinkage is
strong for clubs with little current-season evidence and weakens as matches
accumulate.

Every strength state has a UTC as-of timestamp, observed-match count and source
fields. Market odds are prohibited from the strength fit. The engine is
competition-agnostic in code but the UCL configuration supplies its own
cross-league constants.

The strength template is intentionally empty. No domestic or Champions League
results have been invented. After sourced population, the next validation must
check club identity coverage, country/league effects and expanding-window
strength stability before the score model is fitted.
