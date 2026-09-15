# UCL Matchweek 1 — model versus closing market

**Historical audit, superseded on 15 September 2026.** Opening and closing 1X2 quotes have now been recovered. See [the sourced comparison and $1 return analysis](../../../../../../reports/ucl/2026-27/md01/README.md).

Correction: the final model files preserve 12 1X2 predictions but only three explicit raw O/U 2.5 predictions. The earlier claim of 12 frozen totals prices below was incorrect. The first nine final predictions explicitly withheld totals; the abandoned diagnostic run must not be substituted.

The remainder records the state before external closing quotes were recovered.

## What is preserved

The normal model has frozen prices for **12 of 18 fixtures**:

- **1X2:** 12 modelled fixtures, with fair home/draw/away prices.
- **O/U 2.5:** 3 final modelled fixtures with explicit raw Over and Under prices; 9 first-slate final predictions withheld totals.
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
| O/U 2.5 | 3 fixtures | 0 preserved at audit time | **Not calculable** |

The earlier Matchweek 1 pricing handover explicitly recorded: “No market quotes, no
EV, no bets.” The model run was research-only, so treating its fair prices as saved
bet prices would produce a false CLV result.

## Conclusion

There is no defensible positive or negative CLV claim for UCL Matchweek 1 from the
current evidence. The model coverage and prices are preserved; the missing input is
the closing market file. A valid follow-up needs a contemporaneous close for each
fixture, with the source, bookmaker/consensus definition and capture time recorded.
