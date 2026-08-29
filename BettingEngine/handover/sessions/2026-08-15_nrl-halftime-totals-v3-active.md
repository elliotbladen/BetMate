# NRL halftime totals v3 — active implementation

## Outcome

The active NRL halftime pricer now imports `scripts/nrl_ht_totals_v3.py`.
Version v2 remains on disk for reproducibility but is no longer the production
totals import.

V3 retains the historically fitted score-state baseline, pre-game total prior,
empirical conditional second-half distribution, and median-derived fair betting
line. It adds four reliability-controlled process layers:

1. pace (sets, runs, metres, play-the-balls),
2. attacking opportunity (inside-20s when present, line breaks, forced dropouts,
   set restarts),
3. execution (completion), and
4. defensive stress (missed tackles).

Correlated proxies are averaged inside each layer. Missing provider fields are
ignored, coverage shrinks the live adjustment, and the total process change is
capped at four points. Output is explicitly marked `forward_calibration` until
enough observations exist to fit those coefficients out of sample.

## Collection change

`scripts/nrl_ht_live.py` now captures normalized stats, raw provider stats and
the raw timeline at 10, 20, 30 and 40 minutes. It captures corresponding market
odds unless launched with `--no-snapshot-odds`. It recognizes the NRL draw
feed's `FirstHalf -> SecondHalf` transition even when draw `gameSeconds` remains
zero, uses the match timeline clock as fallback, records checkpoint lag, and
does not fabricate missed earlier snapshots from later data. Existing snapshot
files prevent duplicate collection after a poller restart.

## Validation

- Python compilation passed for scraper, v3, and active pricer.
- 12 direct tests passed: five legacy v2, five v3, two scraper/state-contract.
- Manly–Dolphins replay ran successfully through the active pricer and reported
  `nrl_ht_totals_v3_process_distribution`.
- 753 historical rows were replay-compared with no deep stats. V3 changed zero
  baseline predictions versus v2, confirming that missing features cannot move
  a price.

## Known problems / calibration boundary

- The 2022–2025 archive has no populated deep halftime process stats. Therefore
  a genuine historical backtest of the new process weights is impossible today.
  Only the score-state/distribution layer is historically testable.
- The public NRL match-centre feed does not consistently expose exact field
  coordinates, set-start position, ball-in-play time, or inside-20 possessions.
  Those remain `null`; v3 uses visible opportunity proxies and never converts a
  missing field to zero.
- The next games are the first honest forward-calibration sample. Coefficients
  should be refit only after enough checkpoint/HT/FT outcomes and captured
  opening-to-live/closing totals exist.
- In-play odds capture consumes Odds API calls at every checkpoint. The flag
  `--no-snapshot-odds` exists for quota emergencies, but normally should remain
  off because market-state history is required for calibration.

