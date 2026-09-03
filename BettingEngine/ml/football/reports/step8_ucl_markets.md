# Champions League Step 8 — market-data adapter

The UCL market contract now covers match H2H, Asian handicap and totals, plus
tournament markets for top-eight, top-24, elimination, final position,
qualification and outright winner. Quotes require capture/publication timestamps,
source, market identity and at least two decimal-priced outcomes.

The adapter converts decimal odds to normalized no-vig probabilities for
comparison only. Market data cannot enter the strength or score model. A quote
published after the model cutoff, with inconsistent timing or invalid odds is
rejected. Match and tournament quote templates are empty pending a licensed or
otherwise approved source.
