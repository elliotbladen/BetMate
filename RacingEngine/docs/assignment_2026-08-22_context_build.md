# Assignment — what we built and how each next step must improve it

The job today was not to force the model’s score upward. It was to build the
plumbing that lets us find genuine improvement without fooling ourselves. The
existing base rating remains frozen. That is important because every new idea
needs an honest opponent: the exact model we had before the idea was added.
Earlier weight experiments did not beat that opponent out of sample, so they
remain in shadow. We have not hidden that result or adjusted the test until it
looked favourable.

## Step 1 — freeze the base

We locked `performance-par-v1.0` as the comparison model. This means the new
weight and context work cannot silently change yesterday’s benchmark. The
improvement from this step is measurement quality: future gains can be credited
to a named change. If a candidate does not improve log loss, Brier score and
calibration on the same races, it will not be promoted. We will inspect where
it failed—distance, class, state, going or history depth—then revise the data or
hypothesis using training data only.

## Step 2 — understand the type of race

We classified all 29,845 runner appearances by the race’s weight conditions.
The set contains 19,133 handicap rows, 2,744 quality handicaps, 2,628 set-weight
rows, 3,945 set-weights-plus-penalties rows, 1,382 WFA rows and only 13 unknown.
This should improve later modelling because weight means different things in a
handicap and a WFA race. If separate models still do not improve, we will test
whether the segments are too small or the labels too broad, then pool them with
shrinkage instead of inventing stronger coefficients.

## Step 3 — reconstruct weight honestly

We created one weight-context record per runner. It stores carried weight,
official WFA, weight relative to the field median and the official handicap
rating. It also has proper places for allocated weight, apprentice claims,
overweight and penalties. The crucial finding is that our historical results
separately verify allocated weight for only 354 rows, and do not verify the
other three items. Missing values remain NULL. We will improve this
by capturing pre-race cards with source provenance and timestamps. If coverage
cannot be made reliable, models will use a missingness flag or exclude that
component; they will never assume missing means zero.

## Step 4 — compare each horse with itself

For horses with history, we now calculate the change in carried weight,
official rating, class and distance from the previous run, and whether the new
race was stronger. This is more sensible than awarding every horse a universal
bonus per kilogram. A highly rated horse often carries more because it is
better, so a naive formula can count the same ability twice. The improvement we
seek is whether within-horse changes predict the next performance. If they do
not, we will add interactions carefully—race type, distance and class move—and
use shrinkage where samples are thin.

## Step 5 — add context without mixing meanings

We connected the previous run’s Race Strength, daily track variant, going,
sectional quality, recorded extra distance, steward events and campaign stage.
These remain separate fields. A steward report does not automatically equal a
fixed number of lengths, and a post-meeting track variant cannot pretend it was
known before the meeting. Coverage is already useful: 20,749 rows have prior
Race Strength, 16,917 prior daily variant, 18,280 prior sectional confidence and
3,719 have prior steward evidence. If these features do not improve forecasting,
we will first audit identity and timing, then test corroborated combinations
such as wide-run evidence plus distance travelled rather than turning every
comment into an arbitrary adjustment.

## Step 6 — create the learning table

We materialised 29,845 point-in-time rows. Each row represents what the system
could know before a target race. Historical outcomes come only from races with
an earlier date. The target race’s result-derived weight is explicitly excluded.
There are 9,096 debutant or no-linked-prior-history rows, which stay in the data
instead of disappearing. This table is the foundation for machine learning and
backtesting. Its improvement is protection against hindsight. If the first ML
models do not improve, we will diagnose coverage, calibration and segments;
we will not leak the result or search the holdout for a convenient formula.

## What the tests proved

The new tests prove race-condition precedence and prove that a horse’s second
race can see the first race’s weight but cannot see its own result. The entire
project suite now passes: 65 tests in the project virtual environment. The
feature build was run across the full database. The process was also changed
from repeated per-runner lookups to bulk data joins and insertion, making the
artefact more repeatable.

## What has not improved yet

We have not claimed a better predictive score today. The previous WFA-relative,
IFHA-distance and learned-weight candidates all failed promotion: headline log
loss was worse and the uncertainty ranges crossed zero. That result does not
mean weight is useless. It means the simple versions could not separate weight
burden from horse ability, race conditions and incomplete source detail. Today’s
architecture addresses those causes, but it must still earn promotion in a new
experiment.

## What remains

First, collect trustworthy pre-race allocated weight, claims, overweight,
penalties, minimum weights and compressed handicap scales. Second, link steward
events through durable horse IDs and audit daily-variant timing. Third, import
timestamped Betfair opening, decision-time and closing prices. Fourth, train
small interpretable models on training data only. Fifth, run ablations: base,
base plus one family, then justified interactions. Sixth, compare every version
chronologically against the frozen base, equal probability and eventually the
market. A candidate that fails will be revised only when diagnostics reveal a
plausible data or design issue; otherwise it will be rejected. A candidate that
passes repeatedly will be frozen and then tested once on genuinely new races.

That is how each future step becomes an attempted improvement rather than just
more complexity. The system is now ready to learn from historical choices and
results safely, but it is not yet ready to call itself self-learning or to claim
it can beat the market. Those claims require timestamped market data, repeated
forward results and strict promotion discipline.
