# UCL Step 4 — knockout simulation

The knockout layer now prices a known first-leg state and simulates the second leg with the correct reversed venue. It carries the aggregate score, removes the away-goals rule, and resolves a tied tie through extra time and then penalties. The final is modelled as a neutral single match with the same extra-time/penalty resolution.

The final simulator was corrected so a match decided in extra time or penalties is credited to the actual winner rather than being lost from the home-win count. All outputs include the regulations version and simulation seed for reproducibility.

Promotion remains gated on historical tie-level validation and calibrated extra-time/penalty rates. Match-level 1X2 results must not be used as a substitute for qualification probabilities.
