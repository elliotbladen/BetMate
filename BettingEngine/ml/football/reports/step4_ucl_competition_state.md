# Step 4 — integrated UCL competition-state engine

The shared EPL/EFL match probabilities now feed the UCL competition wrapper.
The wrapper has been validated end to end for league-phase qualification and
knockout state handling: 36-team table buckets, two-leg aggregate scoring,
second-leg venue reversal, no away-goals rule, extra time/penalties and the
neutral final. All 35 UCL tests pass.

The state layer changes how probabilities are propagated through the
tournament; it does not replace the Dixon–Coles/Elo match engine.
