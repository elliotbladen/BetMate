# UCL combined 1X2 + Over/Under matrix

Generated with the EPL/EFL-style row-level matrix layout:

- 378 UCL fixture rows.
- 1X2 model probabilities, fair prices, market probabilities, edges and selection.
- Over/Under 2.5 model, market, fair prices, edges and selection.
- Corner availability flag, player-shadow status and promotion gate.

Market coverage is 360/378 for 1X2 and 355/378 for the rebuilt archived totals fields; model-only totals probabilities are retained for all 378 rows. Corner fields are available for 342 rows. All rows remain paper-only.

Output: `data/ucl/markets/ucl_combined_1x2_ou25_matrix.csv`
