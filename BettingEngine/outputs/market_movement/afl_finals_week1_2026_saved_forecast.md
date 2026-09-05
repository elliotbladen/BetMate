# AFL Finals Week 1 — Saved Market-Movement Forecast

Saved: 2026-09-04 (Australia/Brisbane)

Status: **shadow only — not a bet list and not authorised to alter stakes**.

Model source: `data/line_movement/predictions/afl_finals_direction_shadow.json`

The handicap and totals forecasts come from the four-layer AFL movement-direction pilot. H2H direction is an inference from handicap direction and the observed H2H market; it is not a separately validated H2H classifier. A material move is at least 1.5 points.

## Saved calls

| Match | H2H money forecast | Handicap money forecast | Totals forecast | Confidence / note |
|---|---|---|---|---|
| Fremantle v Hawthorn | Fremantle pre-game model lean; actual market moved slightly to Hawthorn | No material move most likely; secondary Fremantle | No move most likely; upward tail | Match completed before this review; retain only as an out-of-sample audit |
| Geelong v Carlton | Geelong | Geelong; likely close around -9.5 to -10.5 | Near 167.5; slight upward tail | Medium-high handicap, medium H2H, low total |
| Sydney v Brisbane | Brisbane H2H | Sydney + points; likely close around +22.5 to +23.5 | Over; likely 189.5 to 191.5 | Medium handicap; strongest totals call, but totals model remains unvalidated |
| Adelaide v Western Bulldogs | Slight Western Bulldogs H2H | Adelaide; likely -17.5 with -18.5 possible | Upward move largely made; likely 168.5 to 170.5 | Medium handicap, low H2H, medium total |

## Frozen model probabilities from the 2026-09-02 Sportsbet snapshot

`DOWN` means the listed home handicap/total decreases numerically, `UP` means it increases, and `NO_MOVE` means there is no move of at least 1.5 points.

| Match | Snapshot handicap | Handicap DOWN | NO_MOVE | UP | Snapshot total | Total DOWN | NO_MOVE | UP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fremantle v Hawthorn | -13.5 | 23.4% | 61.8% | 14.8% | 162.5 | 15.3% | 58.4% | 26.3% |
| Geelong v Carlton | -6.5 | 26.1% | 58.4% | 15.5% | 168.5 | 17.1% | 58.3% | 24.6% |
| Sydney v Brisbane | +24.5 | 30.1% | 45.3% | 24.6% | 187.5 | 16.8% | 45.4% | 37.8% |
| Adelaide v Western Bulldogs | -15.5 | 20.8% | 62.3% | 16.8% | 168.5 | 13.7% | 52.9% | 33.4% |

## Market state observed when saved

| Match | H2H open → current | Handicap open → current | Total open → current |
|---|---|---|---|
| Fremantle v Hawthorn | Fremantle 1.42 → 1.45 | Fremantle -14.5 → -14.5 | 159.5 → 160.5 |
| Geelong v Carlton | Geelong 1.62 → 1.55 | Geelong -8.5 → -9.5 | 167.5 → 167.5 |
| Sydney v Brisbane | Brisbane 1.26 → 1.25 | Sydney +25.5 → +23.5 | 187.5 → 189.5 |
| Adelaide v Western Bulldogs | Adelaide 1.38 → 1.40 | Adelaide -16.5 → -17.5 | 165.5 → 168.5 |

Sources checked on 2026-09-04:

- https://www.aussportstipping.com/fixtures/afl/2026/09/03/fremantle_vs_hawthorn/
- https://www.aussportstipping.com/fixtures/afl/2026/09/04/geelong_vs_carlton/
- https://www.aussportstipping.com/fixtures/afl/2026/09/05/sydney_vs_brisbane/
- https://www.aussportstipping.com/fixtures/afl/2026/09/05/adelaide_vs_western_bulldogs/

## Grading instructions

After each market closes, record the final H2H prices, primary handicap and total immediately before the bounce. Grade handicap and total as `DOWN`, `NO_MOVE`, or `UP` against the frozen 2026-09-02 snapshot. Keep H2H grading separate because it is currently an inferred signal. Do not retroactively change these saved calls.

