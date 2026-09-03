# Champions League Step 7 — squad and match context

The UCL context contract now supports timestamped player availability,
suspensions, expected minutes, domestic rotation, rest, travel and timezone
movement. Goalkeepers, defenders, midfielders, forwards and coaches have
different diagnostic weights, but no event receives direct model points.

Information announced or published after the model cutoff is rejected. Missing
or unconfirmed information remains unresolved rather than being treated as
availability. Context signals are kept separate from the score model until a
walk-forward audit proves value.

The player-event and match-context templates are empty. No lineup, injury,
travel or rotation observations have been fabricated.
