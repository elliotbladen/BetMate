# UCL Step 3 — league-phase simulation

The league-phase simulator is now the competition-state layer. It validates 36 clubs, 144 unique fixtures, four nine-club coefficient pots, eight opponents per club, four home and four away matches, two opponents from each pot and the same-association limit. It simulates scorelines from the match engine and returns top-8, playoff (9–24), elimination (25–36) and expected-position probabilities.

The simulator is deliberately separate from match pricing: 1X2 and totals price an individual match, while this layer propagates the entire fixture graph into qualification outcomes. It uses a fixed random seed for reproducibility and rejects incomplete or fabricated draw graphs.

Step 3 implementation is complete at the engine level. Historical qualification validation remains dependent on importing the official coefficient-pot and draw metadata for each modern league-phase season. Until those are present, the simulator will fail closed rather than assign invented pots.
