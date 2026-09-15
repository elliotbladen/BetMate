# UCL Matchweek 1 — model versus closing market

**Status: CLV not calculable from the preserved data.**

## What is preserved

The normal model has frozen prices for **12 of 18 fixtures**:

- **1X2:** 12 modelled fixtures, with fair home/draw/away prices.
- **O/U 2.5:** 12 modelled fixtures, with raw Over and Under prices.
- **6 fixtures:** blocked for missing cross-league strength; they have no model price.

The source files are:

- `week_1_shadow_player_rating/prices.csv` — the nine-fixture first run;
- `week_1_champions_league_prices/md1_remaining_normal_and_shadow/run/normal/prices.csv` — the three additional normal prices;
- `.../md1_remaining_normal_and_shadow/predictions.csv` — the frozen six-fixture settlement board.

## Why there is no CLV result

No Matchweek 1 closing market snapshot was stored for these fixtures. The repository
contains the model prices and fixture inputs, but no time-stamped or labelled closing
1X2/O/U quote file for the 2026/27 Matchweek 1 matches. The contemporaneous odds
snapshot archive contains EPL/AFL/NRL markets and does not contain the UCL board.

Therefore the following figures must remain **unreported**, rather than being
reconstructed from a later price:

| Market | Modelled | Closing quotes | CLV |
|---|---:|---:|---|
| 1X2 | 12 fixtures | 0 preserved | **Not calculable** |
| O/U 2.5 | 12 fixtures | 0 preserved | **Not calculable** |

The earlier Matchweek 1 pricing handover explicitly recorded: “No market quotes, no
EV, no bets.” The model run was research-only, so treating its fair prices as saved
bet prices would produce a false CLV result.

## Conclusion

There is no defensible positive or negative CLV claim for UCL Matchweek 1 from the
current evidence. The model coverage and prices are preserved; the missing input is
the closing market file. A valid follow-up needs a contemporaneous close for each
fixture, with the source, bookmaker/consensus definition and capture time recorded.
