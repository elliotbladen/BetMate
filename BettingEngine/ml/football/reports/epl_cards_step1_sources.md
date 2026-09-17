# EPL cards Step 1 — data sources and gaps

## Results and card events

The four completed modelling seasons are now in
`data/epl/cards/epl_card_results_2022_23_to_2025_26.csv` (1,520 matches). The
files are the public E0 season files from football-data.co.uk:

- `https://www.football-data.co.uk/mmz4281/2223/E0.csv`
- `https://www.football-data.co.uk/mmz4281/2324/E0.csv`
- `https://www.football-data.co.uk/mmz4281/2425/E0.csv`
- `https://www.football-data.co.uk/mmz4281/2526/E0.csv`

The normalized file contains `HY`, `AY`, `HR`, and `AR`, plus separate totals for
yellow cards, red cards, and yellow-plus-red cards. The source has 380 rows per
season, no duplicate fixture keys, and no missing card values.

## Settlement convention

The free Footiqo card-odds file calls its market
`over_3_5_yellow_cards_ft_closing_odds`, so the historical odds currently available
to us are a **yellow-card total**, not a generic red-plus-yellow card count. The
model target for that file is therefore `HY + AY`.

This must not be mixed with Pinnacle-style booking-points markets: Pinnacle states
that a yellow card is one booking and a red card is two, with a second yellow handled
under its specific booking rules. If the live bookmaker market is booking points, it
requires a separate target and calibration. We will label the model explicitly as
`yellow_cards_ou35` until a market's rules say otherwise.

## Card closing odds

The user-provided
`Footiqo_Free_Corners_Cards_Odds-hgeoxn.xlsx` has been normalized to
`data/epl/cards/footiqo_epl_cards_closing_odds_2025_26.csv`.

It contains all 380 EPL matches from 2025/26, with complete Over/Under 3.5 yellow-card
closing odds. It is enough to test the final unseen season's price comparison.

The free Footiqo file does **not** contain 2022/23–2024/25 card odds and does not
contain historical opening card odds. Footiqo's public coverage page says the free
sample is 2025/26, while the multi-season specialist card-closing file is part of the
paid package. No free GitHub or football-data source found so far supplies those
historical card prices.

Consequently, the red-card gap is fixed and the 2025/26 closing-price gap is fixed.
The earlier-season closing prices and historical opening prices remain unavailable
without another licensed archive or the Footiqo specialist file. Opening prices will
be collected prospectively from the live odds snapshots rather than invented for the
historical backtest.
