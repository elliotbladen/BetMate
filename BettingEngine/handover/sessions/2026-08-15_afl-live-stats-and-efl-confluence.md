# Handover — AFL live-stat resilience and EFL confluence

**Date:** 2026-08-15  
**Workspace:** `/Users/elliotbladen/BetMate/BettingEngine`

## AFL halftime live statistics

FootyWire did not withhold the Richmond–St Kilda statistics. The failure was in
our parser: it searched raw HTML for continuous text even though FootyWire puts
the home value, label and away value in separate table cells.

### Implemented

- Replaced the FootyWire regex with HTML table-cell parsing.
- Added Fox Sports as an independent backup. Fox player fields are aggregated:
  - `inside_fifty` → team inside 50s
  - `clearances` → team clearances
  - `errors` → team clangers
- Both feeds are fetched when available and cross-checked.
- Each provider retries three times.
- Raw provider HTML is retained as compressed replay material.
- Missing required statistics produce `MISSING_REQUIRED_STATS`.
- Pricing is blocked when both providers fail; the watcher retries next poll.
- An incomplete saved snapshot can be repaired when a later retry succeeds.
- The active Round 23 watcher was restarted with the new code.

### Live validation

Both FootyWire and Fox returned the same Richmond–St Kilda halftime values:

| Statistic | Richmond | St Kilda |
|---|---:|---:|
| Inside 50s | 23 | 29 |
| Clearances | 11 | 23 |
| Clangers | 27 | 29 |

Saved metadata reported `complete`, sources `footywire + foxsports`, and
cross-check `match`.

Primary files:

- `scripts/afl_ht_live.py`
- `tests/test_afl_ht_live_footywire.py`
- `data/afl/halfTime/R23/2026-08-15_richmond_vs_kilda_stats.json`

## EFL Championship confluence matrices

Built genuine historical lookup/confluence workbooks rather than another model
scoreline matrix.

### Outputs

- `outputs/football/championship/efl_championship_1x2_confluence_matrix.xlsx`
- `outputs/football/championship/efl_championship_goals_confluence_matrix.xlsx`
- Reusable builder: `scripts/efl_championship_confluence_matrix.py`

### Data governance

- Development window: 2020/21–2024/25, 2,760 matches.
- The sealed 2025/26 model-evaluation vault remains excluded.
- Current 2026/27 clubs all receive sheets. Clubs without qualifying recent
  Championship history show insufficient evidence rather than invented values.
- Minimum row sample is five matches.
- Reliability labels: small (5–14), useful (15–29), strong (30+).
- Historical closing probabilities are de-vigged.
- Highlight threshold is an actual-minus-market difference of 7.5 percentage
  points.
- Confluence rows overlap and must not be treated as independent/additive.

### Matrix coverage

Both workbooks include overall, home/away, weekday, month, previous result,
rest, price band, referee and opponent splits.

The 1X2 workbook reports team win and draw rates versus the historical closing
market. The goals workbook reports O/U 2.5 versus the closing totals market and
BTTS versus the Championship base rate. Historical BTTS closing odds are not
available, so BTTS differences are tendencies rather than proven market edges.

## Referee appointments and referee confluence

Official Round 1 appointments were found in the EFL sitemap/page:

`https://www.efl.com/news/2026/august/11/referee-appointments--14-20-august/`

The page content is embedded in Nuxt JSON even when the visible article body is
not rendered by a basic HTML parser. Historical referee names already exist in
the Football-Data Championship archive.

### Strongest referee-only O/U signals

| Match | Referee | Signal | Difference | N |
|---|---|---|---:|---:|
| Portsmouth–QPR | Will Finnie | Over 2.5 | +17.4 pp | 14 |
| Cardiff–Wrexham | Andrew Kitchen | Under 2.5 | +15.0 pp | 51 |
| Norwich–West Brom | Tim Robinson | Under 2.5 | +8.1 pp | 103 |
| Middlesbrough–Lincoln | Bobby Madley | Over 2.5 | +7.8 pp | 51 |
| Bolton–Preston | Adam Herczeg | Under 2.5 | +7.5 pp | 7 |

The best balance of magnitude and sample is Cardiff–Wrexham Under 2.5. The
Portsmouth signal is larger but based on only 14 matches.

### Strongest referee-only BTTS tendencies

| Match | Referee | Signal | Difference vs league | N |
|---|---|---|---:|---:|
| Portsmouth–QPR | Will Finnie | BTTS Yes | +15.3 pp | 14 |
| Middlesbrough–Lincoln | Bobby Madley | BTTS Yes | +7.9 pp | 51 |
| Burnley–West Ham | Josh Smith | BTTS Yes | +6.4 pp | 103 |
| Cardiff–Wrexham | Andrew Kitchen | BTTS No | +5.8 pp | 51 |
| Stoke–Swansea | Oliver Langford | BTTS Yes | +5.5 pp | 125 |

## Week 1 prices discussed

### Cardiff–Wrexham

- Full model Under 2.5: 52.4%, fair $1.91.
- Captured market Under price: approximately $2.05.
- Referee Andrew Kitchen: Under 66.7% versus historical market expectation
  51.7%, a +15.0 pp difference over 51 matches.
- At $2.05 the full-model EV calculation is approximately +7.4%.

### Portsmouth–QPR

- Full model BTTS Yes: 57.5%, fair $1.74.
- Full model Over 2.5: 47.6%, fair $2.10.
- Full model Under 2.5: 52.4%, fair $1.91.
- Referee Will Finnie: Over 2.5 and BTTS Yes both 64.3%, N=14.
- Interpretation: the main totals model has a slight Under lean while referee
  and BTTS evidence support goals. Over 2.5 is interesting only around $2.10+
  and the small referee sample must not be allowed to dominate the main model.

## Operational next steps

1. Add an automated weekly EFL official-appointments fetch that parses the Nuxt
   article payload and stores fixture/referee mappings.
2. Normalize full referee names from the appointment page to historical initials
   in the matrix (`Andrew Kitchen` → `A Kitchen`, etc.).
3. Add referee confluence to the round pricing report as a separate evidence
   line, not as an automatically additive probability adjustment.
4. Audit the frozen Week 1 positions against results and closing prices after
   the round without modifying the original forecasts.
