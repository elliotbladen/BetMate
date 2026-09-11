# Blended course and barrier suitability baseline

Date range of observed data: **2023-09-06 to 2026-09-05**  
Tracks: **Caulfield, Flemington, Randwick, Rosehill, Sandown Hillside and Sandown Lakeside**  
Status: research baseline; suitability and map engines remain shadow-only

## Blend method

The recent three-year database is blended with the owner-supplied since-2017
barrier charts. The charts do not provide denominators or their exact race
filters, so each displayed percentage is treated as a weak prior with an
explicit effective sample size of 20 starts:

```text
blended rate = (observed wins + 20 × visual prior rate)
                / (observed starts + 20)
```

Where a visual prior is unavailable, the observed three-year rate is retained.
The visual source and effective sample size are stored separately so the blend
can be replaced by genuine long-term counts later.

## Findings after blending

The blend preserves the strong recent evidence while tempering extreme values
from either source:

- **Caulfield:** barrier 3 remains strong in sprints (12.8%) and middle
  distances (14.7%); barrier 6 remains competitive in sprints and miles.
- **Flemington:** barrier 6 remains the most stable sprint/mile signal, while
  the visual barrier-8 sprint signal is reduced by the larger recent sample.
- **Sandown Hillside:** barrier 5 remains the strongest high-sample sprint
  signal (18.4% blended); the apparent middle-distance barriers 6–8 are kept
  low-confidence because their recent samples are small.
- **Sandown Lakeside:** the visual and recent sources are both sparse. The
  blended values are retained as priors only and will be pooled toward broader
  Sandown evidence.
- **Rosehill:** barrier 1 remains strong in recent sprints, while barrier 4's
  visual mile signal is moderated by the three-year evidence. Barrier 2 remains
  strong over mile and middle distances.
- **Randwick:** barrier 3 remains the strongest recent sprint signal; barrier 2
  is strengthened in the mile by the visual prior; barrier 1 remains strong in
  middle-distance races.

## Decision

The blended table is now the suitability baseline. It is not a direct winner
adjustment. Before model integration, it must be conditioned further by rail,
going, field size and course regime, with shrinkage and uncertainty reported
for every cell.

Barrier suitability remains separate from the map engine's horse-specific
ability to use the draw. No ratings, prices or bets are changed.

## Moonee Valley

Moonee Valley is intentionally excluded. The rebuilt course will start a new
course regime after reopening. We will collect fresh rail, geometry, barrier,
checkpoint, sectional and going evidence before creating a new bias profile.
