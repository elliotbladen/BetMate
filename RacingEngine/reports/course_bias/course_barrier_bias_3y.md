# Three-year course and barrier bias baseline

Date range: **2023-09-06 to 2026-09-05**  
Tracks: **Caulfield, Flemington, Randwick, Rosehill, Sandown Hillside and Sandown Lakeside**  
Status: research baseline; suitability and map engines remain shadow-only

## Purpose

This report turns the available three-year race history into the first course
and barrier suitability baseline. It is intended to be checked against the
supplied since-2017 visual charts, then evaluated prospectively before any
rating, price or betting integration.

The data contains 2,819 races and 31,032 runner observations in the selected
three-year window. Percentages are descriptive win rates; the CSV retains the
start and win counts needed for shrinkage and uncertainty controls.

## Initial high-sample signals

Only cells with at least 50 runner starts are shown below. Small cells can look
extreme by chance and are not treated as stable bias.

| Track | Distance band | Higher observed barriers |
|---|---|---|
| Caulfield | Sprint | 3 (12.4%), 6 (12.3%), 2 (11.8%) |
| Caulfield | Mile | 6 (11.5%), 5 (11.3%), 7 (10.9%) |
| Caulfield | Middle | 3 (14.3%), 2 (13.3%), 10 (12.7%) |
| Flemington | Sprint | 6 (11.7%), 1 (11.2%), 7 (10.8%) |
| Flemington | Mile | 6 (15.1%), 1 (11.6%), 9 (11.3%) |
| Flemington | Middle | 7 (17.6%), 9 (14.3%), 10 (11.6%) |
| Rosehill | Sprint | 1 (13.5%), 6 (12.2%), 4 (11.3%) |
| Rosehill | Mile | 2 (16.6%), 4 (13.4%), 8 (13.0%) |
| Rosehill | Middle | 2 (18.7%), 9 (13.5%), 7 (10.2%) |
| Randwick | Sprint | 3 (12.4%), 8 (11.4%), 2 (9.6%) |
| Randwick | Mile | 4 (13.0%), 2 (12.6%), 5 (10.8%) |
| Randwick | Middle | 1 (16.1%), 6 (14.1%), 4/3 (12.0%) |
| Sandown Hillside | Sprint | 2/5 (16.7%), 3 (13.0%), 1/4 (11.1%) |

Sandown Lakeside has too few three-year observations for stable distance-level
conclusions and will be pooled toward broader Sandown and track-distance priors.

## Check against the supplied charts

The three-year baseline broadly supports the visual references:

- Caulfield's inside-to-middle barriers, especially 3, 5 and 6, remain useful in
  several distance bands.
- Flemington's sprint and mile results retain strength around barriers 6–8.
- Rosehill shows a recurring barrier 4/2 signal, especially at shorter and mile
  distances.
- Randwick's shorter races show competitive inside and middle draws.
- Sandown Hillside shows a central barrier signal, especially around 4–6.

Exact percentages do not need to match the charts because the charts use a
longer period, may use different race filters, and do not display denominators.
The images are therefore a reasonableness check, not ground truth.

## Modelling safeguards

The suitability engine must:

- use starts and wins, not percentages alone;
- shrink thin barrier cells toward track-distance and overall priors;
- condition on distance, going, rail position and field size where coverage
  permits;
- treat Sandown Hillside and Lakeside as separate course configurations;
- preserve the observation dates and source provenance;
- keep barrier suitability separate from the map engine's horse-specific ability
  to exploit a draw.

## Moonee Valley

Moonee Valley is intentionally excluded. The course is being rebuilt, so its
old geometry and historical barrier effects should not be carried forward as
if they describe the new track. Once racing resumes, the registry should start
a new course regime and collect prospective barrier, rail, going, checkpoint and
sectional evidence before establishing a new bias profile.
