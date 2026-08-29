# AFL R23 2026 — ML tiered prices

Generated 12 August 2026. Fair prices are decimal odds with no bookmaker margin.

This is the ML forecast with every currently available adjustment tier applied:

- **Base ML:** raw margin and total forecasts.
- **ML total calibration:** +0.1 points.
- **Tier 2:** opponent/matchup adjustment.
- **Tier 3:** situational adjustment.
- **Tier 4:** venue adjustment.

Tiers 5 (injuries), 6 (referee) and 7 (weather) are currently zero for every R23 game: no usable adjustment feed was loaded, so they have not been guessed or back-filled.

| Date | Match | Tiered margin | Fair H2H (home / away) | Tiered total | Margin change | Total change |
|---|---|---:|---:|---:|---:|---:|
| 14 Aug | Fremantle v Adelaide | Fremantle -8.3 | 1.69 / 2.45 | 162.7 | +3.5 | -1.3 |
| 15 Aug | Brisbane v Gold Coast | Brisbane -53.7 | 1.07 / 14.69 | 170.8 | +8.0 | +0.1 |
| 15 Aug | Hawthorn v Collingwood | Hawthorn -8.9 | 1.67 / 2.48 | 173.0 | -0.2 | +0.8 |
| 15 Aug | North Melbourne v Geelong | Geelong -26.8 | 4.38 / 1.30 | 167.1 | -3.9 | +0.0 |
| 15 Aug | Port Adelaide v Melbourne | Port Adelaide -0.5 | 1.98 / 2.02 | 161.3 | -0.4 | -1.9 |
| 15 Aug | Richmond v St Kilda | St Kilda -49.2 | 11.65 / 1.09 | 162.6 | -5.0 | -1.9 |
| 16 Aug | Essendon v Sydney | Sydney -39.9 | 7.47 / 1.15 | 167.7 | -1.3 | -1.9 |
| 16 Aug | GWS v West Coast | GWS -55.6 | 1.07 / 16.33 | 179.3 | +4.0 | +2.1 |
| 16 Aug | Western Bulldogs v Carlton | Western Bulldogs -14.0 | 1.54 / 2.87 | 150.4 | +1.4 | +2.1 |

## Method

`tiered margin = raw ML margin + T2 + T3 + T4 + T5 + T6`

`tiered total = raw ML total + 0.1 calibration + T2 + T3 + T4 + T5 + T6 + T7`

H2H prices are derived from the tiered margin using the model's 36-point normal margin distribution. Positive margin changes strengthen the home side; negative changes strengthen the away side.

## Important model check

Richmond–St Kilda remains a material disagreement between the raw ML H2H classifier (Richmond 50.8%) and the margin model (St Kilda by 49.2 after tiers). The prices above deliberately follow the tiered **margin** model so the handicap and H2H are internally consistent; treat that fixture as a no-bet until the input data is reviewed.
