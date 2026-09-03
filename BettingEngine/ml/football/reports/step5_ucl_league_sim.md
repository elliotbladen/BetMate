# Champions League Step 5 — league-phase simulator

The table simulator is now built. It accepts the validated 36-club/144-match
league graph and club expected-goal states, draws scorelines with a seeded
Poisson process, applies points and goal-difference ordering, and returns each
club’s top-eight, 9–24 play-off and 25–36 elimination probabilities.

The simulation is deliberately blocked when the draw graph is incomplete or a
club is missing an expected-goal state. It does not use closing odds, final
standings or future information. The current repository contains only empty
UCL templates, so no probability table has been fabricated.

The next task is to populate sourced club strengths and the actual league-phase
fixture graph, then compare simulated rankings with UEFA standings in a
format-era backtest.
