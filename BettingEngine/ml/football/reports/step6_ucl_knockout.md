# Champions League Step 6 — knockout aggregate simulator

The knockout engine now carries a known first-leg score into the second-leg
simulation. The second leg must reverse home and away clubs. Aggregate goals
decide the tie; away goals are never doubled. If aggregate scores are level,
the engine simulates extra time and then penalties. The final uses a neutral
single-match simulation with the same tie-resolution treatment.

The output is a qualification probability for each club and a frozen rules
version. Negative expected goals, malformed legs and invalid simulation counts
are rejected. No odds or future results enter the simulation.

This is the engine only: no UCL tie probabilities have been produced because
the sourced club-strength and fixture data remain pending.
