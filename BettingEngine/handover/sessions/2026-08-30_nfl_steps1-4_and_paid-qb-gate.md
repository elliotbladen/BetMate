# NFL build handover — 2026-08-30

## User direction

Build NFL in substantially more detail than EPL, targeting roughly four to six
useful layers rather than forcing ten. Go deep on quarterback research in the
shadow. Paid data may be trialled cheaply, but it continues only if a frozen
test beats the core model and shuffled controls. This session is the conclusion
for today.

## Completed

### Step 1 — data contract

- Locked game IDs, team relocation mappings, dates, feature timing and the
  negative-home-favourite spread convention.
- Rebuilt 3,151 unique 2014–2025 regular-season games.
- Contract passes; closing-spread coverage is 3,065 games.
- The manual 50-game true-opener audit remains intentionally deferred.

### Rule eras

- Added dynamic kickoff from 2024.
- Added onside declaration while trailing, touchback to the 35 and both-team
  regular-season OT possession from 2025.
- Added a separate 2026 onside-alignment flag.
- Actual onside events are forbidden pre-game features.

### Step 2 — baselines

- Rolling 2019–2024: ridge margin MAE 10.31, Elo 10.58, closing spread 9.83.
- Ridge total MAE 10.77, closing total 10.35.
- The 2025 vault has never been predicted or evaluated.

### Step 3 — personnel and context

- Downloaded official nflverse weekly rosters and injury reports for 2014–2025.
- Built prior-game QB posteriors, uncertain-starter mixtures, roster/OL/receiver
  continuity and timestamp-checked position-weighted injury burden.
- Core + QB + continuity: margin MAE 10.11 versus core 10.31.
- Shuffled QB worsened to 10.35, supporting a genuine QB signal.
- Injuries were not promoted; weather remains diagnostic without forecast
  capture timestamps. All personnel components remain shadow-only.

### Step 3.5 — deep QB lab

- Downloaded free nflverse-hosted FTN charting for 2022–2025 (cost USD $0).
- Tested catchability, interception-worthy plays, QB-fault sacks, pocket escape,
  blitz, play action, motion, throwaways and created receptions.
- On 544 games from 2023–2024, core MAE was 10.37 and core + FTN was 10.47.
- FTN detail was rejected for promotion but retained prospectively.
- Cheapest useful paid experiment is one month of PFF+ at USD $24.99 using CSV
  exports. Subscription API access is not included. No purchase was made.
- A provider-neutral PFF/SIS import schema is in `ml/nfl/qb_lab.py`.

### Step 4 — challenger and calibration

- Installed scikit-learn and added it to requirements.
- Independent shallow tree: MAE 10.294 versus ridge 10.309, but RMSE worsened
  from 13.260 to 13.291. No promotion.
- Margin-derived H2H: Brier 0.2250, log loss 0.6413, accuracy 65.29%.
- Direct calibrated H2H was worse on all three; rejected.
- Closing market remains strongest. Blending stays disabled until at least 500
  frozen prospective predictions.

## Current state and next session

- Data contract passes.
- 2025 vault remains sealed with zero predictions in Steps 2–4.
- All active pricing remains unchanged; all new work is shadow research.
- Paid test gate: trial one month only, import licensed CSV, freeze fields and
  thresholds, compare core/core+paid/shuffled-paid, cancel if it fails.
- Next delivery step is Step 5: freeze code/config/model hashes, then run the
  vault exactly once and begin the 2026 paper season only when the user approves
  opening the vault.

## End-of-session clarification

- Step 4 did not place or simulate bets at the opening line.
- The reported 65.29% is outright winner accuracy, not an opening-line betting
  strike rate and not proof of profit.
- Step 4 compared predictions with results, closing spreads and closing
  moneyline probabilities.
- A valid opener simulation still requires the precise obtainable bookmaker,
  timestamp, price, spread pushes/key numbers, bookmaker margin, closing-line
  value, flat-stake profit and ROI.
- The deferred true-opening-line audit must be completed before any historical
  opening-line profitability claim is accepted.
