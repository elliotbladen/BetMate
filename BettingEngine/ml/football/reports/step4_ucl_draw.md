# Champions League Step 4 — league-phase draw graph

The draw validator now enforces the frozen UEFA league-phase structure before a
table or qualification simulation can run. It requires 36 unique clubs in four
coefficient pots of nine, eight unique opponents per club, four home and four
away fixtures, two opponents from each pot and no more than two opponents from
the same association.

Duplicate pairings, unknown clubs, wrong pot counts and association violations
fail closed. The validator is deliberately separate from the rating model: a
strong club cannot compensate for an invalid or incomplete schedule graph.

The constraints template is empty pending sourced UEFA fixture/draw data. No
draw has been fabricated. Once populated, the graph must pass this validator
before Step 5 table simulation begins.
