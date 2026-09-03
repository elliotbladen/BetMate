# Step 1 — shared EPL/EFL engine wired into UCL

The UCL data contract now adapts to the same Dixon–Coles implementation used by
EPL/EFL: time-decayed weighted fitting, low-score correction (`rho`), attack,
defence and home-advantage parameters, and strict as-of cutoffs. UCL rows are
marked `goals_fallback` until sourced xG is available; no xG is fabricated.

The competition wrapper remains separate: league-phase qualification and
knockout aggregate state consume the shared match probabilities downstream.
