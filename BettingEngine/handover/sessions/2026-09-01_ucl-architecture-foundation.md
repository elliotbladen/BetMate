# Champions League architecture foundation — 1 September 2026

Research established that the modern UEFA Champions League is a 36-club,
single-league phase followed by a play-off/round-of-16 knockout path. The new
competition is structurally different from EPL/EFL: opponent allocation is
coefficient-pot constrained, schedules are unequal, and qualification state
changes incentives. Knockout ties are aggregate two-leg contests without away
goals; ties use extra time and penalties, while the final is one neutral match.

Approved architecture: cross-league hierarchical club strength, a format-aware
league-phase table simulator, an aggregate-score knockout Markov layer and
coherent match/tournament markets. The model will share infrastructure with the
football engine but use Champions-League-specific coefficients and validation.

The first implementation task is the competition/data contract, followed by
club identity and the 2024/25–2025/26 format-era backtest.

Step 1 is now complete: the 2026/27 rules contract is frozen in
`ml/football/ucl_rules.py`, with validation tests and a machine-readable report.

Step 2 is now complete: canonical club identity, alias collision checks and the
timestamped match data contract are implemented. Empty CSV templates are ready
for sourced population; no club or match rows were invented.

Step 3 is now complete: cross-league attack/defence strength with league
adjustment and UEFA-prior shrinkage is implemented and tested. The fit remains
blocked until the sourced UCL club and match templates are populated.

Step 4 is now complete: the league-phase draw validator enforces 36 clubs, four
pots of nine, eight unique opponents, four home/four away, two per pot and the
same-association limit. Sourced fixture population remains pending.

Step 5 is now complete: the seeded scoreline table simulator produces top-eight,
play-off and elimination probabilities from the validated graph. It refuses to
run with incomplete fixtures or missing club strength states; no probabilities
have been fabricated.

Step 6 is now complete: the aggregate knockout simulator carries first-leg
scores, reverses the second-leg venue, removes away goals and resolves ties via
extra time and penalties. The neutral final path is also implemented; no real
tie probabilities have been generated before sourced data exists.

Step 7 is now complete: timestamped player, suspension, rotation, rest and travel
context contracts are implemented. All are diagnostic with zero direct points;
the sourced context templates remain empty pending collection.

Step 8 is now complete: UCL match and tournament quote contracts normalize
decimal odds to no-vig probabilities while keeping markets downstream of model
features. Empty quote templates are ready for sourced population; no odds were
fabricated.

Step 9 is now complete: format-aware backtest metrics cover H/D/A RPS, Brier,
log loss, accuracy and top-eight/top-24 calibration. Modern league-phase seasons
are separated from legacy group-stage seasons; the run is blocked until sourced
matches and expanding-window predictions exist.

On 1 September the architecture was reworked around the actual sources found:
openfootball for UEFA results/stages and Football-Data UK for domestic results,
statistics and available odds. The priority is now a reproducible match-market
backtest, with modern league-phase qualification evaluated separately from
legacy group-stage seasons. A five-step data-first build plan is saved in
`ml/football/reports/ucl_reworked_build_plan.md`.

The openfootball source was downloaded and imported: 1,997 main-competition
match rows from 2011/12–2025/26, including 189 each in 2024/25 and 2025/26. The
rows preserve stages and date-only precision; odds and xG are absent and no rows
were fabricated. Step 9 now has sourced matches loaded and awaits predictions.

The first expanding-window results-only baseline is now run across all 1,997
matches. It uses only prior results, reports modern and legacy format eras
separately, and excludes odds/xG. This is a baseline for the cross-league fit,
not a promoted pricing model.
