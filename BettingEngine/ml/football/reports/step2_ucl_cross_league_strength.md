# Step 2 — cross-league club strength

UCL club ratings now have a point-in-time strength contract. Domestic observed
attack/defence ratings are adjusted for the source league and shrunk toward a
UEFA prior, with the shrinkage weakening as observed match count grows. This
handles clubs entering from different leagues and prevents sparse UCL history
from producing extreme ratings. Market odds are excluded from the state.

The layer is ready to consume domestic xG/Dixon–Coles snapshots and UEFA
coefficient priors during the UCL walk-forward fit.
