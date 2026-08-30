# NFL Step 3 — Personnel and context

## Outcome

Step 3 is implemented in shadow mode. Official nflverse weekly rosters and
injury reports for 2014–2025 were added. Quarterback histories were derived from
play-by-play and emitted before each current game was incorporated. Expanding
walk-forward tests again cover 2019–2024 only; the 2025 vault remains untouched.

| Model | Margin MAE | Margin RMSE | MAE to close |
|---|---:|---:|---:|
| Core EPA | 10.31 | 13.26 | 2.84 |
| Core + quarterback | 10.18 | 13.12 | 2.48 |
| Core + shuffled quarterback | 10.35 | 13.33 | 2.94 |
| Core + continuity | 10.23 | 13.16 | 2.78 |
| Core + injuries | 10.28 | 13.24 | 2.83 |
| Core + QB + continuity | **10.11** | **13.05** | **2.48** |
| Core + all personnel | 10.10 | 13.07 | 2.52 |

Quarterback information provides the clearest gain: 0.13 points of margin MAE
and 0.37 points closer to the closing spread. Roster continuity adds a smaller
gain. The simple injury burden barely improves game-result error and makes the
combined model farther from the close than QB plus continuity, so injuries are
not promoted. Shuffling QB values onto the wrong games makes the model worse
than the core, which supports the conclusion that correctly mapped QB history
contains real signal rather than merely benefiting from extra columns.

## What is genuinely point-in-time

QB posteriors use only prior dropbacks: passing EPA, success, sacks,
interceptions and scrambling are regressed over a 150-dropback prior. Roster
features compare the current weekly ACT/INA list with the prior week and prior
season. Injury rows are rejected when their modification date is later than the
game date.

## Restrictions

The historical schedule identifies the QB who actually started. That is useful
for measuring the ceiling of QB information, but a future price must instead
use a timestamped probability mixture of starter and backup. The mixture logic
is implemented and tested; a missing or unresolved live probability must keep
T2 shadow or trigger T0 abstention.

Injuries are position-weighted, not snap-weighted, because historical snap
shares are not present. Weather in the schedule is an observed game condition,
not a timestamped forecast. It remains diagnostic only. Rest stays inside the
regularised baseline and receives no hand-written bye bonus.

## Artefacts and gate

- `ml/nfl/personnel.py`: QB posterior, starter mixture, roster and injury store
- `ml/nfl/phase3.py`: one-family-at-a-time walk-forward ablations
- `data/nfl/features/personnel_context.parquet`: 3,151 unique games
- `data/nfl/predictions/step3_ablations.csv`: frozen development predictions
- `ml/nfl/reports/step3_personnel_context.json`: machine-readable scoreboard

All components remain shadow-only. QB plus continuity is the leading Step 3
candidate, but promotion requires prospective starter probabilities, complete
snap-aware availability and frozen live confirmation.
